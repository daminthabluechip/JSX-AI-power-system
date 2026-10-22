from datetime import datetime, timezone

from ..extensions import db


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    planning_date = db.Column(db.Date, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="queued")
    total_distance_km = db.Column(db.Float)
    total_time_min = db.Column(db.Float)
    solve_time_s = db.Column(db.Float)
    baseline_distance_km = db.Column(db.Float)
    baseline_served = db.Column(db.Integer)
    unassigned = db.Column(db.JSON)
    vehicle_ids = db.Column(db.JSON)
    error = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    routes = db.relationship("Route", backref="plan", cascade="all, delete-orphan")


class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    planned_departure = db.Column(db.DateTime)
    load_kg = db.Column(db.Float, default=0)
    volume_m3 = db.Column(db.Float, default=0)
    distance_km = db.Column(db.Float)
    return_time = db.Column(db.DateTime)
    start_latitude = db.Column(db.Float)
    start_longitude = db.Column(db.Float)
    stops = db.relationship("Stop", backref="route", order_by="Stop.sequence",
                            cascade="all, delete-orphan")


class Stop(db.Model):
    __tablename__ = "stops"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    planned_arrival = db.Column(db.DateTime)
    planned_departure = db.Column(db.DateTime)
    actual_arrival = db.Column(db.DateTime)
