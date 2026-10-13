from datetime import datetime, timezone

from ..extensions import db


class Plan(db.Model):
    """One optimizer result for a planning date. Re-planning creates a new version."""
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    planning_date = db.Column(db.Date, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    # queued | solving | ready | failed | dispatched
    status = db.Column(db.String(20), nullable=False, default="queued")
    total_distance_km = db.Column(db.Float)
    total_time_min = db.Column(db.Float)
    solve_time_s = db.Column(db.Float)   # logged to check the 30s / 15s targets
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    routes = db.relationship("Route", backref="plan", cascade="all, delete-orphan")


class Route(db.Model):
    """The trip one vehicle makes within a plan."""
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    planned_departure = db.Column(db.DateTime)
    load_kg = db.Column(db.Float, default=0)
    volume_m3 = db.Column(db.Float, default=0)
    stops = db.relationship("Stop", backref="route", order_by="Stop.sequence",
                            cascade="all, delete-orphan")


class Stop(db.Model):
    """One customer visit on a route, in order."""
    __tablename__ = "stops"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    planned_arrival = db.Column(db.DateTime)
    planned_departure = db.Column(db.DateTime)
