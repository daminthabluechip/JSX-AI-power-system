from datetime import datetime, timezone

from ..extensions import db


class Event(db.Model):
    """A disruption that triggers a re-plan: delay, breakdown, rush order or cancellation."""
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # delay | breakdown | rush_order | cancellation
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    occurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    delay_minutes = db.Column(db.Integer)  # only for delay events
    # which plan version handled this event
    handled_by_plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"))


class Position(db.Model):
    """A vehicle GPS reading (simulated at first, later from JXG tracking)."""
    __tablename__ = "positions"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed_kmh = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
