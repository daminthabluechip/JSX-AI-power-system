"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Pause, Play, RotateCcw, Search, Timer, Truck } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import FleetMapLoader from "@/components/map/FleetMapLoader";
import { api, waitForPlan, type DelayAlert, type PlanComparison, type TrackedVehicle } from "@/lib/api";
import { usePolling } from "@/lib/useApi";

const STATE_LABEL: Record<TrackedVehicle["state"], string> = {
  waiting: "Waiting to depart", driving: "Driving", at_stop: "At stop",
  stopped: "Held up", finished: "Back at depot", idle: "Idle",
};

type Replan =
  | { phase: "idle" }
  | { phase: "planning"; vehicle: string }
  | { phase: "ready"; planId: number; version: number; comparison: PlanComparison }
  | { phase: "dispatching" };

export default function LiveTrackingPage() {
  const [tab, setTab] = useState<"active" | "all">("active");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [speed, setSpeed] = useState(20);
  const [replan, setReplan] = useState<Replan>({ phase: "idle" });
  const [actionError, setActionError] = useState<string | null>(null);

  const tracking = usePolling(() => api.tracking.positions(), 2000);
  const alerts = usePolling(() => api.tracking.alerts(), 3000);

  const items = tracking.data?.items ?? [];
  const sim = tracking.data?.simulator;
  const hasPlan = tracking.data?.plan_id != null;
  const active = items.filter((v) => v.active);
  const list = items.filter(
    (v) => (tab === "all" || v.active) && v.registration.toLowerCase().includes(query.toLowerCase())
  );
  const selected = items.find((v) => v.vehicle_id === selectedId) ?? active[0] ?? items[0] ?? null;

  async function control(body: Record<string, unknown>) {
    setActionError(null);
    try {
      await api.tracking.simulator(body);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Command failed");
    }
  }

  async function replanFor(alert: DelayAlert) {
    setActionError(null);
    setReplan({ phase: "planning", vehicle: alert.registration });
    try {
      const out = await api.events.report(alert.suggested_event);
      const plan = await waitForPlan(out.plan.id);
      if (plan.status === "failed") throw new Error(plan.error ?? "Re-planning failed");
      const comparison = await api.plans.compare(out.replaces_plan_id, plan.id);
      setReplan({ phase: "ready", planId: plan.id, version: plan.version, comparison });
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Re-planning failed");
      setReplan({ phase: "idle" });
    }
  }

  async function dispatchNew() {
    if (replan.phase !== "ready") return;
    setReplan({ phase: "dispatching" });
    try {
      await api.plans.dispatch(replan.planId);
      setReplan({ phase: "idle" });
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Dispatch failed");
      setReplan({ phase: "idle" });
    }
  }

  const mapVehicles = (hasPlan ? active : items).map((v) => ({
    id: v.registration,
    position: [v.latitude, v.longitude] as [number, number],
    path: v.active ? v.path : [],
  }));

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Live Tracking</h2>
          <p className="text-sm text-slate-500">Monitor vehicles and deliveries in real time.</p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Live updates
        </span>
      </div>

      {tracking.error && <ErrorBox message={tracking.error} />}
      {actionError && <ErrorBox message={actionError} />}
      {tracking.data && !hasPlan && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          No plan is being executed. <Link href="/route-planning" className="font-semibold underline">Generate and dispatch one</Link>, then start the simulator here.
        </div>
      )}

      {hasPlan && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
          <span className="flex items-center gap-1.5 font-semibold"><Timer size={16} className="text-blue-600" /> Simulator</span>
          <span className="rounded bg-slate-100 px-2 py-1 font-mono text-xs">{sim?.sim_time ?? "--:--"}</span>
          <label className="flex items-center gap-1 text-xs text-slate-500">
            Speed
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="rounded border border-slate-200 px-1 py-0.5 text-slate-900">
              {[5, 10, 20, 30, 60].map((s) => <option key={s} value={s}>{s} min/s</option>)}
            </select>
          </label>
          {sim?.running ? (
            <button onClick={() => control({ action: "stop" })} className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 font-medium"><Pause size={14} /> Pause</button>
          ) : (
            <button onClick={() => control({ action: "start", speed })} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white"><Play size={14} /> {items.some((v) => v.recorded_at) ? "Resume" : "Start"}</button>
          )}
          <button
            disabled={!selected?.active}
            onClick={() => selected && control({ action: "delay", vehicle_id: selected.vehicle_id, minutes: 60 })}
            className="rounded-lg border border-orange-200 px-3 py-1.5 font-medium text-orange-600 disabled:opacity-50"
            title="Simulate a traffic jam: the selected vehicle stops for 60 simulated minutes"
          >
            Jam {selected?.registration ?? "vehicle"} (60 min)
          </button>
          <button onClick={() => control({ action: "reset" })} className="ml-auto flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-slate-600"><RotateCcw size={14} /> Reset</button>
        </div>
      )}

      {(alerts.data?.items ?? []).map((a) => (
        <div key={a.vehicle_id} className="flex items-center gap-3 rounded-xl border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900">
          <AlertTriangle size={18} className="shrink-0" />
          <span className="flex-1"><span className="font-semibold">{a.message}.</span> A new plan can recover the schedule.</span>
          <button
            onClick={() => replanFor(a)}
            disabled={replan.phase !== "idle"}
            className="rounded-lg bg-orange-600 px-3 py-1.5 font-semibold text-white disabled:opacity-50"
          >
            Re-plan now
          </button>
        </div>
      ))}

      {replan.phase === "planning" && (
        <div className="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <Loader2 className="animate-spin" size={16} /> Re-planning from current positions after the delay of {replan.vehicle}... about 10 seconds.
        </div>
      )}
      {(replan.phase === "ready" || replan.phase === "dispatching") && (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <CheckCircle2 size={18} className="shrink-0" />
          {replan.phase === "ready" ? (
            <>
              <span className="flex-1">
                <span className="font-semibold">New plan v{replan.version} is ready.</span>{" "}
                {replan.comparison.changes.filter((c) => c.change === "reassigned").length} orders change vehicle,{" "}
                {replan.comparison.unchanged_orders} are untouched, {replan.comparison.unassigned.after} unassigned.
              </span>
              <button onClick={dispatchNew} className="rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white">Dispatch new plan</button>
            </>
          ) : (
            <span className="flex-1">Dispatching...</span>
          )}
        </div>
      )}

      <div className="flex h-[520px] gap-4">
        <aside className="flex w-80 shrink-0 flex-col rounded-xl border border-slate-200 bg-white">
          <div className="p-3">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400">
              <Search size={14} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a vehicle..." className="w-full bg-transparent text-slate-900 outline-none" />
            </div>
            <div className="mt-3 flex border-b border-slate-200 text-xs font-medium">
              {(["active", "all"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={`-mb-px flex-1 border-b-2 pb-2 capitalize ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500"}`}>
                  {t} ({t === "active" ? active.length : items.length})
                </button>
              ))}
            </div>
          </div>
          <ul className="flex-1 overflow-y-auto">
            {list.map((v) => (
              <li key={v.vehicle_id}>
                <button
                  onClick={() => setSelectedId(v.vehicle_id)}
                  className={`flex w-full items-center gap-3 border-l-2 px-3 py-3 text-left text-sm ${v.vehicle_id === selected?.vehicle_id ? "border-blue-600 bg-blue-50/50" : "border-transparent"}`}
                >
                  <span className="rounded-lg bg-blue-50 p-2 text-blue-600"><Truck size={14} /></span>
                  <span className="flex-1">
                    <span className="block font-semibold">{v.registration}</span>
                    <span className="block text-xs text-slate-500">
                      {v.next_stop ? `Next: ${v.next_stop.customer}` : STATE_LABEL[v.state]}
                    </span>
                  </span>
                  <span className="text-right text-xs">
                    <span className="block font-semibold">{v.next_stop?.eta ?? ""}</span>
                    {v.lag_minutes > 0 && <span className="font-semibold text-orange-600">+{v.lag_minutes} min</span>}
                  </span>
                </button>
              </li>
            ))}
            {list.length === 0 && <li className="p-6 text-center text-xs text-slate-400">No vehicles to show.</li>}
          </ul>
        </aside>

        <div className="relative flex-1 overflow-hidden rounded-xl border border-slate-200">
          <FleetMapLoader vehicles={mapVehicles} selectedId={selected?.registration} onSelect={(reg) => setSelectedId(items.find((v) => v.registration === reg)?.vehicle_id ?? null)} />
          {selected && (
            <div className="absolute inset-x-4 bottom-4 z-[1000] flex items-center gap-8 rounded-xl bg-white p-4 text-xs shadow-lg">
              <div><p className="text-sm font-bold">{selected.registration}</p><p className="text-slate-500">{STATE_LABEL[selected.state]}</p></div>
              <div><p className="text-slate-500">Driver</p><p className="font-semibold">{selected.driver ?? "-"}</p></div>
              <div><p className="text-slate-500">Speed</p><p className="font-semibold">{selected.speed_kmh} km/h</p></div>
              <div><p className="text-slate-500">Next stop</p><p className="font-semibold">{selected.next_stop?.customer ?? "-"}</p></div>
              <div><p className="text-slate-500">ETA</p><p className="font-semibold text-blue-600">{selected.next_stop?.eta ?? "-"}</p></div>
              <div>
                <p className="text-slate-500">Schedule</p>
                <p className={`font-semibold ${selected.lag_minutes > 0 ? "text-orange-600" : "text-emerald-600"}`}>
                  {selected.lag_minutes > 0 ? `${selected.lag_minutes} min late` : "On time"}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 text-xs">
        <div>
          <p className="text-sm font-semibold">Tracking integration</p>
          <p className="text-slate-500">Simulated feed. A real feed only has to POST readings to /tracking/positions.</p>
        </div>
        <div className="flex gap-2 text-slate-600">
          {["Current location", "Vehicle movement", "Schedule lag", "Delay alerts", "Delivery progress"].map((t) => (
            <span key={t} className="rounded-full bg-slate-50 px-2 py-1">{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
