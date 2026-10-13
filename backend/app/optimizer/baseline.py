"""A deliberately simple "manual-style" plan to compare the optimizer against.

Nearest-neighbour: fill one vehicle at a time, always driving to the closest order that still
fits (capacity + time window), and start the next vehicle when nothing fits any more.
The proposal's target is: the optimizer saves at least 10% distance versus this plan.
"""
from .types import PlanResult, PlannedRoute, PlannedStop


def nearest_neighbour(vehicles, orders, dist_m, dur_min):
    result = PlanResult()
    remaining = {node: o for node, o in enumerate(orders, start=1)}

    # Biggest vehicles first, as a dispatcher would load them.
    for spec in sorted(vehicles, key=lambda v: -v.weight_capacity_kg):
        if not remaining:
            break
        here, clock = spec.start_node, spec.shift_start
        load = volume = 0.0
        nodes, arrivals = [], []

        while True:
            best = None
            for node, o in remaining.items():
                if o.required_vehicle_type and o.required_vehicle_type != spec.vehicle_type:
                    continue   # wrong kind of vehicle for this order
                if load + o.weight_kg > spec.weight_capacity_kg:
                    continue
                if volume + o.volume_m3 > spec.volume_capacity_m3:
                    continue
                arrival = max(clock + dur_min[here][node], o.tw_start)  # wait if too early
                back_home = arrival + o.service_min + dur_min[node][0]
                if arrival > o.tw_end or back_home > spec.shift_end:
                    continue
                if best is None or dist_m[here][node] < dist_m[here][best[0]]:
                    best = (node, arrival)
            if best is None:
                break
            node, arrival = best
            o = remaining.pop(node)
            nodes.append(node)
            arrivals.append(arrival)
            load += o.weight_kg
            volume += o.volume_m3
            clock, here = arrival + o.service_min, node

        if not nodes:
            continue
        route = PlannedRoute(vehicle_id=spec.id, load_kg=load, volume_m3=volume, start_node=spec.start_node)
        route.departure = max(spec.shift_start, arrivals[0] - dur_min[spec.start_node][nodes[0]])
        path = [spec.start_node] + nodes + [0]
        route.distance_m = sum(dist_m[a][b] for a, b in zip(path, path[1:]))
        for seq, (node, arrival) in enumerate(zip(nodes, arrivals), start=1):
            o = orders[node - 1]
            route.stops.append(PlannedStop(o.id, seq, arrival, arrival + o.service_min))
        route.return_time = route.stops[-1].departure + dur_min[nodes[-1]][0]
        result.routes.append(route)

    result.unassigned = [{"order_id": o.id, "reason": "Did not fit any vehicle (baseline)"}
                         for o in remaining.values()]
    return result
