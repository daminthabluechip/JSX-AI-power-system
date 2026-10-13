from datetime import date

from app.extensions import db
from app.models import Order, Stop
from app.simulator.engine import Simulator
from seed.seed_data import seed

DAY = date(2026, 10, 14)


def hm(text):
    h, m = map(int, text.split(":"))
    return h * 60 + m


def run_day(app, client, delay_vehicle_minutes=0):
    """Seed, plan, dispatch and simulate the whole day (optionally with one badly delayed vehicle)."""
    seed(DAY)
    pid = client.post("/plans/generate", json={"date": DAY.isoformat(), "time_limit_s": 2}).get_json()["id"]
    client.post(f"/plans/{pid}/dispatch")
    plan = client.get(f"/plans/{pid}").get_json()
    sim = Simulator()
    start = min(hm(r["planned_departure"]) for r in plan["routes"]) - 5
    busiest = max(plan["routes"], key=lambda r: len(r["stops"]))["vehicle"]["id"]
    if delay_vehicle_minutes:
        sim.delays[busiest] = [(start, delay_vehicle_minutes)]
    for t in range(start, 23 * 60 + 1, 20):      # a position report every 20 simulated minutes
        sim.tick(app.config, t)
    return plan, busiest


def report(client, **params):
    q = "&".join(f"{k}={v}" for k, v in {"days": 1, "today": DAY.isoformat(), **params}.items())
    return client.get(f"/reports?{q}").get_json()


def test_report_without_data_is_empty_not_invented(client):
    r = report(client)
    assert r["daily"] == [] and r["kpis"]["on_time_pct"] is None and r["kpis"]["planned_km"] is None
    assert r["insights"] == []


def test_on_time_day_reports_everything_on_time(app, client):
    plan, _ = run_day(app, client)
    r = report(client)
    k = r["kpis"]
    assert k["on_time_pct"] == 100 and k["late_deliveries"] == 0
    assert k["measured_deliveries"] == sum(len(x["stops"]) for x in plan["routes"])
    assert k["planned_km"] == plan["total_distance_km"]
    assert k["distance_saved_pct"] == plan["distance_saved_pct"]
    assert k["utilization_pct"] > 0
    assert r["daily"][0]["delivered"] == k["measured_deliveries"]
    assert {i["title"] for i in r["insights"]} >= {"Route efficiency", "On-time performance", "Capacity opportunity"}


def test_a_long_delay_shows_up_as_late_deliveries(app, client):
    run_day(app, client, delay_vehicle_minutes=240)
    r = report(client)

    # cross-check the reported count against the raw data
    late = 0
    for stop, order in db.session.query(Stop, Order).join(Order, Stop.order_id == Order.id).filter(Stop.actual_arrival.isnot(None)):
        if order.latest_arrival and stop.actual_arrival.hour * 60 + stop.actual_arrival.minute > order.latest_arrival.hour * 60 + order.latest_arrival.minute:
            late += 1
    assert late > 0
    assert r["kpis"]["late_deliveries"] == late
    assert r["kpis"]["on_time_pct"] < 100 and r["kpis"]["avg_delay_min"] > 0
    assert any(i["title"] == "Late deliveries" for i in r["insights"])


def test_range_and_csv_export(app, client):
    run_day(app, client)
    assert report(client, days=7)["kpis"]["planned_km"] == report(client, days=1)["kpis"]["planned_km"]
    assert report(client, today="2026-12-01")["daily"] == []          # the day is outside the range

    res = client.get(f"/reports/export?days=1&today={DAY.isoformat()}")
    assert res.status_code == 200 and res.mimetype == "text/csv"
    lines = res.get_data(as_text=True).strip().splitlines()
    assert lines[0].startswith("date,orders,delivered") and lines[1].startswith("2026-10-14,50,")


def test_report_validates_params(client):
    assert client.get("/reports?days=0").status_code == 400
    assert client.get("/reports?days=999").status_code == 400
    assert client.get("/reports?today=tomorrow").status_code == 400
