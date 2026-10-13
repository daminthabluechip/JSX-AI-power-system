"""An order that requires a vehicle type may only be served by a vehicle of that type."""
from datetime import date

from app.optimizer.baseline import nearest_neighbour
from app.optimizer.solver import solve
from app.optimizer.types import OrderSpec, VehicleSpec
from app.optimizer.validators import check_plan
from app.services.routing_service import HaversineProvider
from seed.seed_data import seed

DEPOT = (6.9271, 79.8612)


def problem(vehicles, orders, offsets):
    coords = [DEPOT] + [(DEPOT[0] + a, DEPOT[1] + b) for a, b in offsets]
    dist, dur = HaversineProvider().matrix(coords)
    return vehicles, orders, dist, dur


def served_by(result):
    return {s.order_id: r.vehicle_id for r in result.routes for s in r.stops}


def test_required_type_beats_the_cheaper_vehicle():
    # Vehicle 1 is nearer/cheaper, but the order needs refrigeration, so vehicle 2 must take it.
    vehicles = [VehicleSpec(1, 10000, 50, vehicle_type="truck"), VehicleSpec(2, 10000, 50, vehicle_type="refrigerated")]
    orders = [OrderSpec(1, 500, 2, required_vehicle_type="refrigerated"), OrderSpec(2, 500, 2)]
    v, o, d, t = problem(vehicles, orders, [(0.05, 0.0), (0.05, 0.01)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert served_by(result)[1] == 2
    assert not result.unassigned and check_plan(result, v, o) == []


def test_no_vehicle_of_the_required_type_gives_a_clear_reason():
    vehicles = [VehicleSpec(1, 10000, 50, vehicle_type="truck")]
    orders = [OrderSpec(1, 500, 2, required_vehicle_type="refrigerated"), OrderSpec(2, 500, 2)]
    v, o, d, t = problem(vehicles, orders, [(0.05, 0.0), (0.0, 0.05)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert list(served_by(result)) == [2]
    assert "required type 'refrigerated'" in result.unassigned[0]["reason"]


def test_capacity_is_checked_against_eligible_vehicles_only():
    # The big truck could carry 9 t, but only the small refrigerated van is allowed.
    vehicles = [VehicleSpec(1, 20000, 80, vehicle_type="truck"), VehicleSpec(2, 5000, 20, vehicle_type="refrigerated")]
    orders = [OrderSpec(1, 9000, 5, required_vehicle_type="refrigerated")]
    v, o, d, t = problem(vehicles, orders, [(0.05, 0.0)])
    result = solve(v, o, d, t, time_limit_s=1)
    assert "every 'refrigerated' vehicle" in result.unassigned[0]["reason"]


def test_baseline_and_validator_respect_the_rule():
    vehicles = [VehicleSpec(1, 20000, 80, vehicle_type="truck"), VehicleSpec(2, 8000, 30, vehicle_type="flatbed")]
    orders = [OrderSpec(1, 500, 2, required_vehicle_type="flatbed"), OrderSpec(2, 500, 2)]
    v, o, d, t = problem(vehicles, orders, [(0.05, 0.0), (0.0, 0.05)])
    base = nearest_neighbour(v, o, d, t)
    assert served_by(base)[1] == 2 and check_plan(base, v, o) == []

    # Deliberately break the plan: move the route that carries the flatbed order onto the truck.
    flatbed_route = next(r for r in base.routes if any(s.order_id == 1 for s in r.stops))
    flatbed_route.vehicle_id = 1
    assert any("needs a 'flatbed' vehicle" in p for p in check_plan(base, v, o))


# ---------- API ----------

def test_api_accepts_only_known_types(client):
    vehicle = {"registration": "VH-T1", "weight_capacity_kg": 5000, "volume_capacity_m3": 20}
    assert client.post("/vehicles", json={**vehicle, "vehicle_type": "refrigerated"}).status_code == 201
    assert client.post("/vehicles", json={**vehicle, "registration": "VH-T2", "vehicle_type": "hovercraft"}).status_code == 400

    order = {"customer": "x", "address": "y", "latitude": 6.9, "longitude": 79.8, "weight_kg": 10,
             "volume_m3": 1, "target_date": "2026-10-14"}
    created = client.post("/orders", json={**order, "required_vehicle_type": "flatbed"}).get_json()
    assert created["required_vehicle_type"] == "flatbed"
    assert client.post("/orders", json={**order, "required_vehicle_type": "boat"}).status_code == 400
    cleared = client.patch(f"/orders/{created['id']}", json={"required_vehicle_type": None}).get_json()
    assert cleared["required_vehicle_type"] is None


def test_csv_import_reads_the_vehicle_type_column(client):
    header = "customer,address,latitude,longitude,weight_kg,volume_m3,target_date,required_vehicle_type"
    ok = client.post("/orders/import", data=f"{header}\nA,1 Rd,6.9,79.8,10,1,2026-10-14,Refrigerated\nB,2 Rd,6.9,79.8,10,1,2026-10-14,\n".encode(),
                     content_type="text/csv")
    assert ok.status_code == 201
    types = {o["customer"]: o["required_vehicle_type"] for o in client.get("/orders").get_json()["items"]}
    assert types == {"A": "refrigerated", "B": None}                     # case-insensitive, blank = any
    bad = client.post("/orders/import", data=f"{header}\nC,3 Rd,6.9,79.8,10,1,2026-10-14,spaceship\n".encode(), content_type="text/csv")
    assert bad.status_code == 400 and "required_vehicle_type" in bad.get_json()["errors"][0]["errors"]


def test_full_plan_on_seed_data_respects_every_type(app, client):
    seed(date(2026, 10, 14))
    pid = client.post("/plans/generate", json={"date": "2026-10-14", "time_limit_s": 3}).get_json()["id"]
    plan = client.get(f"/plans/{pid}").get_json()
    assert plan["status"] == "ready"

    orders = {o["id"]: o for o in client.get("/orders?per_page=100").get_json()["items"]}
    vehicles = {v["id"]: v for v in client.get("/vehicles?per_page=100").get_json()["items"]}
    constrained = 0
    for route in plan["routes"]:
        for stop in route["stops"]:
            need = orders[stop["order_id"]]["required_vehicle_type"]
            if need:
                constrained += 1
                assert vehicles[route["vehicle"]["id"]]["vehicle_type"] == need
    assert constrained > 0   # the sample data really contains constrained orders, and they were served
