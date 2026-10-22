from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request

from ..extensions import db
from ..models import Event, Order, Plan, Route, Vehicle
from ..services import tracking_service as tracking
from ..services.plan_service import create_plan, minutes, start_plan
from .helpers import ValidationError, clean_payload
from .orders import SPEC as ORDER_SPEC
from .orders import check_window
from .plans import plan_summary

bp = Blueprint("events", __name__, url_prefix="/events")

TYPES = ["delay", "breakdown", "rush_order", "cancellation", "vehicle_available"]


def event_to_dict(e):
    return {
        "id": e.id,
        "type": e.type,
        "vehicle_id": e.vehicle_id,
        "order_id": e.order_id,
        "delay_minutes": e.delay_minutes,
        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        "handled_by_plan_id": e.handled_by_plan_id,
    }


def as_id(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def fail(field, message, status=400):
    return jsonify(error="validation_failed", details={field: message}), status


def apply_event(body, plan):
    kind = body.get("type")
    event = Event(type=kind)
    overrides = {}

    if kind in ("delay", "breakdown"):
        vehicle = db.session.get(Vehicle, as_id(body.get("vehicle_id"))) if as_id(body.get("vehicle_id")) else None
        if vehicle is None:
            return None, fail("vehicle_id", "existing vehicle required")
        event.vehicle_id = vehicle.id

        if kind == "breakdown":
            vehicle.status = "maintenance"
        else:
            delay = body.get("delay_minutes")
            if not isinstance(delay, int) or delay <= 0:
                return None, fail("delay_minutes", "positive whole number required")
            event.delay_minutes = delay
            route = Route.query.filter_by(plan_id=plan.id, vehicle_id=vehicle.id).first()
            base = (route.planned_departure.hour * 60 + route.planned_departure.minute
                    if route else minutes(vehicle.shift_start, 7 * 60))
            overrides[vehicle.id] = base + delay

    elif kind == "vehicle_available":
        vehicle = db.session.get(Vehicle, as_id(body.get("vehicle_id"))) if as_id(body.get("vehicle_id")) else None
        if vehicle is None:
            return None, fail("vehicle_id", "existing vehicle required")
        if vehicle.status != "available":
            return None, fail("vehicle_id", f"vehicle is {vehicle.status}, not available", 409)
        event.vehicle_id = vehicle.id

    elif kind == "cancellation":
        order = db.session.get(Order, as_id(body.get("order_id"))) if as_id(body.get("order_id")) else None
        if order is None:
            return None, fail("order_id", "existing order required")
        if order.status in ("delivered", "cancelled"):
            return None, fail("order_id", f"order is already {order.status}", 409)
        order.status = "cancelled"
        event.order_id = order.id

    elif kind == "rush_order":
        payload = {"priority": "high", "target_date": plan.planning_date.isoformat(), **(body.get("order") or {})}
        data = clean_payload(payload, ORDER_SPEC)
        bad = check_window(data)
        if bad:
            return None, bad
        order = Order(**data)
        db.session.add(order)
        db.session.flush()
        event.order_id = order.id

    else:
        return None, fail("type", f"must be one of {TYPES}")

    db.session.add(event)
    return event, overrides


def live_replan_inputs(previous, event, overrides):
    live_plan = tracking.dispatched_plan()
    if live_plan is None or live_plan.planning_date != previous.planning_date:
        return None
    plans = [live_plan] if live_plan.id == previous.id else [live_plan, previous]
    now_min, starts = tracking.replan_context([p.id for p in plans])

    in_plans = {r.vehicle_id for p in plans for r in p.routes}
    vehicle_ids = sorted(v.id for v in Vehicle.query.filter(Vehicle.status != "maintenance")
                         if v.id in in_plans or v.status == "available")

    wanted = {s.order_id for r in previous.routes for s in r.stops}
    wanted |= {u["order_id"] for u in (previous.unassigned or [])}
    if event.type == "rush_order" and event.order_id:
        wanted.add(event.order_id)
    order_ids = sorted(o.id for o in Order.query.filter(Order.id.in_(wanted),
                                                        Order.status.notin_(["delivered", "cancelled"])))

    if now_min is not None:
        for vid in vehicle_ids:
            overrides[vid] = max(overrides.get(vid, 0), now_min)
        if event.type == "delay" and event.vehicle_id:
            overrides[event.vehicle_id] = now_min + event.delay_minutes
    return {"vehicle_ids": vehicle_ids, "order_ids": order_ids, "starts": starts}


@bp.post("")
def report_event():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError({"body": "JSON object expected"})

    if body.get("plan_id") is not None:
        previous = db.session.get(Plan, as_id(body["plan_id"]) or 0)
    else:
        previous = (Plan.query.filter(Plan.status.in_(["ready", "dispatched"]))
                    .order_by(Plan.id.desc()).first())
    if previous is None or previous.status not in ("ready", "dispatched"):
        return fail("plan_id", "no finished plan to re-plan; generate a plan first", 409)

    event, overrides = apply_event(body, previous)
    if event is None:
        db.session.rollback()
        return overrides

    live = live_replan_inputs(previous, event, overrides)

    new_plan = create_plan(previous.planning_date)
    event.handled_by_plan_id = new_plan.id
    db.session.commit()

    start_plan(current_app._get_current_object(), new_plan,
               time_limit_s=body.get("time_limit_s") or current_app.config["REPLAN_TIME_LIMIT_S"],
               shift_overrides=overrides, previous_plan_id=previous.id, **(live or {}))
    db.session.refresh(new_plan)
    return jsonify(event=event_to_dict(event), plan=plan_summary(new_plan),
                   replaces_plan_id=previous.id), 202


@bp.get("")
def list_events():
    limit = min(request.args.get("limit", 20, type=int), 100)
    events = Event.query.order_by(Event.id.desc()).limit(limit).all()
    return jsonify(items=[event_to_dict(e) for e in events])
