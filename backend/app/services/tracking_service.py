import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import func

from ..extensions import db
from ..models import Depot, Order, Plan, Position, Vehicle
from .routing_service import get_provider, haversine_m

AT_STOP_KM = 0.2
FINISHED_STATES = ("finished",)


def at(day, minute):
    return datetime.combine(day, time(0, 0)) + timedelta(minutes=minute)


def minutes_of(dt, day):
    return (dt.replace(tzinfo=None) - datetime.combine(day, time(0, 0))).total_seconds() / 60


def km_between(a, b):
    return haversine_m(a, b) / 1000


@dataclass
class Waypoint:
    xy: tuple
    arrive: float
    depart: float
    order_id: int | None = None


def route_schedule(route, day, config):
    depot = Depot.query.first()
    depot_xy = (depot.latitude, depot.longitude)
    start_xy = (route.start_latitude, route.start_longitude) if route.start_latitude is not None else depot_xy
    dep = minutes_of(route.planned_departure, day)

    orders = {o.id: o for o in Order.query.filter(Order.id.in_([s.order_id for s in route.stops]))}
    wps = [Waypoint(start_xy, dep, dep)]
    for s in route.stops:
        o = orders[s.order_id]
        wps.append(Waypoint((o.latitude, o.longitude), minutes_of(s.planned_arrival, day),
                            minutes_of(s.planned_departure, day), s.order_id))

    back = get_provider(config).matrix([wps[-1].xy, depot_xy])[1][0][1]
    home = wps[-1].depart + back
    wps.append(Waypoint(depot_xy, home, home))
    return wps


def position_at(wps, t):
    if t <= wps[0].depart:
        return wps[0].xy, 0.0, "waiting"
    last = len(wps) - 1
    for i in range(1, len(wps)):
        prev, cur = wps[i - 1], wps[i]
        if t < cur.arrive:
            span = max(cur.arrive - prev.depart, 1e-9)
            f = min(max((t - prev.depart) / span, 0.0), 1.0)
            xy = (prev.xy[0] + f * (cur.xy[0] - prev.xy[0]), prev.xy[1] + f * (cur.xy[1] - prev.xy[1]))
            return xy, km_between(prev.xy, cur.xy) / (span / 60), "driving"
        if t <= cur.depart:
            return cur.xy, 0.0, "finished" if i == last else "at_stop"
    return wps[-1].xy, 0.0, "finished"


def _project(p, a, b):
    k = math.cos(math.radians(a[0]))
    ax, ay, bx, by = a[1] * k, a[0], b[1] * k, b[0]
    px, py = p[1] * k, p[0]
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    f = 0.0 if length2 == 0 else min(max(((px - ax) * dx + (py - ay) * dy) / length2, 0.0), 1.0)
    cx, cy = ax + f * dx, ay + f * dy
    return f, math.hypot((px - cx) * 111.32, (py - cy) * 110.57)


def schedule_lag(wps, xy, t):
    if t <= wps[0].depart:
        return 0.0
    if km_between(xy, wps[-1].xy) < AT_STOP_KM and t >= wps[-1].arrive - 1:
        return 0.0
    candidates = []
    for prev, cur in zip(wps, wps[1:]):
        f, dist = _project(xy, prev.xy, cur.xy)
        if f >= 0.999:
            planned = min(max(t, cur.arrive), cur.depart)
        elif f <= 0.001:
            planned = min(max(t, prev.arrive), prev.depart)
        else:
            planned = prev.depart + f * (cur.arrive - prev.depart)
        candidates.append((dist, planned))
    best_dist = min(d for d, _ in candidates)
    planned = min((p for d, p in candidates if d <= best_dist + 0.05), key=lambda p: abs(p - t))
    return max(0.0, t - planned)


def ingest(vehicle_id, lat, lon, speed_kmh, recorded_at):
    db.session.add(Position(vehicle_id=vehicle_id, latitude=lat, longitude=lon,
                            speed_kmh=speed_kmh, recorded_at=recorded_at))


def prune(vehicle_ids, keep=300):
    for vid in vehicle_ids:
        old = (Position.query.filter_by(vehicle_id=vid).order_by(Position.id.desc())
               .offset(keep).with_entities(Position.id).all())
        if old:
            Position.query.filter(Position.id.in_([i for (i,) in old])).delete(synchronize_session=False)


def latest_positions():
    newest = (db.session.query(func.max(Position.id).label("pid")).group_by(Position.vehicle_id).subquery())
    rows = Position.query.join(newest, Position.id == newest.c.pid).all()
    return {p.vehicle_id: p for p in rows}


def dispatched_plan():
    return Plan.query.filter_by(status="dispatched").order_by(Plan.id.desc()).first()


def snapshot(config):
    depot = Depot.query.first()
    plan = dispatched_plan()
    readings = latest_positions()
    vehicles = {v.id: v for v in Vehicle.query.order_by(Vehicle.id)}
    items, in_plan = [], set()

    if plan:
        for route in plan.routes:
            v = vehicles[route.vehicle_id]
            in_plan.add(v.id)
            wps = route_schedule(route, plan.planning_date, config)
            r = readings.get(v.id)
            if r is None:
                xy, speed, t, state, lag = wps[0].xy, 0.0, None, "waiting", 0.0
            else:
                xy, speed, t = (r.latitude, r.longitude), r.speed_kmh or 0.0, minutes_of(r.recorded_at, plan.planning_date)
                lag = schedule_lag(wps, xy, t)
                _, _, planned_state = position_at(wps, t - lag)
                state = "driving" if planned_state == "finished" else planned_state
                if km_between(xy, wps[-1].xy) < AT_STOP_KM and t >= wps[-1].arrive - 1:
                    state = "finished"
                elif speed == 0 and state == "driving":
                    state = "stopped"

            planned_t = (t - lag) if t is not None else wps[0].depart
            nxt = next((w for w in wps[1:-1] if w.depart > planned_t), None)
            next_stop = None
            if nxt:
                order = db.session.get(Order, nxt.order_id)
                eta = nxt.arrive + (lag if planned_t < nxt.arrive else 0)
                next_stop = {"order_id": nxt.order_id, "customer": order.customer,
                             "eta": at(plan.planning_date, eta).strftime("%H:%M")}
            items.append({
                "vehicle_id": v.id, "registration": v.registration, "driver": v.driver,
                "active": state != "finished", "state": state,
                "latitude": xy[0], "longitude": xy[1], "speed_kmh": round(speed),
                "recorded_at": r.recorded_at.isoformat() if r else None,
                "lag_minutes": round(lag), "next_stop": next_stop, "plan_id": plan.id,
                "path": [list(w.xy) for w in wps],
            })

    for vid, v in vehicles.items():
        if vid not in in_plan:
            items.append({
                "vehicle_id": v.id, "registration": v.registration, "driver": v.driver,
                "active": False, "state": "idle", "latitude": depot.latitude, "longitude": depot.longitude,
                "speed_kmh": 0, "recorded_at": None, "lag_minutes": 0, "next_stop": None,
                "plan_id": None, "path": [],
            })
    return {"plan_id": plan.id if plan else None, "items": items}


def delay_alerts(config):
    threshold = config.get("TRACKING_DELAY_THRESHOLD_MIN", 15)
    alerts = []
    for item in snapshot(config)["items"]:
        if item["active"] and item["lag_minutes"] >= threshold:
            alerts.append({
                "vehicle_id": item["vehicle_id"], "registration": item["registration"],
                "lag_minutes": item["lag_minutes"], "plan_id": item["plan_id"],
                "message": f"{item['registration']} is {item['lag_minutes']} min behind schedule",
                "suggested_event": {"type": "delay", "vehicle_id": item["vehicle_id"],
                                    "delay_minutes": item["lag_minutes"]},
            })
    return alerts


def replan_context(plan_ids):
    day, vehicle_ids = None, set()
    for pid in plan_ids:
        p = db.session.get(Plan, pid)
        day = p.planning_date
        vehicle_ids |= {r.vehicle_id for r in p.routes}
    readings = {vid: r for vid, r in latest_positions().items() if vid in vehicle_ids}
    if not readings:
        return None, {}
    now = max(minutes_of(r.recorded_at, day) for r in readings.values())
    return int(math.ceil(now)), {vid: (r.latitude, r.longitude, int(math.ceil(now))) for vid, r in readings.items()}
