"""Plain data classes passed in and out of the optimizer.

The optimizer knows nothing about the database or Flask: it receives these objects and
returns a PlanResult. All clock times are "minutes since midnight" (e.g. 08:30 -> 510).
"""
from dataclasses import dataclass, field

DAY_MINUTES = 24 * 60


@dataclass
class VehicleSpec:
    id: int
    weight_capacity_kg: int
    volume_capacity_m3: float
    shift_start: int = 7 * 60     # earliest departure from the depot
    shift_end: int = 19 * 60      # must be back at the depot by then
    # Matrix row where this vehicle starts. 0 = the depot; re-planning a vehicle that is already
    # out on the road uses an extra matrix row holding its current position (and shift_start is
    # then "now").
    start_node: int = 0
    vehicle_type: str = "truck"   # e.g. truck, van, refrigerated, flatbed


@dataclass
class OrderSpec:
    id: int
    weight_kg: float
    volume_m3: float
    priority: str = "medium"      # critical | high | medium | low
    tw_start: int = 0             # customer window: earliest arrival
    tw_end: int = DAY_MINUTES     # customer window: latest arrival
    service_min: int = 10         # time spent unloading at the stop
    required_vehicle_type: str | None = None   # only a vehicle of this type may serve the order


@dataclass
class PlannedStop:
    order_id: int
    sequence: int                 # 1 = first stop
    arrival: int                  # minutes since midnight
    departure: int


@dataclass
class PlannedRoute:
    vehicle_id: int
    departure: int = 0            # when the vehicle leaves its start point
    start_node: int = 0           # matrix row it starts from (0 = depot)
    stops: list = field(default_factory=list)
    load_kg: float = 0
    volume_m3: float = 0
    distance_m: int = 0           # depot -> stops -> depot
    return_time: int = 0          # when it is back at the depot


@dataclass
class PlanResult:
    routes: list = field(default_factory=list)
    unassigned: list = field(default_factory=list)   # [{"order_id": 3, "reason": "..."}]
    solve_time_s: float = 0.0

    @property
    def total_distance_km(self):
        return round(sum(r.distance_m for r in self.routes) / 1000, 2)

    @property
    def total_time_min(self):
        return sum(r.return_time - r.departure for r in self.routes)
