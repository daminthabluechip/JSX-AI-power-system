"""/plans endpoints: generate a plan and read it back."""
from datetime import date

from flask import Blueprint, current_app, jsonify, request

from ..extensions import db
from ..models import Depot, Order, Plan, Vehicle
from ..services.plan_service import create_plan, start_plan
from .helpers import ValidationError, fmt_time, parse_date

bp = Blueprint("plans", __name__, url_prefix="/plans")

RESCHEDULE_MIN = 5   # an arrival time must move by at least this many minutes to count as a change


def plan_summary(p):
    """The figures shown at the top of a plan (without routes)."""
    saved = None
    if p.baseline_distance_km and p.total_distance_km is not None:
        saved = round(100 * (1 - p.total_distance_km / p.baseline_distance_km), 1)
    return {
        "id": p.id,
        "planning_date": p.planning_date.isoformat(),
        "version": p.version,
        "status": p.status,
        "error": p.error,
        "total_distance_km": p.total_distance_km,
        "total_time_min": p.total_time_min,
        "solve_time_s": p.solve_time_s,
        "baseline_distance_km": p.baseline_distance_km,
        "distance_saved_pct": saved,  # vs. the nearest-neighbour baseline
    }


def plan_detail(p):
    """Full plan: summary + one entry per vehicle route with its ordered stops."""
    vehicles = {v.id: v for v in Vehicle.query.filter(Vehicle.id.in_([r.vehicle_id for r in p.routes]))}
    order_ids = [s.order_id for r in p.routes for s in r.stops] + [u["order_id"] for u in (p.unassigned or [])]
    orders = {o.id: o for o in Order.query.filter(Order.id.in_(order_ids))}

    depot = Depot.query.first()
    depot_xy = [depot.latitude, depot.longitude] if depot else None
    routes = []
    for r in p.routes:
        v = vehicles[r.vehicle_id]
        start = [r.start_latitude, r.start_longitude] if r.start_latitude is not None else depot_xy
        stop_xy = [[orders[s.order_id].latitude, orders[s.order_id].longitude] for s in r.stops]
        routes.append({
            # start point -> each stop in order -> back to the depot (for drawing the route on a map)
            "path": ([start] + stop_xy + [depot_xy]) if depot_xy else stop_xy,
            "id": r.id,
            "vehicle": {"id": v.id, "registration": v.registration, "model": v.model, "driver": v.driver,
                        "vehicle_type": v.vehicle_type, "weight_capacity_kg": v.weight_capacity_kg,
                        "volume_capacity_m3": v.volume_capacity_m3},
            "planned_departure": r.planned_departure.strftime("%H:%M"),
            "return_time": r.return_time.strftime("%H:%M") if r.return_time else None,
            "distance_km": r.distance_km,
            "load_kg": r.load_kg,
            "volume_m3": r.volume_m3,
            # how full the vehicle is, as a percentage of its capacity
            "weight_utilization_pct": round(100 * r.load_kg / v.weight_capacity_kg, 1),
            "volume_utilization_pct": round(100 * r.volume_m3 / v.volume_capacity_m3, 1),
            "stops": [{
                "sequence": s.sequence,
                "order_id": s.order_id,
                "customer": orders[s.order_id].customer,
                "address": orders[s.order_id].address,
                "latitude": orders[s.order_id].latitude,
                "longitude": orders[s.order_id].longitude,
                "priority": orders[s.order_id].priority,
                # what the customer asked for, so a route can be explained against it
                "window_start": fmt_time(orders[s.order_id].earliest_arrival),
                "window_end": fmt_time(orders[s.order_id].latest_arrival),
                "weight_kg": orders[s.order_id].weight_kg,
                "required_vehicle_type": orders[s.order_id].required_vehicle_type,
                "planned_arrival": s.planned_arrival.strftime("%H:%M"),
                "planned_departure": s.planned_departure.strftime("%H:%M"),
            } for s in r.stops],
        })

    unassigned = [{**u, "customer": orders[u["order_id"]].customer,
                   "priority": orders[u["order_id"]].priority} for u in (p.unassigned or [])]
    return {**plan_summary(p), "depot": ({"name": depot.name, "latitude": depot.latitude, "longitude": depot.longitude}
                                          if depot else None),
            "routes": routes, "unassigned": unassigned}


@bp.post("/generate")
def generate():
    """POST /plans/generate {date?, vehicle_ids?, order_ids?, time_limit_s?}

    Returns 202 immediately with the plan id; poll GET /plans/<id> until status is
    "ready" (or "failed").
    """
    body = request.get_json(silent=True) or {}
    try:
        day = parse_date(body["date"]) if body.get("date") else date.today()
    except ValueError:
        raise ValidationError({"date": "expected YYYY-MM-DD"})
    for key in ("vehicle_ids", "order_ids"):
        if key in body and not (isinstance(body[key], list) and all(isinstance(i, int) for i in body[key])):
            raise ValidationError({key: "expected a list of ids"})

    plan = create_plan(day)
    start_plan(current_app._get_current_object(), plan, body.get("vehicle_ids"),
               body.get("order_ids"), body.get("time_limit_s"))
    db.session.refresh(plan)
    return jsonify(plan_summary(plan)), 202


@bp.get("")
def list_plans():
    """GET /plans?date= - newest first."""
    query = Plan.query.order_by(Plan.id.desc())
    if day := request.args.get("date"):
        query = query.filter(Plan.planning_date == day)
    return jsonify(items=[plan_summary(p) for p in query.limit(50)])


@bp.get("/<int:plan_id>")
def get_plan(plan_id):
    """GET /plans/<id> - the plan with routes, stops, arrival times and vehicle utilization."""
    return jsonify(plan_detail(db.get_or_404(Plan, plan_id)))


def assignments(p):
    """order_id -> where the plan serves it (vehicle, stop number, arrival)."""
    out = {}
    for r in p.routes:
        reg = db.session.get(Vehicle, r.vehicle_id).registration
        for s in r.stops:
            out[s.order_id] = {"vehicle": reg, "sequence": s.sequence,
                               "arrival": s.planned_arrival.strftime("%H:%M")}
    return out


@bp.get("/<int:plan_id>/compare/<int:other_id>")
def compare_plans(plan_id, other_id):
    """GET /plans/<a>/compare/<b> - what changed going from plan a (before) to plan b (after).

    Each order is classified as: unchanged, rescheduled (same vehicle, arrival time moved by
    RESCHEDULE_MIN or more), reassigned (different vehicle), dropped (was served, now
    unassigned), completed (already delivered, so no longer planned), removed (no longer in the
    plan, e.g. cancelled), now_assigned or added. Stop numbers are ignored on purpose: they
    shift whenever earlier stops are delivered, without anything really changing.
    """
    a, b = db.get_or_404(Plan, plan_id), db.get_or_404(Plan, other_id)
    before, after = assignments(a), assignments(b)
    unassigned_after = {u["order_id"] for u in (b.unassigned or [])}
    unassigned_before = {u["order_id"] for u in (a.unassigned or [])}

    delivered = {o.id for o in Order.query.filter(Order.id.in_(set(before) - set(after)),
                                                  Order.status == "delivered")}

    def clock(text):
        return int(text[:2]) * 60 + int(text[3:])

    changes, unchanged = [], 0
    for oid in sorted(set(before) | set(after) | unassigned_after):
        was, now = before.get(oid), after.get(oid)
        if was and now:
            if was["vehicle"] != now["vehicle"]:
                kind = "reassigned"
            elif abs(clock(was["arrival"]) - clock(now["arrival"])) >= RESCHEDULE_MIN:
                kind = "rescheduled"
            else:
                unchanged += 1
                continue
        elif was:
            if oid in unassigned_after:
                kind = "dropped"
            else:
                kind = "completed" if oid in delivered else "removed"
        elif now:
            kind = "now_assigned" if oid in unassigned_before else "added"
        else:
            continue  # unassigned in both plans: nothing changed
        changes.append({"order_id": oid, "change": kind, "before": was, "after": now})

    names = {o.id: o.customer for o in Order.query.filter(Order.id.in_([c["order_id"] for c in changes]))}
    for c in changes:
        c["customer"] = names.get(c["order_id"])

    def delta(x, y):
        return None if x is None or y is None else round(y - x, 2)

    return jsonify(
        before=plan_summary(a), after=plan_summary(b),
        distance_delta_km=delta(a.total_distance_km, b.total_distance_km),
        time_delta_min=delta(a.total_time_min, b.total_time_min),
        vehicles_used={"before": len(a.routes), "after": len(b.routes)},
        unassigned={"before": len(unassigned_before), "after": len(unassigned_after)},
        unchanged_orders=unchanged, changes=changes,
    )


@bp.post("/<int:plan_id>/dispatch")
def dispatch_plan(plan_id):
    """POST /plans/<id>/dispatch - send a finished plan to the vehicles.

    Marks the plan "dispatched", the vehicles it uses "on_route" and its orders "in_transit".
    TODO: TOOL/API CALL HERE - notify drivers / the JXG tracking system once that integration exists.
    """
    plan = db.get_or_404(Plan, plan_id)
    if plan.status != "ready":
        return jsonify(error="conflict", details={"status": f"plan is {plan.status}, only ready plans can be dispatched"}), 409
    # A newly dispatched plan replaces whichever plan was being executed for that date.
    for old in Plan.query.filter_by(status="dispatched", planning_date=plan.planning_date):
        old.status = "superseded"
        for route in old.routes:   # vehicles the new plan no longer uses go back to the pool
            vehicle = db.session.get(Vehicle, route.vehicle_id)
            if vehicle.status == "on_route":
                vehicle.status = "available"
    for route in plan.routes:
        db.session.get(Vehicle, route.vehicle_id).status = "on_route"
        for stop in route.stops:
            db.session.get(Order, stop.order_id).status = "in_transit"
    plan.status = "dispatched"
    db.session.commit()
    return jsonify(plan_summary(plan))
