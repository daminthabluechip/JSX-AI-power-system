"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, Loader2, Sparkles, Wrench, XCircle, Zap } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import PlanMap from "@/components/map/PlanMap";
import {
  api, formatDuration, todayISO, waitForPlan,
  type DisruptionEvent, type EventType, type Plan, type PlanComparison,
} from "@/lib/api";
import { useApi } from "@/lib/useApi";

type Scenario = {
  type: EventType;
  title: string;
  icon: typeof Zap;
  box: string;
  detail: string;
  body: Record<string, unknown> | null;
};

function scenariosFor(plan: Plan | null): Scenario[] {
  const busiest = plan && [...plan.routes].sort((a, b) => b.stops.length - a.stops.length)[0];
  const lastStop = plan?.routes.at(-1)?.stops[0];
  return [
    {
      type: "delay", title: "Heavy traffic & delays", icon: AlertTriangle, box: "bg-red-50 text-red-500",
      detail: busiest ? `${busiest.vehicle.registration} is held up for 30 minutes` : "Needs a plan",
      body: busiest ? { type: "delay", vehicle_id: busiest.vehicle.id, delay_minutes: 30 } : null,
    },
    {
      type: "breakdown", title: "Vehicle breakdown", icon: Wrench, box: "bg-orange-50 text-orange-500",
      detail: busiest ? `${busiest.vehicle.registration} goes out of service; its orders are reassigned` : "Needs a plan",
      body: busiest ? { type: "breakdown", vehicle_id: busiest.vehicle.id } : null,
    },
    {
      type: "rush_order", title: "New urgent delivery", icon: Zap, box: "bg-blue-50 text-blue-600",
      detail: "Summit Medical, Kandy - critical priority",
      body: plan ? {
        type: "rush_order",
        order: {
          customer: "Summit Medical (urgent)", address: "Hospital Road, Kandy", latitude: 7.2906, longitude: 80.6337,
          weight_kg: 400, volume_m3: 2, priority: "critical", earliest_arrival: "09:00", latest_arrival: "16:00",
        },
      } : null,
    },
    {
      type: "cancellation", title: "Cancellation / unavailable", icon: XCircle, box: "bg-violet-50 text-violet-600",
      detail: lastStop ? `${lastStop.customer} cancels their order` : "Needs a plan",
      body: lastStop ? { type: "cancellation", order_id: lastStop.order_id } : null,
    },
  ];
}

const EVENT_LABEL: Record<EventType, string> = {
  delay: "Delay reported", breakdown: "Vehicle breakdown", rush_order: "Rush order added", cancellation: "Order cancelled",
  vehicle_available: "Vehicle became available",
};

const CHANGE_STYLE: Record<string, string> = {
  reassigned: "bg-orange-50 text-orange-600", rescheduled: "bg-blue-50 text-blue-600",
  dropped: "bg-red-50 text-red-600", removed: "bg-slate-100 text-slate-600",
  completed: "bg-emerald-50 text-emerald-600",
  added: "bg-emerald-50 text-emerald-600", now_assigned: "bg-emerald-50 text-emerald-600",
};

export default function OptimizationPage() {
  const [selected, setSelected] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<PlanComparison | null>(null);
  const [applied, setApplied] = useState<string | null>(null);
  const [maps, setMaps] = useState<{ before: Plan; after: Plan } | null>(null);
  const [mapView, setMapView] = useState<"before" | "after">("after");

  const current = useApi(async () => {
    const { items } = await api.plans.list(todayISO());
    const latest = items.find((p) => p.status === "ready" || p.status === "dispatched");
    return latest ? api.plans.get(latest.id) : null;
  });
  const events = useApi(() => api.events.list(5));

  const plan = current.data ?? null;
  const scenarios = scenariosFor(plan);
  const scenario = scenarios[selected];

  async function apply() {
    if (!scenario.body) return;
    setRunning(true);
    setError(null);
    try {
      const out = await api.events.report(scenario.body);
      const next = await waitForPlan(out.plan.id);
      if (next.status === "failed") throw new Error(next.error ?? "Re-planning failed");
      setComparison(await api.plans.compare(out.replaces_plan_id, next.id));
      if (plan) setMaps({ before: plan, after: next });
      setMapView("after");
      setApplied(scenario.title);
      await Promise.all([current.reload(), events.reload()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Re-planning failed");
    } finally {
      setRunning(false);
    }
  }

  const moved = comparison?.changes.filter((c) => c.change === "reassigned" || c.change === "rescheduled").length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Dynamic Optimization</h2>
          <p className="text-sm text-slate-500">Automatically recalculate plans when real-time disruptions affect operations.</p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Monitoring live
        </span>
      </div>

      {current.error && <ErrorBox message={current.error} />}
      {error && <ErrorBox message={error} />}
      {!current.loading && !current.error && !plan && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          There is no plan for today yet.{" "}
          <Link href="/route-planning" className="font-semibold underline">Generate one on Route Planning</Link> first.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Disruptions</h3>
          <p className="text-xs text-slate-500">Select an event to simulate. Applying it changes data (e.g. a breakdown takes the vehicle out of service).</p>
          <ul className="mt-3 space-y-2">
            {scenarios.map((s, i) => (
              <li key={s.type}>
                <button
                  onClick={() => setSelected(i)}
                  className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm ${selected === i ? "border-blue-300 bg-blue-50/50" : "border-slate-200"}`}
                >
                  <span className={`rounded-lg p-2 ${s.box}`}><s.icon size={16} /></span>
                  <span className="flex-1">
                    <span className="block font-semibold">{s.title}</span>
                    <span className="block text-xs text-slate-500">{s.detail}</span>
                  </span>
                  <ChevronRight size={16} className="text-slate-400" />
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 p-5 text-white">
          <div className="flex items-center gap-2">
            <Sparkles size={18} />
            <div>
              <h3 className="font-semibold">Instant route recalibration</h3>
              <p className="text-xs text-blue-100">AI response for the selected disruption</p>
            </div>
          </div>
          <p className="mt-4 rounded-lg bg-white/10 p-3 text-xs">
            Selected event<br /><span className="text-sm font-semibold">{scenario.title}</span>
          </p>

          {running ? (
            <div className="my-8 text-center text-sm">
              <Loader2 className="mx-auto mb-2 animate-spin" size={30} />
              Re-planning... about 10 seconds
            </div>
          ) : comparison ? (
            <>
              <div className="my-4 text-center">
                <CheckCircle2 size={32} className="mx-auto rounded-full bg-white/20 p-1.5" />
                <p className="mt-2 font-semibold">Updated plan ready</p>
                <p className="text-xs text-blue-100">After &quot;{applied}&quot;: plan v{comparison.after.version} replaces v{comparison.before.version}</p>
              </div>
              <dl className="grid grid-cols-3 divide-x divide-white/20 rounded-lg bg-white/10 py-3 text-center text-xs">
                <div><dt className="text-blue-100">Orders changed</dt><dd className="text-xl font-bold">{comparison.changes.length}</dd></div>
                <div><dt className="text-blue-100">Unchanged</dt><dd className="text-xl font-bold">{comparison.unchanged_orders}</dd></div>
                <div><dt className="text-blue-100">Unassigned</dt><dd className="text-xl font-bold">{comparison.unassigned.after}</dd></div>
              </dl>
            </>
          ) : (
            <p className="my-8 text-center text-xs text-blue-100">Choose a disruption and press Apply to see the new plan.</p>
          )}

          <button
            onClick={apply}
            disabled={running || !scenario.body}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-white py-2 text-sm font-semibold text-blue-700 disabled:opacity-60"
          >
            <CheckCircle2 size={16} /> Apply &amp; re-plan
          </button>
        </section>
      </div>

      {comparison && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Plan Comparison</h3>
              <p className="text-xs text-slate-500">What changed between the previous and the new plan.</p>
            </div>
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">Optimization complete</span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            {([["Previous plan", comparison.before, comparison.vehicles_used.before, comparison.unassigned.before, "border-t-red-400"],
               ["New plan", comparison.after, comparison.vehicles_used.after, comparison.unassigned.after, "border-t-emerald-500"]] as const).map(
              ([title, p, vehiclesUsed, unassigned, accent]) => (
                <div key={title} className={`rounded-xl border border-t-2 border-slate-200 p-5 ${accent}`}>
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold">{title}</h4>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">v{p.version}</span>
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                    <div><dt className="text-slate-500">Total distance</dt><dd className="text-base font-bold">{p.total_distance_km} km</dd></div>
                    <div><dt className="text-slate-500">Total drive time</dt><dd className="text-base font-bold">{formatDuration(p.total_time_min)}</dd></div>
                    <div><dt className="text-slate-500">Vehicles used</dt><dd className="text-base font-bold">{vehiclesUsed}</dd></div>
                    <div><dt className="text-slate-500">Unassigned orders</dt><dd className="text-base font-bold">{unassigned}</dd></div>
                  </dl>
                </div>
              )
            )}
          </div>

          <div className="mt-4 grid grid-cols-4 gap-3">
            {[
              ["Distance change", comparison.distance_delta_km == null ? "-" : `${comparison.distance_delta_km > 0 ? "+" : ""}${comparison.distance_delta_km} km`],
              ["Drive time change", comparison.time_delta_min == null ? "-" : `${comparison.time_delta_min > 0 ? "+" : ""}${Math.round(comparison.time_delta_min)} min`],
              ["Orders moved or retimed", moved],
              ["Orders untouched", comparison.unchanged_orders],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 p-3 text-xs">
                <p className="text-slate-500">{label}</p>
                <p className="text-base font-bold">{value}</p>
              </div>
            ))}
          </div>

          {maps && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-semibold">Route map</span>
                {(["before", "after"] as const).map((k) => (
                  <button
                    key={k}
                    onClick={() => setMapView(k)}
                    className={`rounded-full px-3 py-1 font-medium ${mapView === k ? "bg-blue-600 text-white" : "border border-slate-200 text-slate-600"}`}
                  >
                    {k === "before" ? `Previous plan v${maps.before.version}` : `New plan v${maps.after.version}`}
                  </button>
                ))}
              </div>
              <PlanMap key={mapView} plan={maps[mapView]} heightClass="h-[380px]" />
            </div>
          )}

          {comparison.changes.length > 0 && (
            <table className="mt-4 w-full text-left text-xs">
              <thead className="uppercase text-slate-400">
                <tr><th className="py-2">Order</th><th>Change</th><th>Before</th><th>After</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comparison.changes.slice(0, 12).map((c) => (
                  <tr key={c.order_id}>
                    <td className="py-2 font-semibold">{c.customer}</td>
                    <td><span className={`rounded px-2 py-0.5 font-medium ${CHANGE_STYLE[c.change]}`}>{c.change.replace("_", " ")}</span></td>
                    <td>{c.before ? `${c.before.vehicle} #${c.before.sequence} at ${c.before.arrival}` : "-"}</td>
                    <td>{c.after ? `${c.after.vehicle} #${c.after.sequence} at ${c.after.arrival}` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {comparison.changes.length > 12 && (
            <p className="mt-2 text-xs text-slate-400">Showing 12 of {comparison.changes.length} changes.</p>
          )}
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="font-semibold">Optimization activity</h3>
        <p className="text-xs text-slate-500">Recent disruptions and the re-plans they triggered</p>
        <ul className="mt-3 grid grid-cols-3 gap-4 text-sm">
          {(events.data?.items ?? []).slice(0, 3).map((e: DisruptionEvent) => (
            <li key={e.id}>
              <p className="font-semibold">{EVENT_LABEL[e.type]}</p>
              <p className="text-xs text-slate-500">
                {e.vehicle_id ? `Vehicle #${e.vehicle_id}` : `Order #${e.order_id}`}
                {e.delay_minutes ? ` · +${e.delay_minutes} min` : ""} · handled by plan #{e.handled_by_plan_id}
              </p>
            </li>
          ))}
          {!events.loading && (events.data?.items.length ?? 0) === 0 && <li className="text-xs text-slate-400">No events yet.</li>}
        </ul>
      </section>
    </div>
  );
}
