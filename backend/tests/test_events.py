from datetime import date

from app.models import Vehicle
from seed.seed_data import seed

DAY = "2026-10-14"


def make_plan(client):
    seed(date(2026, 10, 14))
    res = client.post("/plans/generate", json={"date": DAY, "time_limit_s": 2})
    return client.get(f"/plans/{res.get_json()['id']}").get_json()


def report(client, body):
    res = client.post("/events", json=body)
    assert res.status_code == 202, res.get_json()
    return res.get_json(), client.get(f"/plans/{res.get_json()['plan']['id']}").get_json()


def served_orders(plan):
    return {s["order_id"] for r in plan["routes"] for s in r["stops"]}


def test_event_needs_a_finished_plan_first(client):
    res = client.post("/events", json={"type": "breakdown", "vehicle_id": 1})
    assert res.status_code == 409


def test_breakdown_removes_vehicle_and_replans_its_orders(app, client):
    old = make_plan(client)
    broken = old["routes"][0]["vehicle"]["id"]
    moved = {s["order_id"] for s in old["routes"][0]["stops"]}

    out, new = report(client, {"type": "breakdown", "vehicle_id": broken})
    assert out["replaces_plan_id"] == old["id"] and new["version"] == old["version"] + 1
    assert new["status"] == "ready"
    assert broken not in {r["vehicle"]["id"] for r in new["routes"]}
    assert db_status(broken) == "maintenance"
    covered = served_orders(new) | {u["order_id"] for u in new["unassigned"]}
    assert moved <= covered
    assert client.get("/events").get_json()["items"][0]["handled_by_plan_id"] == new["id"]


def db_status(vehicle_id):
    from app.extensions import db
    return db.session.get(Vehicle, vehicle_id).status


def test_cancellation_removes_order(app, client):
    old = make_plan(client)
    victim = old["routes"][0]["stops"][0]["order_id"]
    _, new = report(client, {"type": "cancellation", "order_id": victim})
    assert victim not in served_orders(new)
    assert victim not in {u["order_id"] for u in new["unassigned"]}
    assert client.post("/events", json={"type": "cancellation", "order_id": victim}).status_code == 409


def test_rush_order_is_added_and_critical_is_served(app, client):
    make_plan(client)
    rush = {"customer": "Summit Medical", "address": "Hospital Rd, Kandy", "latitude": 7.29,
            "longitude": 80.63, "weight_kg": 300, "volume_m3": 1, "priority": "critical",
            "earliest_arrival": "09:00", "latest_arrival": "16:00"}
    out, new = report(client, {"type": "rush_order", "order": rush})
    assert out["event"]["order_id"] in served_orders(new)


def test_delay_pushes_departure_later(app, client):
    old = make_plan(client)
    route = old["routes"][0]
    h, m = map(int, route["planned_departure"].split(":"))
    _, new = report(client, {"type": "delay", "vehicle_id": route["vehicle"]["id"], "delay_minutes": 90})
    for r in new["routes"]:
        if r["vehicle"]["id"] == route["vehicle"]["id"]:
            nh, nm = map(int, r["planned_departure"].split(":"))
            assert nh * 60 + nm >= h * 60 + m + 90 - 1
    for r in new["routes"]:
        assert all(s["planned_arrival"] >= r["planned_departure"] for s in r["stops"])


def test_event_validation(app, client):
    make_plan(client)
    assert client.post("/events", json={"type": "meteor"}).status_code == 400
    assert client.post("/events", json={"type": "breakdown"}).status_code == 400
    assert client.post("/events", json={"type": "breakdown", "vehicle_id": "x"}).status_code == 400
    assert client.post("/events", json={"type": "delay", "vehicle_id": 1}).status_code == 400
    assert client.post("/events", json={"type": "cancellation", "order_id": 99999}).status_code == 400
    assert client.post("/events", json={"type": "rush_order", "order": {"customer": "x"}}).status_code == 400
    assert client.post("/events", json=[1]).status_code == 400


def test_compare_reports_what_changed(app, client):
    old = make_plan(client)
    victim = old["routes"][0]["stops"][0]["order_id"]
    _, new = report(client, {"type": "cancellation", "order_id": victim})

    diff = client.get(f"/plans/{old['id']}/compare/{new['id']}").get_json()
    assert diff["before"]["id"] == old["id"] and diff["after"]["id"] == new["id"]
    removed = [c for c in diff["changes"] if c["change"] == "removed"]
    assert [c["order_id"] for c in removed] == [victim]
    assert removed[0]["customer"]
    assert diff["unchanged_orders"] >= 0 and "distance_delta_km" in diff
    assert client.get("/plans/1/compare/9999").status_code == 404


def test_replan_is_stable_for_small_disruptions(app, client):
    old = make_plan(client)
    total = len(served_orders(old))

    first = old["routes"][0]["stops"][0]["order_id"]
    _, after_cancel = report(client, {"type": "cancellation", "order_id": first})
    diff = client.get(f"/plans/{old['id']}/compare/{after_cancel['id']}").get_json()
    reassigned = [c for c in diff["changes"] if c["change"] == "reassigned"]
    assert len(reassigned) <= 0.25 * total, f"{len(reassigned)} of {total} orders changed vehicle"

    rush = {"customer": "Rush", "address": "x", "latitude": 7.0, "longitude": 79.9,
            "weight_kg": 200, "volume_m3": 1, "priority": "critical"}
    _, after_rush = report(client, {"type": "rush_order", "order": rush})
    diff = client.get(f"/plans/{after_cancel['id']}/compare/{after_rush['id']}").get_json()
    reassigned = [c for c in diff["changes"] if c["change"] == "reassigned"]
    assert len(reassigned) <= 0.25 * total, f"{len(reassigned)} of {total} orders changed vehicle"
