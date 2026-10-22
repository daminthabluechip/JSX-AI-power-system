from ..extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    volume_m3 = db.Column(db.Float, nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    target_date = db.Column(db.Date, nullable=False)
    earliest_arrival = db.Column(db.Time)
    latest_arrival = db.Column(db.Time)
    required_vehicle_type = db.Column(db.String(30))
    status = db.Column(db.String(20), nullable=False, default="pending")
