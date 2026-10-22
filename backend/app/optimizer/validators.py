def check_plan(result, vehicles, orders):
    vehicle_by_id = {v.id: v for v in vehicles}
    order_by_id = {o.id: o for o in orders}
    problems, seen = [], set()

    for route in result.routes:
        v = vehicle_by_id[route.vehicle_id]
        weight = sum(order_by_id[s.order_id].weight_kg for s in route.stops)
        volume = sum(order_by_id[s.order_id].volume_m3 for s in route.stops)
        if weight > v.weight_capacity_kg + 1e-6:
            problems.append(f"vehicle {v.id}: weight {weight:.0f} kg over capacity {v.weight_capacity_kg}")
        if volume > v.volume_capacity_m3 + 1e-6:
            problems.append(f"vehicle {v.id}: volume {volume:.1f} m3 over capacity {v.volume_capacity_m3}")
        if route.departure < v.shift_start or route.return_time > v.shift_end:
            problems.append(f"vehicle {v.id}: outside shift {v.shift_start}-{v.shift_end}")

        previous_departure = route.departure
        for stop in route.stops:
            o = order_by_id[stop.order_id]
            if o.required_vehicle_type and o.required_vehicle_type != v.vehicle_type:
                problems.append(f"order {o.id}: needs a '{o.required_vehicle_type}' vehicle but is on "
                                f"vehicle {v.id} ('{v.vehicle_type}')")
            if not o.tw_start <= stop.arrival <= o.tw_end:
                problems.append(f"order {o.id}: arrival {stop.arrival} outside window "
                                f"{o.tw_start}-{o.tw_end}")
            if stop.arrival < previous_departure:
                problems.append(f"order {o.id}: arrives before the previous stop is finished")
            previous_departure = stop.departure
            if o.id in seen:
                problems.append(f"order {o.id}: served more than once")
            seen.add(o.id)
    return problems
