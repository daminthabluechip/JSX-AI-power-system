from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import VEHICLE_TYPES, Event, Position, Route, Vehicle
from .helpers import clean_payload, fmt_time, paginate

bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")

STATUSES = ["available", "on_route", "maintenance"]

SPEC = {
    "registration": {"kind": "str", "required": True},
    "model": {"kind": "str"},
    "vehicle_type": {"kind": "str", "choices": VEHICLE_TYPES},
    "driver": {"kind": "str"},
    "weight_capacity_kg": {"kind": "num", "required": True, "positive": True},
    "volume_capacity_m3": {"kind": "num", "required": True, "positive": True},
    "shift_start": {"kind": "time"},
    "shift_end": {"kind": "time"},
    "status": {"kind": "str", "choices": STATUSES},
    "depot_id": {"kind": "num"},
}


def to_dict(v):
    return {
        "id": v.id,
        "registration": v.registration,
        "model": v.model,
        "vehicle_type": v.vehicle_type,
        "driver": v.driver,
        "weight_capacity_kg": v.weight_capacity_kg,
        "volume_capacity_m3": v.volume_capacity_m3,
        "shift_start": fmt_time(v.shift_start),
        "shift_end": fmt_time(v.shift_end),
        "status": v.status,
        "depot_id": v.depot_id,
    }


@bp.get("")
def list_vehicles():
    query = Vehicle.query.order_by(Vehicle.id)
    if status := request.args.get("status"):
        query = query.filter(Vehicle.status == status)
    if q := request.args.get("q"):
        like = f"%{q}%"
        query = query.filter(Vehicle.registration.ilike(like) | Vehicle.driver.ilike(like)
                             | Vehicle.model.ilike(like))
    return paginate(query, to_dict)


@bp.get("/summary")
def summary():
    rows = dict(db.session.query(Vehicle.status, func.count()).group_by(Vehicle.status).all())
    return jsonify(
        all=sum(rows.values()),
        available=rows.get("available", 0),
        on_route=rows.get("on_route", 0),
        maintenance=rows.get("maintenance", 0),
    )


@bp.get("/<int:vehicle_id>")
def get_vehicle(vehicle_id):
    return jsonify(to_dict(db.get_or_404(Vehicle, vehicle_id)))


@bp.post("")
def create_vehicle():
    data = clean_payload(request.get_json(silent=True), SPEC)
    if Vehicle.query.filter_by(registration=data["registration"]).first():
        return jsonify(error="validation_failed",
                       details={"registration": "already exists"}), 409
    vehicle = Vehicle(**data)
    db.session.add(vehicle)
    db.session.commit()
    return jsonify(to_dict(vehicle)), 201


@bp.put("/<int:vehicle_id>")
@bp.patch("/<int:vehicle_id>")
def update_vehicle(vehicle_id):
    vehicle = db.get_or_404(Vehicle, vehicle_id)
    for key, value in clean_payload(request.get_json(silent=True), SPEC, partial=True).items():
        setattr(vehicle, key, value)
    db.session.commit()
    return jsonify(to_dict(vehicle))


@bp.delete("/<int:vehicle_id>")
def delete_vehicle(vehicle_id):
    vehicle = db.get_or_404(Vehicle, vehicle_id)
    if Route.query.filter_by(vehicle_id=vehicle_id).first() or Event.query.filter_by(vehicle_id=vehicle_id).first():
        return jsonify(error="conflict", details={
            "message": "This vehicle is part of existing plans. Set its status to maintenance instead of deleting it."}), 409
    Position.query.filter_by(vehicle_id=vehicle_id).delete()
    db.session.delete(vehicle)
    db.session.commit()
    return "", 204
