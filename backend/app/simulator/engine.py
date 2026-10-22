import threading
import time as realtime

from ..extensions import db
from ..models import Order
from ..services import tracking_service as tracking

TICK_SECONDS = 2.0


class Simulator:
    def __init__(self):
        self.running = False
        self.start_minute = 7 * 60
        self.speed = 1.0
        self._started_real = 0.0
        self.delays = {}
        self.has_run = False
        self._thread = None
        self._lock = threading.Lock()

    def now(self):
        if not self.running:
            return self.start_minute
        return self.start_minute + (realtime.monotonic() - self._started_real) * self.speed

    def status(self):
        m = self.now()
        return {"running": self.running, "speed": self.speed, "sim_minute": round(m, 1),
                "sim_time": f"{int(m // 60) % 24:02d}:{int(m % 60):02d}",
                "delays": {str(k): sum(t for _, t in v) for k, v in self.delays.items()}}

    def start(self, app, start_minute=None, speed=None):
        with self._lock:
            if start_minute is not None:
                self.start_minute = start_minute
            if speed:
                self.speed = float(speed)
            self._started_real = realtime.monotonic()
            self.has_run = True
            if self.running:
                return
            self.running = True
            self._thread = threading.Thread(target=self._loop, args=(app,), daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self.start_minute = self.now()
            self.running = False

    def inject_delay(self, vehicle_id, minutes):
        self.delays.setdefault(vehicle_id, []).append((self.now(), minutes))

    def reset(self):
        self.stop()
        self.delays = {}
        self.has_run = False
        from ..models import Position
        Position.query.delete()
        db.session.commit()

    def _loop(self, app):
        while self.running:
            with app.app_context():
                try:
                    self.tick(app.config)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    db.session.rollback()
            realtime.sleep(TICK_SECONDS)

    def tick(self, config, sim_minute=None):
        sim_minute = self.now() if sim_minute is None else sim_minute
        plan = tracking.dispatched_plan()
        if plan is None:
            return 0
        day = plan.planning_date
        all_home = True
        for route in plan.routes:
            wps = tracking.route_schedule(route, day, config)
            stalls = self.delays.get(route.vehicle_id, [])
            lost = sum(min(total, max(0.0, sim_minute - start)) for start, total in stalls)
            jammed = any(start <= sim_minute < start + total for start, total in stalls)
            effective = sim_minute - lost
            all_home = all_home and effective >= wps[-1].arrive

            xy, speed, _ = tracking.position_at(wps, effective)
            tracking.ingest(route.vehicle_id, xy[0], xy[1], 0.0 if jammed else speed, tracking.at(day, sim_minute))

            for stop in route.stops:
                planned = tracking.minutes_of(stop.planned_arrival, day)
                if stop.actual_arrival is None and effective >= planned:
                    stop.actual_arrival = tracking.at(day, sim_minute - (effective - planned))

            done = [s.order_id for s in route.stops if tracking.minutes_of(s.planned_departure, day) <= effective]
            if done:
                Order.query.filter(Order.id.in_(done), Order.status == "in_transit").update(
                    {"status": "delivered"}, synchronize_session=False)
        tracking.prune([r.vehicle_id for r in plan.routes])
        db.session.commit()
        if all_home and self.running:
            self.start_minute = sim_minute
            self.running = False
        return len(plan.routes)


simulator = Simulator()
