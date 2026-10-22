from datetime import date

from app.extensions import db
from app.models import Plan
from seed.seed_data import seed

DAY = "2026-10-14"


def vehicles_by_reg(client):
    return {v["registration"]: v for v in client.get("/vehicles?per_page=100").get_json()["items"]}


def plan_with_few_vehicles(client, regs=("VH-5120",), **extra):
    seed(date(2026, 10, 14))
    ids = [vehicles_by_reg(client)[r]["id"] for r in regs]
    res = client.post("/plans/generate", json={"date": DAY, "vehicle_ids": ids, "time_limit_s": 2, **extra})
    return client.get(f"/plans/{res.get_json()['id']}").get_json(), ids


def notes(client):
    return client.get("/notifications").get_json()["items"]


def test_notifies_about_vehicles_the_plan_did_not_consider(client):
    plan, used = plan_with_few_vehicles(client)
    assert plan["unassigned"] and plan["status"] == "ready"
    items = notes(client)
    assert items

    regs = {n["vehicle"]["registration"] for n in items}
    assert "VH-5120" not in regs
    assert "VH-2275" not in regs and "VH-2048" not in regs
    for n in items:
        assert n["plan_id"] == plan["id"] and n["orders"]
        assert n["suggested_event"] == {"type": "vehicle_available", "vehicle_id": n["vehicle"]["id"]}
        assert "unassigned" in n["message"] and n["vehicle"]["registration"] in n["message"]


def test_only_orders_the_vehicle_can_carry_are_listed(client):
    plan, _ = plan_with_few_vehicles(client)
    orders = {o["id"]: o for o in client.get("/orders?per_page=100").get_json()["items"]}
    for n in notes(client):
        v = n["vehicle"]
        for o in n["orders"]:
            full = orders[o["order_id"]]
            assert full["weight_kg"] <= v["weight_capacity_kg"]
            need = full["required_vehicle_type"]
            assert need is None or need == v["vehicle_type"]


def test_vehicle_type_rule_decides_who_is_told(client):
    seed(date(2026, 10, 14))
    ids = [vehicles_by_reg(client)["VH-5120"]["id"]]
    only = client.post("/orders", json={"customer": "Cold Chain Ltd", "address": "x", "latitude": 6.93, "longitude": 79.86,
                                        "weight_kg": 300, "volume_m3": 2, "target_date": DAY,
                                        "required_vehicle_type": "refrigerated"}).get_json()
    res = client.post("/plans/generate", json={"date": DAY, "vehicle_ids": ids, "order_ids": [only["id"]], "time_limit_s": 2})
    plan = client.get(f"/plans/{res.get_json()['id']}").get_json()
    assert [u["order_id"] for u in plan["unassigned"]] == [only["id"]]

    types = {n["vehicle"]["vehicle_type"] for n in notes(client)}
    assert types == {"refrigerated"}


def test_a_vehicle_leaving_maintenance_triggers_a_notice(client):
    plan, _ = plan_with_few_vehicles(client)
    assert "VH-2275" not in {n["vehicle"]["registration"] for n in notes(client)}
    vid = vehicles_by_reg(client)["VH-2275"]["id"]
    client.patch(f"/vehicles/{vid}", json={"status": "available"})
    assert "VH-2275" in {n["vehicle"]["registration"] for n in notes(client)}


def test_a_new_vehicle_triggers_a_notice(client):
    plan_with_few_vehicles(client)
    before = {n["vehicle"]["registration"] for n in notes(client)}
    client.post("/vehicles", json={"registration": "VH-NEW1", "weight_capacity_kg": 15000, "volume_capacity_m3": 40,
                                    "vehicle_type": "truck"})
    after = {n["vehicle"]["registration"] for n in notes(client)}
    assert after - before == {"VH-NEW1"}


def test_no_notice_when_everything_was_planned(client):
    seed(date(2026, 10, 14))
    ids = [o["id"] for o in client.get("/orders?per_page=3").get_json()["items"]]
    res = client.post("/plans/generate", json={"date": DAY, "order_ids": ids, "time_limit_s": 2})
    plan = client.get(f"/plans/{res.get_json()['id']}").get_json()
    assert plan["unassigned"] == [] and notes(client) == []


def test_old_plans_without_a_vehicle_list_stay_quiet(client):
    plan, _ = plan_with_few_vehicles(client)
    assert notes(client)
    db.session.get(Plan, plan["id"]).vehicle_ids = None
    db.session.commit()
    assert notes(client) == []


def test_replanning_with_the_vehicle_uses_it_and_clears_the_notice(client):
    plan, _ = plan_with_few_vehicles(client)
    note = next(n for n in notes(client) if n["vehicle"]["registration"] == "VH-1189")

    res = client.post("/events", json=note["suggested_event"])
    assert res.status_code == 202
    new = client.get(f"/plans/{res.get_json()['plan']['id']}").get_json()

    assert new["status"] == "ready" and new["version"] == plan["version"] + 1
    assert note["vehicle"]["id"] in {r["vehicle"]["id"] for r in new["routes"]}
    assert len(new["unassigned"]) < len(plan["unassigned"])
    assert note["vehicle"]["registration"] not in {n["vehicle"]["registration"] for n in notes(client)}


def test_vehicle_available_event_validation(client):
    plan_with_few_vehicles(client)
    reg = vehicles_by_reg(client)
    assert client.post("/events", json={"type": "vehicle_available"}).status_code == 400
    assert client.post("/events", json={"type": "vehicle_available", "vehicle_id": 99999}).status_code == 400
    broken = client.post("/events", json={"type": "vehicle_available", "vehicle_id": reg["VH-2275"]["id"]})
    assert broken.status_code == 409 and "maintenance" in broken.get_json()["details"]["vehicle_id"]
