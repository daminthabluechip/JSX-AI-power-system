"""Glue between the database and the optimizer.

generate flow:  API creates a Plan row (status "queued")  ->  run_plan() loads vehicles and
orders, builds the travel matrix, calls the optimizer + baseline, saves routes/stops, and marks
the plan "ready" (or "failed"). The solve runs in a background thread so the request returns
immediately and the dashboard polls GET /plans/<id> until the status changes.
"""
import threading
import traceback
from datetime import datetime, time, timedelta

from ..extensions import db
from ..models import Depot, Order, Plan, Route, Stop, Vehicle
from ..optimizer.baseline import nearest_neighbour
from ..optimizer.solver import solve
from ..optimizer.types import OrderSpec, VehicleSpec
from ..optimizer.validators import check_plan
from .routing_service import get_provider

# Orders in these states still need to be planned.
PLANNABLE_ORDER_STATUSES = ["pending", "scheduled"]


def minutes(t, default):
    """datetime.time -> minutes since midnight."""
    return default if t is None else t.hour * 60 + t.minute


def create_plan(day, vehicle_ids=None, order_ids=None, time_limit_s=None):
    """Insert a queued Plan row (next version number for that date) and return it."""
    version = Plan.query.filter_by(planning_date=day).count() + 1
    plan = Plan(planning_date=day, version=version, status="queued")
    db.session.add(plan)
    db.session.commit()
    return plan


def start_plan(app, plan, vehicle_ids=None, order_ids=None, time_limit_s=None, shift_overrides=None,
               previous_plan_id=None, starts=None):
    """Run the solve now (tests) or in a background thread (normal operation).

    shift_overrides: {vehicle_id: earliest departure in minutes} - used by re-planning when
    a vehicle is delayed and cannot leave the depot at its normal shift start.
    previous_plan_id: warm-start from that plan so a re-plan changes as little as possible.
    starts: {vehicle_id: (lat, lon, earliest_minute)} - plan from where a vehicle is right now.
    """
    limit = time_limit_s or app.config["SOLVER_TIME_LIMIT_S"]
    if app.config["PLAN_SYNC"]:
        run_plan(app, plan.id, vehicle_ids, order_ids, limit, shift_overrides, previous_plan_id, starts)
        return

    def worker():
        with app.app_context():  # the thread needs its own app context / db session
            run_plan(app, plan.id, vehicle_ids, order_ids, limit, shift_overrides, previous_plan_id, starts)

    threading.Thread(target=worker, daemon=True).start()


def load_problem(day, vehicle_ids, order_ids, shift_overrides=None, starts=None):
    """Read vehicles/orders/depot from the DB and convert them to optimizer inputs."""
    depot = Depot.query.first()
    if depot is None:
        raise ValueError("No depot configured")

    vq = Vehicle.query
    vq = vq.filter(Vehicle.id.in_(vehicle_ids)) if vehicle_ids else vq.filter_by(status="available")
    vehicles_db = vq.order_by(Vehicle.id).all()

    oq = Order.query.filter(Order.target_date == day)
    oq = (oq.filter(Order.id.in_(order_ids)) if order_ids
          else oq.filter(Order.status.in_(PLANNABLE_ORDER_STATUSES)))
    orders_db = oq.order_by(Order.id).all()

    # Fail loudly instead of returning an empty plan that looks successful.
    for label, wanted, found in (("vehicle", vehicle_ids, vehicles_db), ("order", order_ids, orders_db)):
        missing = sorted(set(wanted or []) - {x.id for x in found})
        if missing:
            raise ValueError(f"Unknown {label} ids (or none for {day}): {missing}")
    if not vehicles_db:
        raise ValueError("No available vehicles to plan with")
    if not orders_db:
        raise ValueError(f"No pending orders for {day}")

    overrides = shift_overrides or {}
    vehicles = [VehicleSpec(v.id, v.weight_capacity_kg, v.volume_capacity_m3,
                            max(minutes(v.shift_start, 7 * 60), overrides.get(v.id, 0)),
                            minutes(v.shift_end, 19 * 60), vehicle_type=v.vehicle_type or "truck")
                for v in vehicles_db]
    orders = [OrderSpec(o.id, o.weight_kg, o.volume_m3, o.priority,
                        minutes(o.earliest_arrival, 0), minutes(o.latest_arrival, 24 * 60),
                        required_vehicle_type=o.required_vehicle_type)
              for o in orders_db]
    coords = [(depot.latitude, depot.longitude)] + [(o.latitude, o.longitude) for o in orders_db]

    # Vehicles already on the road start from their current position: add one matrix row per
    # such vehicle, and don't let them "leave" before the moment the position was reported.
    for spec in vehicles:
        if starts and spec.id in starts:
            lat, lon, earliest = starts[spec.id]
            spec.start_node = len(coords)
            spec.shift_start = max(spec.shift_start, earliest)
            coords.append((lat, lon))
    return vehicles, orders, coords


def run_plan(app, plan_id, vehicle_ids, order_ids, time_limit_s, shift_overrides=None,
             previous_plan_id=None, starts=None):
    """Solve and store the result for one plan. Never raises: failures are saved on the plan."""
    plan = db.session.get(Plan, plan_id)
    try:
        plan.status = "solving"
        db.session.commit()

        vehicles, orders, coords = load_problem(
            plan.planning_date, vehicle_ids, order_ids, shift_overrides, starts)
        plan.vehicle_ids = [v.id for v in vehicles]   # remember who was considered (see Plan.vehicle_ids)
        db.session.commit()

        # TODO: TOOL/API CALL HERE - the routing provider (OSRM/ORS) is called inside matrix()
        # when ROUTING_PROVIDER=osrm; results are cached per pair.
        dist_m, dur_min = get_provider(app.config).matrix(coords)

        previous = None
        if previous_plan_id:
            old = db.session.get(Plan, previous_plan_id)
            previous = {r.vehicle_id: [s.order_id for s in r.stops] for r in old.routes}
        result = solve(vehicles, orders, dist_m, dur_min, time_limit_s, previous)
        baseline = nearest_neighbour(vehicles, orders, dist_m, dur_min)

        problems = check_plan(result, vehicles, orders)  # must never trigger; guards solver bugs
        if problems:
            raise RuntimeError("Invalid plan: " + "; ".join(problems[:3]))

        save_result(plan, result, baseline, coords)
    except Exception as exc:  # noqa: BLE001 - we want every failure recorded on the plan
        db.session.rollback()
        plan = db.session.get(Plan, plan_id)
        plan.status = "failed"
        plan.error = f"{type(exc).__name__}: {exc}"[:500]
        db.session.commit()
        traceback.print_exc()


def save_result(plan, result, baseline, coords=None):
    """Write routes and stops to the DB and fill in the plan totals."""
    midnight = datetime.combine(plan.planning_date, time(0, 0))
    at = lambda m: midnight + timedelta(minutes=m)  # noqa: E731

    for r in result.routes:
        route = Route(plan_id=plan.id, vehicle_id=r.vehicle_id, planned_departure=at(r.departure),
                      load_kg=r.load_kg, volume_m3=r.volume_m3,
                      distance_km=round(r.distance_m / 1000, 2), return_time=at(r.return_time))
        if r.start_node:   # started from a vehicle position instead of the depot
            route.start_latitude, route.start_longitude = coords[r.start_node]
        route.stops = [Stop(order_id=s.order_id, sequence=s.sequence,
                            planned_arrival=at(s.arrival), planned_departure=at(s.departure))
                       for s in r.stops]
        db.session.add(route)

    plan.total_distance_km = result.total_distance_km
    plan.total_time_min = result.total_time_min
    plan.solve_time_s = result.solve_time_s
    plan.baseline_distance_km = baseline.total_distance_km
    plan.baseline_served = sum(len(r.stops) for r in baseline.routes)
    plan.unassigned = result.unassigned
    plan.status = "ready"
    db.session.commit()
