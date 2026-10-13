"""Vehicle simulator: stands in for JXG's real tracking feed until access is available.

It moves every vehicle of the dispatched plan along its planned route on a fast clock and
reports positions through tracking_service.ingest() - exactly what a real feed adapter would do.
Swap the simulator for the real feed by stopping it and calling ingest() from the adapter.

Simulated clock: sim_minutes = start + (real seconds elapsed) * speed.  speed = simulated
minutes per real second, so speed 1 means a 10-hour working day plays out in 10 real minutes.

Injected delay: the vehicle stands still for the given number of simulated minutes (a traffic
jam) and then carries on, permanently behind the plan by that amount.
"""
import threading
import time as realtime

from ..extensions import db
from ..models import Order
from ..services import tracking_service as tracking

TICK_SECONDS = 2.0   # how often (real time) the running simulator reports positions


class Simulator:
    def __init__(self):
        self.running = False
        self.start_minute = 7 * 60
        self.speed = 1.0
        self._started_real = 0.0
        self.delays = {}      # vehicle_id -> [(sim_minute_when_injected, total_delay_minutes)]
        self.has_run = False  # True once started; a later start without a time resumes from here
        self._thread = None
        self._lock = threading.Lock()

    # ----- clock -----
    def now(self):
        """Current simulated minute since midnight."""
        if not self.running:
            return self.start_minute
        return self.start_minute + (realtime.monotonic() - self._started_real) * self.speed

    def status(self):
        m = self.now()
        return {"running": self.running, "speed": self.speed, "sim_minute": round(m, 1),
                "sim_time": f"{int(m // 60) % 24:02d}:{int(m % 60):02d}",
                "delays": {str(k): sum(t for _, t in v) for k, v in self.delays.items()}}

    # ----- control -----
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
            self.start_minute = self.now()   # keep the time where it stopped
            self.running = False

    def inject_delay(self, vehicle_id, minutes):
        self.delays.setdefault(vehicle_id, []).append((self.now(), minutes))

    def reset(self):
        """Stop, forget delays and delete stored positions."""
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
                except Exception:   # keep the simulator alive; the error shows in the server log
                    import traceback
                    traceback.print_exc()
                    db.session.rollback()
            realtime.sleep(TICK_SECONDS)

    # ----- one step -----
    def tick(self, config, sim_minute=None):
        """Report one position per vehicle of the dispatched plan at the given (or current) time.
        Returns the number of positions reported. Call inside an app context."""
        sim_minute = self.now() if sim_minute is None else sim_minute
        plan = tracking.dispatched_plan()
        if plan is None:
            return 0
        day = plan.planning_date
        all_home = True   # does every vehicle's plan end before this moment?
        for route in plan.routes:
            wps = tracking.route_schedule(route, day, config)
            stalls = self.delays.get(route.vehicle_id, [])
            # Time lost so far: grows 1:1 with the clock during a jam, then stays constant.
            lost = sum(min(total, max(0.0, sim_minute - start)) for start, total in stalls)
            jammed = any(start <= sim_minute < start + total for start, total in stalls)
            effective = sim_minute - lost   # the point of the plan the vehicle has really reached
            all_home = all_home and effective >= wps[-1].arrive

            xy, speed, _ = tracking.position_at(wps, effective)
            tracking.ingest(route.vehicle_id, xy[0], xy[1], 0.0 if jammed else speed, tracking.at(day, sim_minute))

            # Record the real arrival time of every stop reached since the last tick. The tick can
            # overshoot a stop, so step back by the overshoot to get the moment it was reached.
            for stop in route.stops:
                planned = tracking.minutes_of(stop.planned_arrival, day)
                if stop.actual_arrival is None and effective >= planned:
                    stop.actual_arrival = tracking.at(day, sim_minute - (effective - planned))

            # Stops the vehicle has finished are delivered.
            done = [s.order_id for s in route.stops if tracking.minutes_of(s.planned_departure, day) <= effective]
            if done:
                Order.query.filter(Order.id.in_(done), Order.status == "in_transit").update(
                    {"status": "delivered"}, synchronize_session=False)
        tracking.prune([r.vehicle_id for r in plan.routes])
        db.session.commit()
        if all_home and self.running:   # the working day is over: stop instead of running into the night
            self.start_minute = sim_minute
            self.running = False
        return len(plan.routes)


simulator = Simulator()   # one per server process
