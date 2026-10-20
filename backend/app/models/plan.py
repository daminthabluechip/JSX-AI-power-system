from datetime import datetime, timezone

from ..extensions import db


class Plan(db.Model):
    """One optimizer result for a planning date. Re-planning creates a new version."""
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    planning_date = db.Column(db.Date, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    # queued | solving | ready | failed | dispatched | superseded (a newer plan was dispatched)
    status = db.Column(db.String(20), nullable=False, default="queued")
    total_distance_km = db.Column(db.Float)
    total_time_min = db.Column(db.Float)
    solve_time_s = db.Column(db.Float)   # logged to check the 30s / 15s targets
    baseline_distance_km = db.Column(db.Float)  # nearest-neighbour plan, to show the savings
    # How many orders the nearest-neighbour plan managed to serve. The optimizer often serves MORE orders,
    # so comparing total kilometres alone is unfair: see plan_summary().
    baseline_served = db.Column(db.Integer)
    unassigned = db.Column(db.JSON)      # [{"order_id": 3, "reason": "..."}]
    # Ids of the vehicles the optimizer was allowed to use for this plan. A vehicle that is available
    # now but NOT in this list became available later: that is what triggers the "vehicle available" notice.
    vehicle_ids = db.Column(db.JSON)
    error = db.Column(db.String(500))    # set when status == failed
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
    distance_km = db.Column(db.Float)      # driving distance of this vehicle's whole trip
    return_time = db.Column(db.DateTime)   # when it is back at the depot
    # Where the vehicle starts. NULL = the depot; set when a re-plan starts from the vehicle's
    # current position (a vehicle that is already on the road).
    start_latitude = db.Column(db.Float)
    start_longitude = db.Column(db.Float)
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
    # When the vehicle really reached this stop (from tracking). NULL until it gets there.
    # Compared with the customer's window to measure on-time delivery in the reports.
    actual_arrival = db.Column(db.DateTime)
