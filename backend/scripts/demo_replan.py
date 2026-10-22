import argparse
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from seed.seed_data import reset, seed  # noqa: E402


class DemoConfig(Config):
    PLAN_SYNC = True


def line(text=""):
    print(text, flush=True)


def show(label, plan, elapsed):
    saved = plan["distance_saved_pct"]
    line(f"  {label}: plan v{plan['version']} (id {plan['id']}) {plan['status']} in {elapsed:.1f}s | "
         f"{len(plan['routes'])} vehicles, {plan['total_distance_km']} km, "
         f"{len(plan['unassigned'])} unassigned" + (f", {saved}% shorter than baseline" if saved is not None else ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reseed", action="store_true", help="wipe and reload the sample data first")
    args = parser.parse_args()

    app = create_app(DemoConfig)
    with app.app_context():
        if args.reseed:
            reset()
            seed()
            line("Sample data reloaded.")
        client = app.test_client()
        checks = []

        line("\n1. Generate the day's plan")
        t0 = time.time()
        res = client.post("/plans/generate", json={"date": date.today().isoformat()})
        elapsed = time.time() - t0
        plan = client.get(f"/plans/{res.get_json()['id']}").get_json()
        if plan["status"] != "ready":
            line(f"  FAILED: {plan['error']}")
            return 1
        show("initial plan", plan, elapsed)
        checks.append(("Plan generated in 30 s or less", elapsed <= 30, f"{elapsed:.1f}s"))

        busiest = max(plan["routes"], key=lambda r: len(r["stops"]))
        some_stop = plan["routes"][-1]["stops"][0]

        disruptions = [
            ("2. DELAY: " + busiest["vehicle"]["registration"] + " is stuck for 60 minutes",
             {"type": "delay", "vehicle_id": busiest["vehicle"]["id"], "delay_minutes": 60}),
            ("3. RUSH ORDER: urgent medical delivery in Kandy",
             {"type": "rush_order", "order": {
                 "customer": "Summit Medical (RUSH)", "address": "Hospital Rd, Kandy",
                 "latitude": 7.2906, "longitude": 80.6337, "weight_kg": 400, "volume_m3": 2,
                 "priority": "critical", "earliest_arrival": "09:00", "latest_arrival": "15:00"}}),
            ("4. CANCELLATION: " + some_stop["customer"] + " cancels",
             {"type": "cancellation", "order_id": some_stop["order_id"]}),
            ("5. BREAKDOWN: " + busiest["vehicle"]["registration"] + " breaks down",
             {"type": "breakdown", "vehicle_id": busiest["vehicle"]["id"]}),
        ]
        slowest = 0.0
        previous = plan
        for title, body in disruptions:
            line("\n" + title)
            t0 = time.time()
            res = client.post("/events", json=body)
            elapsed = time.time() - t0
            if res.status_code != 202:
                line(f"  FAILED ({res.status_code}): {res.get_json()}")
                return 1
            new = client.get(f"/plans/{res.get_json()['plan']['id']}").get_json()
            show("re-plan", new, elapsed)
            slowest = max(slowest, elapsed)

            diff = client.get(f"/plans/{previous['id']}/compare/{new['id']}").get_json()
            kinds = {}
            for c in diff["changes"]:
                kinds[c["change"]] = kinds.get(c["change"], 0) + 1
            line(f"  changes vs v{previous['version']}: {kinds or 'none'}; {diff['unchanged_orders']} orders unchanged; "
                 f"distance {diff['distance_delta_km']:+} km")
            previous = new

        checks.append(("Re-plan in 15 s or less (slowest of 4)", slowest <= 15, f"{slowest:.1f}s"))
        checks.append(("Final plan has no unassigned reasons missing",
                       all(u["reason"] for u in previous["unassigned"]), f"{len(previous['unassigned'])} unassigned"))
        line("\nTargets")
        for name, ok, detail in checks:
            line(f"  [{'PASS' if ok else 'FAIL'}] {name} ({detail})")
        return 0 if all(ok for _, ok, _ in checks) else 2


if __name__ == "__main__":
    sys.exit(main())
