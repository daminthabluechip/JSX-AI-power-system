from datetime import date

from seed.seed_data import seed


def test_generate_and_read_plan(app, client):
    seed(date(2026, 10, 14))

    res = client.post("/plans/generate", json={"date": "2026-10-14", "time_limit_s": 3})
    assert res.status_code == 202
    plan_id = res.get_json()["id"]

    plan = client.get(f"/plans/{plan_id}").get_json()   # tests solve synchronously
    assert plan["status"] == "ready"
    assert plan["version"] == 1 and plan["routes"]
    assert plan["total_distance_km"] > 0 and plan["solve_time_s"] is not None

    served = 0
    for route in plan["routes"]:
        assert route["weight_utilization_pct"] <= 100 and route["volume_utilization_pct"] <= 100
        stops = route["stops"]
        assert [s["sequence"] for s in stops] == list(range(1, len(stops) + 1))
        # arrival times never go backwards along a route
        times = [s["planned_arrival"] for s in stops]
        assert times == sorted(times)
        served += len(stops)
    assert served + len(plan["unassigned"]) == 50   # every order is either planned or explained
    assert all(u["reason"] for u in plan["unassigned"])


def test_second_generate_creates_new_version(app, client):
    seed(date(2026, 10, 14))
    body = {"date": "2026-10-14", "time_limit_s": 1}
    client.post("/plans/generate", json=body)
    second = client.post("/plans/generate", json=body).get_json()
    assert second["version"] == 2
    assert len(client.get("/plans?date=2026-10-14").get_json()["items"]) == 2


def test_generate_without_depot_marks_plan_failed(client):
    res = client.post("/plans/generate", json={"date": "2026-10-14"})
    plan = client.get(f"/plans/{res.get_json()['id']}").get_json()
    assert plan["status"] == "failed" and "depot" in plan["error"].lower()


def test_generate_validates_input(client):
    assert client.post("/plans/generate", json={"date": "tomorrow"}).status_code == 400
    assert client.post("/plans/generate", json={"vehicle_ids": "all"}).status_code == 400
    assert client.get("/plans/999").status_code == 404


def test_unknown_ids_and_empty_input_fail_clearly(app, client):
    seed(date(2026, 10, 14))
    bad_vehicle = client.post("/plans/generate", json={"date": "2026-10-14", "vehicle_ids": [9999]})
    plan = client.get(f"/plans/{bad_vehicle.get_json()['id']}").get_json()
    assert plan["status"] == "failed" and "9999" in plan["error"]

    no_orders = client.post("/plans/generate", json={"date": "2030-01-01"})
    plan = client.get(f"/plans/{no_orders.get_json()['id']}").get_json()
    assert plan["status"] == "failed" and "No pending orders" in plan["error"]


def test_dispatch_updates_vehicles_and_orders(app, client):
    seed(date(2026, 10, 14))
    pid = client.post("/plans/generate", json={"date": "2026-10-14", "time_limit_s": 2}).get_json()["id"]
    plan = client.get(f"/plans/{pid}").get_json()

    assert client.post(f"/plans/{pid}/dispatch").get_json()["status"] == "dispatched"
    assert client.post(f"/plans/{pid}/dispatch").status_code == 409   # only once
    used = {r["vehicle"]["id"] for r in plan["routes"]}
    for vid in used:
        assert client.get(f"/vehicles/{vid}").get_json()["status"] == "on_route"
    first_order = plan["routes"][0]["stops"][0]["order_id"]
    assert client.get(f"/orders/{first_order}").get_json()["status"] == "in_transit"


def test_plan_detail_has_what_a_map_needs(app, client):
    seed(date(2026, 10, 14))
    pid = client.post("/plans/generate", json={"date": "2026-10-14", "time_limit_s": 2}).get_json()["id"]
    plan = client.get(f"/plans/{pid}").get_json()
    depot = [plan["depot"]["latitude"], plan["depot"]["longitude"]]
    for route in plan["routes"]:
        stops = [[s["latitude"], s["longitude"]] for s in route["stops"]]
        assert route["path"] == [depot] + stops + [depot]     # depot -> stops in order -> depot
