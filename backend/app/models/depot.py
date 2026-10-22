from ..extensions import db


class Depot(db.Model):
    __tablename__ = "depots"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    opens_at = db.Column(db.Time)
    closes_at = db.Column(db.Time)
