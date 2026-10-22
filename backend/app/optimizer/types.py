from dataclasses import dataclass, field

DAY_MINUTES = 24 * 60


@dataclass
class VehicleSpec:
    id: int
    weight_capacity_kg: int
    volume_capacity_m3: float
    shift_start: int = 7 * 60
    shift_end: int = 19 * 60
    start_node: int = 0
    vehicle_type: str = "truck"


@dataclass
class OrderSpec:
    id: int
    weight_kg: float
    volume_m3: float
    priority: str = "medium"
    tw_start: int = 0
    tw_end: int = DAY_MINUTES
    service_min: int = 10
    required_vehicle_type: str | None = None


@dataclass
class PlannedStop:
    order_id: int
    sequence: int
    arrival: int
    departure: int


@dataclass
class PlannedRoute:
    vehicle_id: int
    departure: int = 0
    start_node: int = 0
    stops: list = field(default_factory=list)
    load_kg: float = 0
    volume_m3: float = 0
    distance_m: int = 0
    return_time: int = 0


@dataclass
class PlanResult:
    routes: list = field(default_factory=list)
    unassigned: list = field(default_factory=list)
    solve_time_s: float = 0.0

    @property
    def total_distance_km(self):
        return round(sum(r.distance_m for r in self.routes) / 1000, 2)

    @property
    def total_time_min(self):
        return sum(r.return_time - r.departure for r in self.routes)
