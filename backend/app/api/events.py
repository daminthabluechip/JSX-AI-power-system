"""/events endpoints: report a disruption, which triggers a re-plan.

Supported types:
  vehicle_available vehicle_id               a vehicle can be used again (or is new): re-plan with it
  delay         vehicle_id + delay_minutes   the vehicle cannot leave until that much later
  breakdown     vehicle_id                   vehicle is taken out of service
  rush_order    order {...}                  a new urgent order must be added
  cancellation  order_id                     an order is removed

Each event creates a NEW plan version for the same date (the old version is kept so the two
can be compared with GET /plans/<id>/compare/<other>).
"""
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
    """Accept only real integers as ids (rejects strings, floats, booleans)."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def fail(field, message, status=400):
    return jsonify(error="validation_failed", details={field: message}), status


def apply_event(body, plan):
    """Validate the event, apply its side effects to vehicles/orders, and return
    (event, shift_overrides) - or (None, error_response) when the request is invalid."""
    kind = body.get("type")
    event = Event(type=kind)
    overrides = {}

    if kind in ("delay", "breakdown"):
        vehicle = db.session.get(Vehicle, as_id(body.get("vehicle_id"))) if as_id(body.get("vehicle_id")) else None
        if vehicle is None:
            return None, fail("vehicle_id", "existing vehicle required")
        event.vehicle_id = vehicle.id

        if kind == "breakdown":
            # Out of service: the next plan only uses vehicles whose status is "available".
            vehicle.status = "maintenance"
        else:
            delay = body.get("delay_minutes")
            if not isinstance(delay, int) or delay <= 0:
                return None, fail("delay_minutes", "positive whole number required")
            event.delay_minutes = delay
            # The vehicle may not leave before (its planned departure + the delay).
            route = Route.query.filter_by(plan_id=plan.id, vehicle_id=vehicle.id).first()
            base = (route.planned_departure.hour * 60 + route.planned_departure.minute
                    if route else minutes(vehicle.shift_start, 7 * 60))
            overrides[vehicle.id] = base + delay

    elif kind == "vehicle_available":
        # No data to change: the vehicle is already "available", so the re-plan below (which uses every
        # available vehicle and every order still waiting, including the unassigned ones) picks it up.
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
        order.status = "cancelled"   # excluded from the next plan
        event.order_id = order.id

    elif kind == "rush_order":
        payload = {"priority": "high", "target_date": plan.planning_date.isoformat(), **(body.get("order") or {})}
        data = clean_payload(payload, ORDER_SPEC)   # raises ValidationError -> 400
        bad = check_window(data)
        if bad:
            return None, bad
        order = Order(**data)
        db.session.add(order)
        db.session.flush()   # gives order.id
        event.order_id = order.id

    else:
        return None, fail("type", f"must be one of {TYPES}")

    db.session.add(event)
    return event, overrides


def live_replan_inputs(previous, event, overrides):
    """Extra inputs when the day is already under way (a plan has been dispatched).

    A live re-plan must not start everything from the depot at shift start. Instead:
      - each vehicle starts from its latest reported position, no earlier than "now"
      - only orders that are not yet delivered or cancelled are planned
      - vehicles still on the road are used even though their status is "on_route"
    Returns keyword arguments for start_plan, or None when nothing is being executed.
    `overrides` (earliest departure per vehicle) is updated in place.
    """
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

    if now_min is not None:   # nobody may depart before "now"
        for vid in vehicle_ids:
            overrides[vid] = max(overrides.get(vid, 0), now_min)
        if event.type == "delay" and event.vehicle_id:
            overrides[event.vehicle_id] = now_min + event.delay_minutes
    return {"vehicle_ids": vehicle_ids, "order_ids": order_ids, "starts": starts}


@bp.post("")
def report_event():
    """POST /events {type, vehicle_id?, order_id?, delay_minutes?, order?, plan_id?, time_limit_s?}

    Applies the disruption, then starts a re-plan in the background (202). Poll the returned
    plan with GET /plans/<id>; compare it with the previous version via /plans/<id>/compare/<old>.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError({"body": "JSON object expected"})

    # Which plan is being disrupted: the one named, or the newest finished (ready or running) plan.
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
        return overrides   # the error response

    live = live_replan_inputs(previous, event, overrides)   # None unless a plan is being executed

    new_plan = create_plan(previous.planning_date)   # commits (also saves the event + side effects)
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
    """GET /events?limit= - newest first (feeds the 'Optimization activity' list)."""
    limit = min(request.args.get("limit", 20, type=int), 100)
    events = Event.query.order_by(Event.id.desc()).limit(limit).all()
    return jsonify(items=[event_to_dict(e) for e in events])
