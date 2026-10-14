"""Notifications for the dispatcher.

Today there is one kind: "vehicle_available". When the newest plan left orders unassigned and a
vehicle that the plan did not consider has since become available (a new vehicle, one back from
maintenance, one that finished its route), tell the dispatcher which unassigned orders it could take.

Nothing is stored: the list is worked out from the data each time it is asked for, so it appears when
the situation arises and disappears by itself once a re-plan has considered that vehicle.
"""
from ..models import Order, Plan, Vehicle

OPEN_ORDER_STATUSES = ("pending", "scheduled")   # still waiting to be planned


def can_carry(vehicle, order):
    """Could this vehicle take this order, looking only at type and size? (Time windows are left to
    the optimizer: it is the one that decides whether the order really fits into the day.)"""
    if order.required_vehicle_type and order.required_vehicle_type != vehicle.vehicle_type:
        return False
    return order.weight_kg <= vehicle.weight_capacity_kg and order.volume_m3 <= vehicle.volume_capacity_m3


def vehicle_available_notifications():
    """One notification per newly available vehicle that could take at least one unassigned order."""
    plan = (Plan.query.filter(Plan.status.in_(["ready", "dispatched"])).order_by(Plan.id.desc()).first())
    # Plans made before vehicle_ids was recorded have no list of considered vehicles: say nothing.
    if plan is None or not plan.unassigned or plan.vehicle_ids is None:
        return []

    open_orders = [o for o in Order.query.filter(Order.id.in_([u["order_id"] for u in plan.unassigned]))
                   if o.status in OPEN_ORDER_STATUSES]
    if not open_orders:
        return []

    considered = set(plan.vehicle_ids)
    notes = []
    for v in Vehicle.query.filter_by(status="available").order_by(Vehicle.id):
        if v.id in considered:
            continue   # the optimizer already had this vehicle and still could not use it
        fits = [o for o in open_orders if can_carry(v, o)]
        if not fits:
            continue
        tonnes = v.weight_capacity_kg / 1000
        notes.append({
            "type": "vehicle_available",
            "plan_id": plan.id,
            "vehicle": {"id": v.id, "registration": v.registration, "model": v.model,
                        "vehicle_type": v.vehicle_type, "weight_capacity_kg": v.weight_capacity_kg},
            "orders": [{"order_id": o.id, "customer": o.customer, "priority": o.priority,
                        "weight_kg": o.weight_kg} for o in fits],
            "unassigned_total": len(open_orders),
            "message": (f"{v.registration} ({v.vehicle_type}, {tonnes:.1f} t) is available and could take "
                        f"{len(fits)} of the {len(open_orders)} unassigned order{'s' if len(open_orders) != 1 else ''}."),
            # the exact body to POST to /events to re-plan with this vehicle
            "suggested_event": {"type": "vehicle_available", "vehicle_id": v.id},
        })
    # The vehicle that could take the most orders comes first; ties keep the vehicle id order.
    notes.sort(key=lambda n: -len(n["orders"]))
    return notes
