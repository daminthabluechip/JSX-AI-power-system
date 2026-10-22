import random

from app.optimizer.types import OrderSpec, VehicleSpec
from app.services.routing_service import HaversineProvider
from seed.seed_data import DEPOT, TOWNS, VEHICLES, WINDOWS


def build(n_orders=50, seed=7, only_available=True):
    rng = random.Random(seed)
    vehicles = [
        VehicleSpec(id=i, weight_capacity_kg=kg, volume_capacity_m3=m3)
        for i, (_, _, _, kg, m3, status, _kind) in enumerate(VEHICLES, start=1)
        if not only_available or status == "available"
    ]
    orders, coords = [], [(DEPOT["latitude"], DEPOT["longitude"])]
    for i in range(1, n_orders + 1):
        _, lat, lon = rng.choice(TOWNS)
        start, end = rng.choice(WINDOWS)
        lat, lon = lat + rng.uniform(-0.02, 0.02), lon + rng.uniform(-0.02, 0.02)
        orders.append(OrderSpec(
            id=i, weight_kg=round(rng.uniform(200, 2400), 1), volume_m3=round(rng.uniform(1, 12), 1),
            priority=rng.choice(["critical", "high", "medium", "medium", "low"]),
            tw_start=start.hour * 60 + start.minute, tw_end=end.hour * 60 + end.minute))
        coords.append((lat, lon))
    dist, dur = HaversineProvider().matrix(coords)
    return vehicles, orders, dist, dur
