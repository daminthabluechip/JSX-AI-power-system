from ..models import Order, Plan, Vehicle

OPEN_ORDER_STATUSES = ("pending", "scheduled")


def can_carry(vehicle, order):
    if order.required_vehicle_type and order.required_vehicle_type != vehicle.vehicle_type:
        return False
    return order.weight_kg <= vehicle.weight_capacity_kg and order.volume_m3 <= vehicle.volume_capacity_m3


def vehicle_available_notifications():
    plan = (Plan.query.filter(Plan.status.in_(["ready", "dispatched"])).order_by(Plan.id.desc()).first())
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
            continue
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
            "suggested_event": {"type": "vehicle_available", "vehicle_id": v.id},
        })
    notes.sort(key=lambda n: -len(n["orders"]))
    return notes
