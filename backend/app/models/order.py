from ..extensions import db


class Order(db.Model):
    """A customer delivery request."""
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    volume_m3 = db.Column(db.Float, nullable=False)
    # critical | high | medium | low  (lower priorities are dropped first when orders don't fit)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    target_date = db.Column(db.Date, nullable=False)
    earliest_arrival = db.Column(db.Time)   # customer time window start
    latest_arrival = db.Column(db.Time)     # customer time window end
    # pending | scheduled | in_transit | delivered | cancelled
    status = db.Column(db.String(20), nullable=False, default="pending")
