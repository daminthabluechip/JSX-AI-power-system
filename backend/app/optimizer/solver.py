"""The OR-Tools vehicle routing model (VRP with capacities and time windows).

Node 0 is the depot, nodes 1..n are the orders (same order as the `orders` list).
Hard rules the solver can never break: weight and volume limits, customer time windows,
vehicle shifts. Soft goals it minimises: distance + travel time + a fixed cost per vehicle
used (which pushes it to combine deliveries onto fewer vehicles).
"""
import time

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .types import DAY_MINUTES, PlanResult, PlannedRoute, PlannedStop

# Cost of leaving an order unserved, by priority. These are much larger than any route cost,
# so an order is only dropped when it truly cannot fit - and low priority goes first.
DROP_PENALTY = {"critical": 40_000_000, "high": 20_000_000, "medium": 10_000_000, "low": 5_000_000}
VEHICLE_FIXED_COST = 50_000   # "metres" of cost charged for every vehicle that is used
TIME_COST_PER_MIN = 500       # one minute of driving costs the same as 500 m
# Re-planning only: extra cost for serving an order with a different vehicle than the previous plan.
# 30 km worth of driving: an order only changes truck when that saves clearly more than this.
STABILITY_PENALTY = 30_000


def eligible(order, vehicles):
    """The vehicles allowed to serve this order (all of them unless it requires a vehicle type)."""
    if not order.required_vehicle_type:
        return list(vehicles)
    return [v for v in vehicles if v.vehicle_type == order.required_vehicle_type]


def explain_unassigned(order, vehicles, earliest_arrival):
    """Best-effort reason why an order is not in the plan."""
    allowed = eligible(order, vehicles)
    if not allowed:
        return f"No selected vehicle of the required type '{order.required_vehicle_type}'"
    scope = "every selected vehicle" if len(allowed) == len(vehicles) else f"every '{order.required_vehicle_type}' vehicle"
    if order.weight_kg > max(v.weight_capacity_kg for v in allowed):
        return f"Weight exceeds the capacity of {scope}"
    if order.volume_m3 > max(v.volume_capacity_m3 for v in allowed):
        return f"Volume exceeds the capacity of {scope}"
    if earliest_arrival > order.tw_end:   # best case over all vehicles, from where each one starts
        return "Customer time window cannot be reached in time by any vehicle"
    return "No remaining vehicle capacity or shift time (lower priority orders are dropped first)"


def solve(vehicles, orders, dist_m, dur_min, time_limit_s=10, previous_routes=None):
    """Build and solve the model. dist_m / dur_min are square matrices: row 0 = depot, rows 1..n
    = the orders, and any further rows are vehicle start positions (see VehicleSpec.start_node).

    previous_routes ({vehicle_id: [order_id, ...]} in stop order) warm-starts the search from an
    earlier plan. Without it, many equally good plans exist and the solver may reshuffle almost
    every order when only one thing changed; starting from the old plan keeps re-plans stable.
    """
    started = time.perf_counter()
    result = PlanResult()
    if not vehicles or not orders:
        result.unassigned = [{"order_id": o.id, "reason": "No vehicles selected"} for o in orders]
        return result

    n = len(orders)
    extra = len(dist_m) - n - 1   # rows beyond the orders: vehicle start positions
    # Vehicles start at their own start node (usually the depot) and always end at the depot.
    manager = pywrapcp.RoutingIndexManager(
        len(dist_m), len(vehicles), [v.start_node for v in vehicles], [0] * len(vehicles))
    routing = pywrapcp.RoutingModel(manager)
    service = [0] + [o.service_min for o in orders] + [0] * extra

    # --- cost of driving an arc: distance plus time ---
    def arc_cost(i, j):
        a, b = manager.IndexToNode(i), manager.IndexToNode(j)
        return dist_m[a][b] + TIME_COST_PER_MIN * dur_min[a][b]

    if previous_routes:
        # Re-plan: each vehicle gets its own cost function that charges STABILITY_PENALTY for
        # visiting an order that another (still available) vehicle carried in the previous plan.
        position = {v.id: k for k, v in enumerate(vehicles)}
        prev_vehicle = {}   # order node -> index of the vehicle that had it before
        for k_id, order_ids in previous_routes.items():
            for oid in order_ids:
                if k_id in position:
                    prev_vehicle[oid] = position[k_id]
        prev_of_node = [None] + [prev_vehicle.get(o.id) for o in orders] + [None] * extra

        def make_cost(k):
            def cost(i, j):
                b = manager.IndexToNode(j)
                bonus = STABILITY_PENALTY if prev_of_node[b] not in (None, k) else 0
                return arc_cost(i, j) + bonus
            return cost

        for k in range(len(vehicles)):
            routing.SetArcCostEvaluatorOfVehicle(routing.RegisterTransitCallback(make_cost(k)), k)
    else:
        routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(arc_cost))

    # --- capacity rules (weight in kg, volume in tenths of m3 so everything is an integer) ---
    def add_capacity(name, per_node, capacities):
        cb = routing.RegisterUnaryTransitCallback(lambda i: per_node[manager.IndexToNode(i)])
        routing.AddDimensionWithVehicleCapacity(cb, 0, capacities, True, name)

    add_capacity("Weight", [0] + [round(o.weight_kg) for o in orders] + [0] * extra,
                 [round(v.weight_capacity_kg) for v in vehicles])
    add_capacity("Volume", [0] + [round(o.volume_m3 * 10) for o in orders] + [0] * extra,
                 [round(v.volume_capacity_m3 * 10) for v in vehicles])

    # --- time: driving time + unloading time; waiting for a window to open is allowed ---
    def transit_time(i, j):
        a, b = manager.IndexToNode(i), manager.IndexToNode(j)
        return service[a] + dur_min[a][b]

    time_idx = routing.RegisterTransitCallback(transit_time)
    routing.AddDimension(time_idx, DAY_MINUTES, DAY_MINUTES, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    for node, order in enumerate(orders, start=1):   # customer time windows
        time_dim.CumulVar(manager.NodeToIndex(node)).SetRange(
            order.tw_start, min(order.tw_end, DAY_MINUTES))
    for v, spec in enumerate(vehicles):              # vehicle shifts + fixed cost per vehicle
        time_dim.CumulVar(routing.Start(v)).SetRange(spec.shift_start, spec.shift_end)
        time_dim.CumulVar(routing.End(v)).SetRange(spec.shift_start, spec.shift_end)
        routing.SetFixedCostOfVehicle(VEHICLE_FIXED_COST, v)

    # --- every order is optional, with a priority-based penalty for dropping it ---
    for node, order in enumerate(orders, start=1):
        routing.AddDisjunction([manager.NodeToIndex(node)], DROP_PENALTY.get(order.priority, 10_000_000))

    # --- vehicle type rule: an order that needs a type may only be served by such a vehicle.
    # VehicleVar is the vehicle that serves the node; -1 means "not served".
    for node, order in enumerate(orders, start=1):
        if order.required_vehicle_type:
            allowed = [k for k, v in enumerate(vehicles) if v.vehicle_type == order.required_vehicle_type]
            routing.VehicleVar(manager.NodeToIndex(node)).SetValues([-1] + allowed)

    # --- search: quick first solution, then local search until the time limit ---
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(int(time_limit_s))
    solution = None
    initial = None
    if previous_routes:
        node_of = {o.id: node for node, o in enumerate(orders, start=1)}
        warm = [[node_of[oid] for oid in previous_routes.get(v.id, []) if oid in node_of]
                for v in vehicles]   # drops cancelled orders and unavailable vehicles
        routing.CloseModelWithParameters(params)
        initial = routing.ReadAssignmentFromRoutes(warm, True)   # None if the old routes no longer fit
    if initial is not None:
        solution = routing.SolveFromAssignmentWithParameters(initial, params)
    else:
        solution = routing.SolveWithParameters(params)

    served = set()
    if solution:
        for v, spec in enumerate(vehicles):
            index = routing.Start(v)
            nodes, arrivals = [], []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if 1 <= node <= n:   # skip the depot / start-position rows
                    nodes.append(node)
                    arrivals.append(solution.Min(time_dim.CumulVar(index)))
                index = solution.Value(routing.NextVar(index))
            if not nodes:
                continue  # vehicle not used

            route = PlannedRoute(vehicle_id=spec.id, start_node=spec.start_node)
            # Leave as late as possible without waiting at the first stop (but not before shift start).
            route.departure = max(spec.shift_start, arrivals[0] - dur_min[spec.start_node][nodes[0]])
            path = [spec.start_node] + nodes + [0]
            route.distance_m = sum(dist_m[a][b] for a, b in zip(path, path[1:]))
            for seq, (node, arrival) in enumerate(zip(nodes, arrivals), start=1):
                order = orders[node - 1]
                route.stops.append(PlannedStop(order.id, seq, arrival, arrival + order.service_min))
                route.load_kg += order.weight_kg
                route.volume_m3 += order.volume_m3
                served.add(node)
            last = route.stops[-1]
            route.return_time = last.departure + dur_min[nodes[-1]][0]
            result.routes.append(route)

    result.unassigned = [
        {"order_id": o.id, "reason": explain_unassigned(
            o, vehicles, min((v.shift_start + dur_min[v.start_node][node] for v in eligible(o, vehicles)),
                             default=0))}
        for node, o in enumerate(orders, start=1) if node not in served
    ]
    result.solve_time_s = round(time.perf_counter() - started, 2)
    return result
