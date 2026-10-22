from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from ..extensions import db
from ..models import Vehicle
from ..services import tracking_service as tracking
from ..simulator.engine import simulator
from .helpers import ValidationError, parse_time

bp = Blueprint("tracking", __name__, url_prefix="/tracking")


@bp.get("/positions")
def positions():
    return jsonify({**tracking.snapshot(current_app.config), "simulator": simulator.status()})


@bp.get("/alerts")
def alerts():
    return jsonify(items=tracking.delay_alerts(current_app.config))


@bp.post("/positions")
def ingest_positions():
    body = request.get_json(silent=True)
    readings = body if isinstance(body, list) else [body]
    errors = {}
    for i, r in enumerate(readings):
        if not isinstance(r, dict) or db.session.get(Vehicle, r.get("vehicle_id") if isinstance(r.get("vehicle_id"), int) else 0) is None:
            errors[f"[{i}].vehicle_id"] = "existing vehicle required"
        elif not all(isinstance(r.get(k), (int, float)) for k in ("latitude", "longitude")):
            errors[f"[{i}]"] = "latitude and longitude must be numbers"
    if errors:
        raise ValidationError(errors)
    for r in readings:
        when = datetime.fromisoformat(r["recorded_at"]) if r.get("recorded_at") else datetime.now()
        tracking.ingest(r["vehicle_id"], r["latitude"], r["longitude"], r.get("speed_kmh"), when)
    db.session.commit()
    return jsonify(accepted=len(readings)), 201


@bp.get("/simulator")
def simulator_status():
    return jsonify(simulator.status())


@bp.post("/simulator")
def simulator_control():
    body = request.get_json(silent=True) or {}
    action = body.get("action")
    if action == "start":
        plan = tracking.dispatched_plan()
        if plan is None:
            return jsonify(error="conflict", details={"plan": "dispatch a plan first"}), 409
        try:
            start = parse_time(body["time"]) if body.get("time") else None
        except ValueError:
            raise ValidationError({"time": "expected HH:MM"})
        if start is None and simulator.has_run:
            start_minute = None
        elif start is None:
            first = min(r.planned_departure for r in plan.routes)
            start_minute = first.hour * 60 + first.minute - 5
        else:
            start_minute = start.hour * 60 + start.minute
        speed = body.get("speed", simulator.speed)
        if not isinstance(speed, (int, float)) or not 0 < speed <= 60:
            raise ValidationError({"speed": "number between 0 and 60 (simulated minutes per second)"})
        simulator.start(current_app._get_current_object(), start_minute, speed)
    elif action == "stop":
        simulator.stop()
    elif action == "delay":
        vid, minutes = body.get("vehicle_id"), body.get("minutes")
        if not isinstance(vid, int) or db.session.get(Vehicle, vid) is None:
            raise ValidationError({"vehicle_id": "existing vehicle required"})
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValidationError({"minutes": "positive whole number required"})
        simulator.inject_delay(vid, minutes)
    elif action == "reset":
        simulator.reset()
    else:
        raise ValidationError({"action": "must be start, stop, delay or reset"})
    return jsonify(simulator.status())
