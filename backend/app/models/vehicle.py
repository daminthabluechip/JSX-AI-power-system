from ..extensions import db


# Kinds of vehicle. An order can require one of these (see Order.required_vehicle_type).
VEHICLE_TYPES = ["truck", "van", "refrigerated", "flatbed"]


class Vehicle(db.Model):
    """A truck in the fleet, with capacities the optimizer must respect."""
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(20), unique=True, nullable=False)  # e.g. VH-2048
    model = db.Column(db.String(80))
    vehicle_type = db.Column(db.String(40), default="truck")
    driver = db.Column(db.String(80))
    weight_capacity_kg = db.Column(db.Float, nullable=False)
    volume_capacity_m3 = db.Column(db.Float, nullable=False)
    shift_start = db.Column(db.Time)   # earliest the vehicle can leave
    shift_end = db.Column(db.Time)     # latest it must be back
    # available | on_route | maintenance
    status = db.Column(db.String(20), nullable=False, default="available")
    depot_id = db.Column(db.Integer, db.ForeignKey("depots.id"))
