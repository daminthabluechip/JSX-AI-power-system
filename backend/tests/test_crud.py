from seed.seed_data import seed

VEHICLE = {"registration": "VH-1", "weight_capacity_kg": 10000, "volume_capacity_m3": 30,
           "shift_start": "07:00", "shift_end": "19:00"}
ORDER = {"customer": "ACME", "address": "1 Main St", "latitude": 6.9, "longitude": 79.8,
         "weight_kg": 500, "volume_m3": 2, "target_date": "2026-10-14",
         "earliest_arrival": "09:00", "latest_arrival": "12:00"}


def test_vehicle_crud_cycle(client):
    created = client.post("/vehicles", json=VEHICLE)
    assert created.status_code == 201
    vid = created.get_json()["id"]
    assert created.get_json()["status"] == "available"  # model default

    assert client.get(f"/vehicles/{vid}").get_json()["shift_start"] == "07:00"
    patched = client.patch(f"/vehicles/{vid}", json={"status": "maintenance"})
    assert patched.get_json()["status"] == "maintenance"
    assert client.get("/vehicles/summary").get_json()["maintenance"] == 1
    assert client.delete(f"/vehicles/{vid}").status_code == 204
    assert client.get(f"/vehicles/{vid}").status_code == 404


def test_vehicle_validation(client):
    bad = client.post("/vehicles", json={"registration": "X", "weight_capacity_kg": -5})
    assert bad.status_code == 400
    details = bad.get_json()["details"]
    assert "weight_capacity_kg" in details and "volume_capacity_m3" in details

    client.post("/vehicles", json=VEHICLE)
    assert client.post("/vehicles", json=VEHICLE).status_code == 409  # duplicate registration

    assert client.post("/vehicles", json={**VEHICLE, "registration": "V2", "status": "flying"}
                       ).status_code == 400


def test_order_crud_and_filters(client):
    created = client.post("/orders", json={**ORDER, "priority": "high"})
    assert created.status_code == 201
    oid = created.get_json()["id"]
    client.post("/orders", json={**ORDER, "customer": "Other", "priority": "low"})

    assert client.get("/orders?priority=high").get_json()["total"] == 1
    assert client.get("/orders?q=other").get_json()["total"] == 1
    assert client.patch(f"/orders/{oid}", json={"status": "cancelled"}).get_json()["status"] == "cancelled"
    assert client.delete(f"/orders/{oid}").status_code == 204


def test_order_rejects_bad_time_window_and_date(client):
    assert client.post("/orders", json={**ORDER, "earliest_arrival": "15:00",
                                        "latest_arrival": "09:00"}).status_code == 400
    assert client.post("/orders", json={**ORDER, "target_date": "not-a-date"}).status_code == 400
    # updating one side of the window is checked against the stored other side
    oid = client.post("/orders", json=ORDER).get_json()["id"]
    assert client.patch(f"/orders/{oid}", json={"latest_arrival": "08:00"}).status_code == 400


def test_seed_loads_expected_counts(app, client):
    seed()
    assert client.get("/vehicles?per_page=100").get_json()["total"] == 10
    assert client.get("/orders?per_page=100").get_json()["total"] == 50
    assert client.get("/vehicles/summary").get_json()["maintenance"] == 1


def test_cannot_delete_vehicle_or_order_that_plans_refer_to(app, client):
    from datetime import date
    seed(date(2026, 10, 14))
    plan = client.get("/plans/%d" % client.post("/plans/generate", json={"date": "2026-10-14", "time_limit_s": 1}).get_json()["id"]).get_json()
    used_vehicle = plan["routes"][0]["vehicle"]["id"]
    used_order = plan["routes"][0]["stops"][0]["order_id"]

    res = client.delete(f"/vehicles/{used_vehicle}")
    assert res.status_code == 409 and "maintenance" in res.get_json()["details"]["message"]
    res = client.delete(f"/orders/{used_order}")
    assert res.status_code == 409 and "Cancel" in res.get_json()["details"]["message"]
    assert client.get(f"/vehicles/{used_vehicle}").status_code == 200   # still there

    # unused ones can still be deleted
    unused = client.post("/vehicles", json=VEHICLE).get_json()["id"]
    assert client.delete(f"/vehicles/{unused}").status_code == 204


def test_edit_can_clear_optional_fields_but_not_required_ones(client):
    """The edit forms send null for a cleared field."""
    vid = client.post("/vehicles", json={**VEHICLE, "driver": "Nimal", "model": "Volvo"}).get_json()["id"]
    cleared = client.patch(f"/vehicles/{vid}", json={"driver": None, "model": "", "status": "maintenance"}).get_json()
    assert cleared["driver"] is None and cleared["status"] == "maintenance"

    bad = client.patch(f"/vehicles/{vid}", json={"weight_capacity_kg": None})
    assert bad.status_code == 400 and "weight_capacity_kg" in bad.get_json()["details"]

    oid = client.post("/orders", json=ORDER).get_json()["id"]
    cleared = client.patch(f"/orders/{oid}", json={"earliest_arrival": None, "latest_arrival": None}).get_json()
    assert cleared["earliest_arrival"] is None and cleared["latest_arrival"] is None
