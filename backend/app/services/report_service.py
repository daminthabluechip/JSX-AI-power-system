"""Numbers for the Reports page: delivery performance, distance, utilization and insights.

Everything is computed from stored data:
  * the plan of record for each day (dispatched one if there is one, else the newest finished one)
  * delivered orders, and stops with a recorded actual arrival time (from tracking)
No figure is invented: where there is no data the value is None and the page says so.
"""
from datetime import date, timedelta

from ..extensions import db
from ..models import Order, Plan, Route, Stop, Vehicle

ON_TIME_GRACE_MIN = 0   # arriving after the customer's latest time by more than this = late


def minutes(dt_or_time):
    """datetime or time -> minutes since midnight."""
    return dt_or_time.hour * 60 + dt_or_time.minute


def plan_of_record(day):
    """The plan that counts for a day: the newest dispatched plan, else the newest finished one."""
    dispatched = Plan.query.filter_by(planning_date=day, status="dispatched").order_by(Plan.id.desc()).first()
    if dispatched:
        return dispatched
    return (Plan.query.filter(Plan.planning_date == day, Plan.status.in_(["ready", "superseded"]))
            .order_by(Plan.id.desc()).first())


def delivery_timing(day):
    """On-time statistics for stops with a recorded arrival on this day -> (measured, late, delays)."""
    rows = (db.session.query(Stop, Order).join(Route, Stop.route_id == Route.id)
            .join(Plan, Route.plan_id == Plan.id).join(Order, Stop.order_id == Order.id)
            .filter(Plan.planning_date == day, Stop.actual_arrival.isnot(None)).all())
    seen, late, delays = set(), 0, []
    for stop, order in rows:
        if order.id in seen:   # the same order can be on several plan versions; count it once
            continue
        seen.add(order.id)
        if order.latest_arrival and minutes(stop.actual_arrival) > minutes(order.latest_arrival) + ON_TIME_GRACE_MIN:
            late += 1
        delays.append(max(0.0, (stop.actual_arrival - stop.planned_arrival).total_seconds() / 60))
    return len(seen), late, delays


def build_report(days=30, today=None):
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    daily, measured_total, late_total, delays_all = [], 0, 0, []
    util_by_vehicle = {}   # vehicle -> [weight utilization %, volume utilization %] lists
    unassigned_total = 0

    for offset in range(days):
        day = start + timedelta(days=offset)
        orders = Order.query.filter(Order.target_date == day, Order.status != "cancelled").all()
        plan = plan_of_record(day)
        if not orders and plan is None:
            continue

        measured, late, delays = delivery_timing(day)
        measured_total += measured
        late_total += late
        delays_all += delays

        utilization = None
        if plan and plan.routes:
            weights = []
            for r in plan.routes:
                v = db.session.get(Vehicle, r.vehicle_id)
                w, vol = 100 * r.load_kg / v.weight_capacity_kg, 100 * r.volume_m3 / v.volume_capacity_m3
                weights.append(w)
                util_by_vehicle.setdefault(v.registration, []).append((w, vol))
            utilization = round(sum(weights) / len(weights), 1)
        if plan:
            unassigned_total += len(plan.unassigned or [])

        daily.append({
            "date": day.isoformat(),
            "orders": len(orders),
            "delivered": sum(1 for o in orders if o.status == "delivered"),
            "late": late,
            "on_time_pct": round(100 * (measured - late) / measured, 1) if measured else None,
            "planned_km": plan.total_distance_km if plan else None,
            "baseline_km": plan.baseline_distance_km if plan else None,
            "utilization_pct": utilization,
            "plan_id": plan.id if plan else None,
        })

    km = [d["planned_km"] for d in daily if d["planned_km"] is not None]
    base = [d["baseline_km"] for d in daily if d["baseline_km"] is not None]
    util = [d["utilization_pct"] for d in daily if d["utilization_pct"] is not None]
    saved = round(100 * (1 - sum(km) / sum(base)), 1) if km and base and sum(base) else None

    kpis = {
        "on_time_pct": round(100 * (measured_total - late_total) / measured_total, 1) if measured_total else None,
        "measured_deliveries": measured_total,
        "late_deliveries": late_total,
        "avg_delay_min": round(sum(delays_all) / len(delays_all), 1) if delays_all else None,
        "utilization_pct": round(sum(util) / len(util), 1) if util else None,
        "planned_km": round(sum(km), 2) if km else None,
        "distance_saved_pct": saved,
        "delivered": sum(d["delivered"] for d in daily),
        "orders": sum(d["orders"] for d in daily),
    }
    return {"from": start.isoformat(), "to": today.isoformat(), "days": days, "kpis": kpis, "daily": daily,
            "insights": insights(kpis, util_by_vehicle, unassigned_total, delays_all)}


def insights(kpis, util_by_vehicle, unassigned_total, delays):
    """Plain, rule-based observations drawn from the figures above (no AI model involved)."""
    out = []

    if kpis["distance_saved_pct"] is not None:
        out.append({"title": "Route efficiency",
                    "text": f"Optimized plans are {kpis['distance_saved_pct']}% shorter than a nearest-neighbour "
                            f"plan over {kpis['planned_km']} km of planned driving.",
                    "link": {"label": "Compare plans", "href": "/optimization"}})

    if kpis["measured_deliveries"]:
        if kpis["late_deliveries"]:
            out.append({"title": "Late deliveries",
                        "text": f"{kpis['late_deliveries']} of {kpis['measured_deliveries']} tracked deliveries "
                                f"arrived after the customer's window (average delay {kpis['avg_delay_min']} min).",
                        "link": {"label": "View live tracking", "href": "/live-tracking"}})
        else:
            out.append({"title": "On-time performance",
                        "text": f"All {kpis['measured_deliveries']} tracked deliveries arrived within the customer's window.",
                        "link": {"label": "View live tracking", "href": "/live-tracking"}})

    if util_by_vehicle:
        avg = {reg: (sum(w for w, _ in v) / len(v), sum(x for _, x in v) / len(v)) for reg, v in util_by_vehicle.items()}
        lowest = min(avg, key=lambda r: avg[r][0])
        mean_w = sum(w for w, _ in avg.values()) / len(avg)
        mean_v = sum(x for _, x in avg.values()) / len(avg)
        limiter = ("volume is the main limit" if mean_v > mean_w + 10
                   else "weight is the main limit" if mean_w > mean_v + 10
                   else "weight and volume are both close to their limits")
        out.append({"title": "Capacity opportunity",
                    "text": f"Vehicles carry {mean_w:.0f}% of their weight and {mean_v:.0f}% of their volume capacity "
                            f"on average, so {limiter}. {lowest} is the least loaded "
                            f"({avg[lowest][0]:.0f}% by weight): consolidating its orders could free a vehicle.",
                    "link": {"label": "Plan routes", "href": "/route-planning"}})

    if unassigned_total:
        out.append({"title": "Orders left unassigned",
                    "text": f"{unassigned_total} order(s) could not be fitted into a plan. Adding vehicles or "
                            f"widening time windows would let the optimizer serve them.",
                    "link": {"label": "View deliveries", "href": "/deliveries"}})
    return out


def report_csv(report):
    """The daily table as CSV text (for the Export report button)."""
    cols = ["date", "orders", "delivered", "late", "on_time_pct", "planned_km", "baseline_km", "utilization_pct"]
    lines = [",".join(cols)]
    for row in report["daily"]:
        lines.append(",".join("" if row[c] is None else str(row[c]) for c in cols))
    return "\n".join(lines) + "\n"
