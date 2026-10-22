from datetime import datetime, timezone

from ..extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    occurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    delay_minutes = db.Column(db.Integer)
    handled_by_plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"))


class Position(db.Model):
    __tablename__ = "positions"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed_kmh = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
