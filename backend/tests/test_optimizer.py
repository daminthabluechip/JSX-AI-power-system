"""Unit tests for the optimizer: hard constraints, priorities and the proposal's targets."""
from app.optimizer.baseline import nearest_neighbour
from app.optimizer.solver import solve
from app.optimizer.types import OrderSpec, VehicleSpec
from app.optimizer.validators import check_plan
from app.services.routing_service import HaversineProvider

from .sample_problem import build

DEPOT = (6.9271, 79.8612)


def tiny_problem(orders, vehicles, offsets):
    """Orders placed at (dlat, dlon) offsets from the depot, using the offline distance estimate."""
    coords = [DEPOT] + [(DEPOT[0] + a, DEPOT[1] + b) for a, b in offsets]
    dist, dur = HaversineProvider().matrix(coords)
    return vehicles, orders, dist, dur


def test_capacity_forces_second_vehicle():
    # Two 6 t orders cannot share one 10 t truck, so both trucks must be used.
    vehicles = [VehicleSpec(1, 10000, 50), VehicleSpec(2, 10000, 50)]
    orders = [OrderSpec(1, 6000, 5), OrderSpec(2, 6000, 5)]
    v, o, d, t = tiny_problem(orders, vehicles, [(0.05, 0.0), (0.0, 0.05)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert len(result.routes) == 2 and not result.unassigned
    assert check_plan(result, v, o) == []


def test_small_orders_are_consolidated_onto_one_vehicle():
    vehicles = [VehicleSpec(1, 10000, 50), VehicleSpec(2, 10000, 50)]
    orders = [OrderSpec(i, 1000, 2) for i in (1, 2, 3)]
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0), (0.02, 0.01), (0.03, 0.0)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert len(result.routes) == 1 and len(result.routes[0].stops) == 3


def test_volume_limit_is_enforced():
    vehicles = [VehicleSpec(1, 100000, 10)]
    orders = [OrderSpec(1, 100, 8), OrderSpec(2, 100, 8)]  # 16 m3 > 10 m3
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0), (0.0, 0.02)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert len(result.unassigned) == 1
    assert check_plan(result, v, o) == []


def test_low_priority_is_dropped_first_with_reason():
    # Only room for one order: the critical one must be served, the low one reported.
    vehicles = [VehicleSpec(1, 5000, 50)]
    orders = [OrderSpec(1, 4000, 5, priority="low"), OrderSpec(2, 4000, 5, priority="critical")]
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0), (0.0, 0.02)])
    result = solve(v, o, d, t, time_limit_s=2)
    assert [s.order_id for r in result.routes for s in r.stops] == [2]
    assert result.unassigned[0]["order_id"] == 1 and result.unassigned[0]["reason"]


def test_oversize_order_gets_specific_reason():
    vehicles = [VehicleSpec(1, 5000, 50)]
    orders = [OrderSpec(1, 9000, 5)]
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0)])
    result = solve(v, o, d, t, time_limit_s=1)
    assert "Weight exceeds" in result.unassigned[0]["reason"]


def test_time_window_is_respected_and_unreachable_window_flagged():
    vehicles = [VehicleSpec(1, 10000, 50)]
    orders = [OrderSpec(1, 100, 1, tw_start=13 * 60, tw_end=14 * 60),   # afternoon only
              OrderSpec(2, 100, 1, tw_start=7 * 60, tw_end=7 * 60 + 5)]  # needs a ~0 min trip at 07:00
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0), (0.5, 0.5)])  # order 2 is far away
    result = solve(v, o, d, t, time_limit_s=2)
    stops = {s.order_id: s for r in result.routes for s in r.stops}
    assert 13 * 60 <= stops[1].arrival <= 14 * 60          # waited until the window opened
    assert 2 not in stops
    assert "time window" in result.unassigned[0]["reason"].lower()


def test_validator_catches_a_bad_plan():
    vehicles = [VehicleSpec(1, 1000, 5)]
    orders = [OrderSpec(1, 900, 3), OrderSpec(2, 900, 3)]
    v, o, d, t = tiny_problem(orders, vehicles, [(0.02, 0.0), (0.0, 0.02)])
    result = solve(v, o, d, t, time_limit_s=1)
    # Force both orders onto one route to make the plan invalid on purpose.
    result.routes[0].stops.append(type(result.routes[0].stops[0])(2, 2, 600, 610))
    assert any("over capacity" in p for p in check_plan(result, v, o))


def test_sample_set_meets_proposal_targets():
    """~50 orders: 0 violations, solves well under 30 s, >= 10% shorter than nearest-neighbour."""
    vehicles, orders, dist, dur = build()
    base = nearest_neighbour(vehicles, orders, dist, dur)
    result = solve(vehicles, orders, dist, dur, time_limit_s=10)

    assert check_plan(result, vehicles, orders) == []
    assert check_plan(base, vehicles, orders) == []
    assert result.solve_time_s <= 30
    assert len(result.unassigned) <= len(base.unassigned)  # never serve fewer orders than baseline
    saved = 1 - result.total_distance_km / base.total_distance_km
    assert saved >= 0.10, f"only {saved:.1%} saved"
