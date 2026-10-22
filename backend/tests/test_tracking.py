from datetime import date

from app.optimizer.solver import solve
from app.optimizer.types import OrderSpec, VehicleSpec
from app.services import tracking_service as tracking
from app.services.routing_service import HaversineProvider
from app.simulator.engine import Simulator
from seed.seed_data import seed

DAY = "2026-10-14"


def hm(text):
    h, m = map(int, text.split(":"))
    return h * 60 + m


def line_schedule():
    wp = tracking.Waypoint
    return [wp((0.0, 0.0), 100, 100), wp((0.0, 0.009), 110, 120, order_id=1), wp((0.0, 0.0), 130, 130)]


def test_position_follows_the_plan():
    wps = line_schedule()
    assert tracking.position_at(wps, 90)[2] == "waiting"
    xy, speed, state = tracking.position_at(wps, 105)
    assert state == "driving" and abs(xy[1] - 0.0045) < 1e-6 and speed > 0
    assert tracking.position_at(wps, 115)[2] == "at_stop"
    assert tracking.position_at(wps, 125)[2] == "driving"
    assert tracking.position_at(wps, 200)[2] == "finished"


def test_lag_is_zero_on_schedule_and_grows_when_behind():
    wps = line_schedule()
    half = (0.0, 0.0045)
    assert tracking.schedule_lag(wps, half, 105) < 0.5
    assert abs(tracking.schedule_lag(wps, half, 115) - 10) < 0.5
    assert tracking.schedule_lag(wps, (0.0, 0.009), 115) == 0
    assert tracking.schedule_lag(wps, half, 95) == 0
    assert tracking.schedule_lag(wps, (0.0, 0.0), 300) == 0


def test_solver_starts_a_vehicle_from_its_current_position():
    depot = (6.9271, 79.8612)
    order_xy, vehicle_xy = (7.30, 80.60), (7.28, 80.58)
    coords = [depot, order_xy, vehicle_xy]
    dist, dur = HaversineProvider().matrix(coords)
    orders = [OrderSpec(1, 100, 1, tw_start=0, tw_end=1440)]

    from_depot = solve([VehicleSpec(1, 5000, 20)], orders, dist, dur, time_limit_s=1)
    from_road = solve([VehicleSpec(1, 5000, 20, shift_start=10 * 60, start_node=2)], orders, dist, dur, time_limit_s=1)

    r = from_road.routes[0]
    assert r.start_node == 2 and r.departure >= 10 * 60
    assert from_road.total_distance_km < from_depot.total_distance_km


def dispatched(client):
    seed(date(2026, 10, 14))
    pid = client.post("/plans/generate", json={"date": DAY, "time_limit_s": 2}).get_json()["id"]
    assert client.post(f"/plans/{pid}/dispatch").status_code == 200
    return client.get(f"/plans/{pid}").get_json()


def test_simulator_moves_vehicles_and_delivers_orders(app, client):
    plan = dispatched(client)
    sim, cfg = Simulator(), app.config
    first_dep = min(hm(r["planned_departure"]) for r in plan["routes"])

    assert sim.tick(cfg, first_dep - 30) == len(plan["routes"])
    before = {i["vehicle_id"]: i for i in client.get("/tracking/positions").get_json()["items"]}
    assert all(i["state"] in ("waiting", "idle") for i in before.values())

    sim.tick(cfg, first_dep + 120)
    after = client.get("/tracking/positions").get_json()["items"]
    moved = [i for i in after if i["state"] in ("driving", "at_stop")]
    assert moved and all(i["lag_minutes"] == 0 for i in after)
    assert all(i["next_stop"] for i in moved)
    delivered = client.get("/orders?status=delivered&per_page=100").get_json()["total"]
    assert delivered > 0

    sim.tick(cfg, 23 * 60)
    assert client.get("/orders?status=in_transit&per_page=100").get_json()["total"] == 0
    assert all(i["state"] in ("finished", "idle") for i in client.get("/tracking/positions").get_json()["items"])


def test_injected_delay_raises_an_alert_with_a_ready_to_use_suggestion(app, client):
    plan = dispatched(client)
    sim, cfg = Simulator(), app.config
    route = max(plan["routes"], key=lambda r: len(r["stops"]))
    vid, t0 = route["vehicle"]["id"], hm(route["planned_departure"]) + 30

    sim.tick(cfg, t0)
    assert client.get("/tracking/alerts").get_json()["items"] == []
    sim.inject_delay(vid, 40)
    sim.delays[vid][0] = (t0, 40)
    sim.tick(cfg, t0 + 5)
    assert client.get("/tracking/alerts").get_json()["items"] == []
    sim.tick(cfg, t0 + 25)

    alerts = client.get("/tracking/alerts").get_json()["items"]
    assert [a["vehicle_id"] for a in alerts] == [vid]
    assert 20 <= alerts[0]["lag_minutes"] <= 30
    assert alerts[0]["suggested_event"]["type"] == "delay"
    stalled = next(i for i in client.get("/tracking/positions").get_json()["items"] if i["vehicle_id"] == vid)
    assert stalled["state"] == "stopped" and stalled["speed_kmh"] == 0


def test_live_replan_starts_from_positions_and_skips_delivered_orders(app, client):
    plan = dispatched(client)
    sim, cfg = Simulator(), app.config
    route = max(plan["routes"], key=lambda r: len(r["stops"]))
    vid = route["vehicle"]["id"]
    depart, back = hm(route["planned_departure"]), hm(route["return_time"])

    now = depart + (back - depart) // 2
    sim.tick(cfg, now - 20)
    sim.delays[vid] = [(now - 20, 60)]
    sim.tick(cfg, now)
    delivered_ids = {o["id"] for o in client.get("/orders?status=delivered&per_page=100").get_json()["items"]}
    assert delivered_ids
    alert = client.get("/tracking/alerts").get_json()["items"][0]

    res = client.post("/events", json=alert["suggested_event"])
    assert res.status_code == 202, res.get_json()
    new = client.get(f"/plans/{res.get_json()['plan']['id']}").get_json()
    assert new["status"] == "ready"

    planned = {s["order_id"] for r in new["routes"] for s in r["stops"]} | {u["order_id"] for u in new["unassigned"]}
    assert not planned & delivered_ids
    assert planned
    for r in new["routes"]:
        assert hm(r["planned_departure"]) >= now - 1
        assert all(hm(s["planned_arrival"]) >= now - 1 for s in r["stops"])

    from app.models import Route
    from app.extensions import db
    started_on_road = Route.query.filter_by(plan_id=new["id"]).filter(Route.start_latitude.isnot(None)).count()
    assert started_on_road >= 1


def test_dispatching_the_replan_supersedes_the_old_plan(app, client):
    plan = dispatched(client)
    sim = Simulator()
    route = plan["routes"][0]
    t = hm(route["planned_departure"]) + 20
    sim.tick(app.config, t)
    res = client.post("/events", json={"type": "delay", "vehicle_id": route["vehicle"]["id"], "delay_minutes": 30})
    new_id = res.get_json()["plan"]["id"]

    assert client.post(f"/plans/{new_id}/dispatch").status_code == 200
    assert client.get(f"/plans/{plan['id']}").get_json()["status"] == "superseded"
    assert client.get("/tracking/positions").get_json()["plan_id"] == new_id


def test_position_ingest_endpoint_and_simulator_controls(app, client):
    dispatched(client)
    ok = client.post("/tracking/positions", json={"vehicle_id": 1, "latitude": 7.0, "longitude": 80.0,
                                                   "recorded_at": "2026-10-14T09:30:00"})
    assert ok.status_code == 201
    assert client.post("/tracking/positions", json={"vehicle_id": 9999, "latitude": 7, "longitude": 80}).status_code == 400
    assert client.post("/tracking/positions", json={"vehicle_id": 1, "latitude": "x", "longitude": 80}).status_code == 400

    assert client.post("/tracking/simulator", json={"action": "bogus"}).status_code == 400
    assert client.post("/tracking/simulator", json={"action": "delay", "vehicle_id": 1, "minutes": -5}).status_code == 400
    assert client.post("/tracking/simulator", json={"action": "start", "speed": 999}).status_code == 400
    assert client.post("/tracking/simulator", json={"action": "reset"}).get_json()["running"] is False
    assert client.get("/tracking/simulator").status_code == 200


def test_simulator_start_requires_a_dispatched_plan(client):
    assert client.post("/tracking/simulator", json={"action": "start"}).status_code == 409


def test_compare_ignores_stop_renumbering_and_labels_delivered_orders_completed(app, client):
    plan = dispatched(client)
    sim = Simulator()
    first_dep = min(hm(r["planned_departure"]) for r in plan["routes"])
    sim.tick(app.config, first_dep + 150)
    res = client.post("/events", json={"type": "rush_order", "order": {
        "customer": "Rush", "address": "x", "latitude": 7.0, "longitude": 79.9, "weight_kg": 100, "volume_m3": 1}})
    diff = client.get(f"/plans/{plan['id']}/compare/{res.get_json()['plan']['id']}").get_json()

    kinds = {}
    for c in diff["changes"]:
        kinds[c["change"]] = kinds.get(c["change"], 0) + 1
    assert kinds.get("completed", 0) > 0 and "removed" not in kinds
    assert diff["unchanged_orders"] > 0
    assert kinds.get("added") == 1


def test_simulator_resumes_from_where_it_was_paused(app, client, monkeypatch):
    from app.simulator import engine
    from app.simulator.engine import simulator

    class NoThread:
        def __init__(self, *a, **k): pass
        def start(self): pass
    monkeypatch.setattr(engine.threading, "Thread", NoThread)
    dispatched(client)
    simulator.reset()
    try:
        first = client.post("/tracking/simulator", json={"action": "start", "time": "09:00", "speed": 1}).get_json()
        assert first["running"] and first["sim_time"] == "09:00"
        client.post("/tracking/simulator", json={"action": "stop"})
        resumed = client.post("/tracking/simulator", json={"action": "start"}).get_json()
        assert resumed["sim_time"].startswith("09:0")
    finally:
        simulator.reset()


def test_simulator_stops_itself_when_every_vehicle_is_home(app, client):
    plan = dispatched(client)
    sim = Simulator()
    sim.running = True
    first_dep = min(hm(r["planned_departure"]) for r in plan["routes"])
    sim.tick(app.config, first_dep + 60)
    assert sim.running
    sim.tick(app.config, 23 * 60)
    assert not sim.running and sim.start_minute == 23 * 60
