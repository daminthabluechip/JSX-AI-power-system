"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, ArrowRight, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import PlanMap from "@/components/map/PlanMap";
import RouteExplanation from "@/components/plan/RouteExplanation";
import VehicleAvailableOffers from "@/components/notifications/VehicleAvailableOffers";
import {
  api, formatDuration, PRIORITY_LABEL, STATUS_LABEL, todayISO, VEHICLE_TYPE_LABEL, waitForPlan,
  type Plan, type Priority,
} from "@/lib/api";
import { useApi, usePolling } from "@/lib/useApi";

const PRIORITY_STYLE: Record<Priority, string> = {
  critical: "bg-red-50 text-red-600",
  high: "bg-orange-50 text-orange-600",
  medium: "bg-blue-50 text-blue-600",
  low: "bg-slate-100 text-slate-600",
};

type Phase = "select" | "solving" | "review" | "dispatching" | "dispatched";

// Add or remove an id from a list of selected ids.
const toggle = (list: number[], id: number) =>
  list.includes(id) ? list.filter((x) => x !== id) : [...list, id];

// The page can be opened on an existing plan with /route-planning?plan=12 (the bell menu links here
// after re-planning). Load that plan first, then start the page with it already in the review step.
export default function RoutePlanningPage() {
  return (
    <Suspense fallback={null}>
      <RoutePlanningLoader />
    </Suspense>
  );
}

function RoutePlanningLoader() {
  const planId = useSearchParams().get("plan");
  const linked = useApi(() => (planId ? api.plans.get(Number(planId)) : Promise.resolve(null)), [planId]);
  if (planId && linked.loading) return <p className="text-sm text-slate-400">Loading plan...</p>;
  return <RoutePlanningContent key={planId ?? "new"} initialPlan={linked.data} />;
}

// Route Planning: pick vehicles + orders, run the optimizer, review the plan, dispatch it.
function RoutePlanningContent({ initialPlan }: { initialPlan: Plan | null }) {
  const vehicles = useApi(() => api.vehicles.list());
  const orders = useApi(() => api.orders.list(todayISO()));

  // null = "the user has not changed the selection yet", so the defaults below apply.
  const [vehicleSel, setVehicleSel] = useState<number[] | null>(null);
  const [orderSel, setOrderSel] = useState<number[] | null>(null);
  const reviewable = initialPlan && (initialPlan.status === "ready" || initialPlan.status === "dispatched");
  const [phase, setPhase] = useState<Phase>(reviewable ? (initialPlan.status === "dispatched" ? "dispatched" : "review") : "select");
  const [plan, setPlan] = useState<Plan | null>(reviewable ? initialPlan : null);
  // Vehicles that became available while this plan has unassigned orders (checked every 6 seconds)
  const offers = usePolling(() => api.notifications.list(), 6000);
  const planOffers = (offers.data?.items ?? []).filter((n) => n.plan_id === plan?.id);
  const [error, setError] = useState<string | null>(null);
  // Shown after "Re-plan with <vehicle>": how many unassigned orders that vehicle managed to take
  const [replanNotice, setReplanNotice] = useState<string | null>(null);

  // Only vehicles that can drive, and orders that still need a plan.
  const usableVehicles = (vehicles.data?.items ?? []).filter((v) => v.status !== "maintenance");
  const plannableOrders = (orders.data?.items ?? []).filter((o) => o.status === "pending" || o.status === "scheduled");

  // Default selection: every available vehicle and every plannable order.
  const vehicleIds = vehicleSel ?? usableVehicles.filter((v) => v.status === "available").map((v) => v.id);
  const orderIds = orderSel ?? plannableOrders.map((o) => o.id);
  const setVehicleIds = setVehicleSel;
  const setOrderIds = setOrderSel;

  const chosenVehicles = usableVehicles.filter((v) => vehicleIds.includes(v.id));
  const chosenOrders = plannableOrders.filter((o) => orderIds.includes(o.id));
  const totalCapacityT = chosenVehicles.reduce((s, v) => s + v.weight_capacity_kg, 0) / 1000;
  const totalLoadT = chosenOrders.reduce((s, o) => s + o.weight_kg, 0) / 1000;
  const canPlan = chosenVehicles.length > 0 && chosenOrders.length > 0 && phase !== "solving" && phase !== "dispatching";

  // Changing the selection makes an existing plan stale.
  const edit = (fn: () => void) => { fn(); if (phase === "review") setPhase("select"); };

  async function generate() {
    setError(null);
    setReplanNotice(null);
    setPhase("solving");
    try {
      // POST /plans/generate starts the optimizer in the background (202) ...
      const started = await api.plans.generate({
        date: todayISO(), vehicle_ids: vehicleIds, order_ids: orderIds,
      });
      // ... then we poll GET /plans/{id} until it is ready or failed.
      const result = await waitForPlan(started.id);
      if (result.status === "failed") throw new Error(result.error ?? "Planning failed");
      setPlan(result);
      setPhase("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Planning failed");
      setPhase("select");
    }
  }

  async function dispatch() {
    if (!plan) return;
    setPhase("dispatching");
    try {
      await api.plans.dispatch(plan.id); // POST /plans/{id}/dispatch
      setPhase("dispatched");
      setVehicleSel(null); // back to defaults once the data reloads
      setOrderSel(null);
      vehicles.reload();
      orders.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dispatch failed");
      setPhase("review");
    }
  }

  const step = phase === "select" || phase === "solving" ? 1 : phase === "dispatched" ? 3 : 2;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">AI Route Planning</h2>
        <p className="text-sm text-slate-500">Build an optimized delivery plan in a few simple steps.</p>
      </div>

      {/* Step indicator */}
      <ol className="mx-auto flex max-w-xl items-center gap-4 text-xs font-medium">
        {["Select resources", "Review route", "Dispatch"].map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-2">
            <span className={`flex h-5 w-5 items-center justify-center rounded-full text-white ${i < step ? "bg-blue-600" : "bg-slate-300"}`}>
              {i + 1}
            </span>
            <span className={i < step ? "text-slate-900" : "text-slate-400"}>{label}</span>
            {i < 2 && <span className="h-px flex-1 bg-slate-200" />}
          </li>
        ))}
      </ol>

      {(vehicles.error || orders.error) && <ErrorBox message={(vehicles.error ?? orders.error)!} />}
      {error && <ErrorBox message={error} />}

      <div className="grid grid-cols-3 items-start gap-4">
        <div className="col-span-2 space-y-4">
          {/* Vehicles */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Select vehicles</h3>
                <p className="text-xs text-slate-500">
                  {chosenVehicles.length} selected · {totalCapacityT.toFixed(1)} t combined capacity
                </p>
              </div>
              <button onClick={() => edit(() => setVehicleIds(usableVehicles.map((v) => v.id)))} className="text-xs font-semibold text-blue-600">
                Select all
              </button>
            </div>
            <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
              {usableVehicles.map((v) => (
                <li key={v.id}>
                  <label className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${vehicleIds.includes(v.id) ? "border-blue-300 bg-blue-50/50" : "border-slate-200"}`}>
                    <input type="checkbox" checked={vehicleIds.includes(v.id)} onChange={() => edit(() => setVehicleIds(toggle(vehicleIds, v.id)))} />
                    <div className="flex-1">
                      <p className="font-semibold">{v.registration}</p>
                      <p className="text-xs text-slate-500">
                        {(v.weight_capacity_kg / 1000).toFixed(1)} t · {v.volume_capacity_m3} m³ · {v.model} · {VEHICLE_TYPE_LABEL[v.vehicle_type]}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${v.status === "available" ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600"}`}>
                      {STATUS_LABEL[v.status]}
                    </span>
                  </label>
                </li>
              ))}
              {!vehicles.loading && usableVehicles.length === 0 && <li className="py-4 text-center text-sm text-slate-400">No vehicles available.</li>}
            </ul>
          </section>

          {/* Deliveries */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Select deliveries</h3>
                <p className="text-xs text-slate-500">
                  {chosenOrders.length} selected · {totalLoadT.toFixed(1)} t total load
                </p>
              </div>
              <button onClick={() => edit(() => setOrderIds(plannableOrders.map((o) => o.id)))} className="text-xs font-semibold text-blue-600">
                Select all
              </button>
            </div>
            <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
              {plannableOrders.map((o) => (
                <li key={o.id}>
                  <label className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${orderIds.includes(o.id) ? "border-blue-300 bg-blue-50/50" : "border-slate-200"}`}>
                    <input type="checkbox" checked={orderIds.includes(o.id)} onChange={() => edit(() => setOrderIds(toggle(orderIds, o.id)))} />
                    <div className="flex-1">
                      <p className="font-semibold">{o.customer}</p>
                      <p className="text-xs text-slate-500">
                        {o.address} · {o.earliest_arrival ?? "-"}–{o.latest_arrival ?? "-"} · {(o.weight_kg / 1000).toFixed(1)} t
                        {o.required_vehicle_type && ` · needs ${VEHICLE_TYPE_LABEL[o.required_vehicle_type].toLowerCase()}`}
                      </p>
                    </div>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLE[o.priority]}`}>{PRIORITY_LABEL[o.priority]}</span>
                  </label>
                </li>
              ))}
              {!orders.loading && plannableOrders.length === 0 && <li className="py-4 text-center text-sm text-slate-400">No pending orders for today.</li>}
            </ul>
          </section>
        </div>

        {/* Route summary panel */}
        <aside className="sticky top-4 rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-blue-600" />
            <div>
              <h3 className="text-sm font-semibold">Route summary</h3>
              <p className="text-xs text-slate-500">AI-powered optimization</p>
            </div>
          </div>

          {phase === "solving" || phase === "dispatching" ? (
            <div className="my-8 text-center text-xs text-slate-500">
              <Loader2 className="mx-auto mb-2 animate-spin text-blue-600" size={28} />
              {phase === "solving" ? "Optimizing routes... this takes about 10 seconds." : "Dispatching..."}
            </div>
          ) : plan && (phase === "review" || phase === "dispatched") ? (
            <>
              <div className="my-5 text-center">
                <CheckCircle2 size={32} className="mx-auto rounded-full bg-emerald-50 p-1.5 text-emerald-600" />
                <p className="mt-2 text-sm font-semibold">{phase === "dispatched" ? "Plan dispatched" : "Route optimized"}</p>
                <p className="text-xs text-slate-500">
                  {phase === "dispatched" ? "Vehicles are now on route." : "Your plan is ready to review and dispatch."}
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200 text-xs">
                {[
                  ["Vehicles", plan.routes.length],
                  ["Stops", plan.routes.reduce((s, r) => s + r.stops.length, 0)],
                  ["Est. distance", `${plan.total_distance_km} km`],
                  ["Est. time", formatDuration(plan.total_time_min)],
                ].map(([k, v]) => (
                  <div key={k} className="bg-white p-3">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="mt-1 text-base font-bold">{v}</dd>
                  </div>
                ))}
              </dl>
              {/* Compare with the simple "nearest stop next" plan. If the two serve different numbers of orders,
                  total kilometres are not comparable, so compare kilometres per delivered order instead. */}
              {plan.baseline_served != null && plan.served !== plan.baseline_served && plan.distance_saved_per_order_pct != null ? (
                <p className="mt-3 text-center text-xs text-emerald-700">
                  Serves {plan.served} orders; a simple plan serves {plan.baseline_served}.{" "}
                  {plan.distance_saved_per_order_pct >= 0
                    ? `${plan.distance_saved_per_order_pct}% shorter per delivered order.`
                    : `${Math.abs(plan.distance_saved_per_order_pct)}% longer per delivered order.`}
                </p>
              ) : (
                plan.distance_saved_pct != null && (
                  <p className="mt-3 text-center text-xs text-emerald-600">
                    {plan.distance_saved_pct >= 0
                      ? `${plan.distance_saved_pct}% shorter than a nearest-neighbour plan`
                      : `${Math.abs(plan.distance_saved_pct)}% longer than a nearest-neighbour plan`}
                  </p>
                )
              )}
              {plan.unassigned.length > 0 && (
                <p className="mt-2 flex items-center justify-center gap-1 text-xs text-amber-600">
                  <AlertTriangle size={12} /> {plan.unassigned.length} order(s) could not be planned
                </p>
              )}
            </>
          ) : (
            <p className="my-8 text-center text-xs text-slate-400">
              {canPlan ? "Press Generate Route to optimize." : "Select at least one vehicle and one delivery."}
            </p>
          )}

          <button
            onClick={generate}
            disabled={!canPlan}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Sparkles size={14} /> {plan ? "Regenerate Route" : "Generate Route"}
          </button>
          <button
            onClick={dispatch}
            disabled={phase !== "review"}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-50"
          >
            <ArrowRight size={14} /> Dispatch Route
          </button>
        </aside>
      </div>

      {/* The planned routes: one card per vehicle with its ordered stops */}
      {plan && (phase === "review" || phase === "dispatched") && (
        <section className="space-y-4">
          <h3 className="text-lg font-bold">Planned routes</h3>
          {replanNotice && (
            <p className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm font-medium text-blue-900">{replanNotice}</p>
          )}
          <PlanMap plan={plan} />
          <div className="grid grid-cols-2 gap-4">
            {plan.routes.map((r) => (
              <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{r.vehicle.registration}</p>
                    <p className="text-xs text-slate-500">{r.vehicle.model} · leaves {r.planned_departure}</p>
                  </div>
                  <div className="text-right text-xs text-slate-500">
                    <p>Weight {r.weight_utilization_pct}%</p>
                    <p>Volume {r.volume_utilization_pct}%</p>
                  </div>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                  <div className="h-1.5 rounded-full bg-blue-600" style={{ width: `${Math.min(100, Math.max(r.weight_utilization_pct, r.volume_utilization_pct))}%` }} />
                </div>
                <ol className="mt-3 space-y-1.5 text-xs">
                  {r.stops.map((s) => (
                    <li key={s.order_id} className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-50 font-semibold text-blue-600">{s.sequence}</span>
                      <span className="flex-1 truncate font-medium">{s.customer}</span>
                      <span className="text-slate-500">{s.planned_arrival}</span>
                    </li>
                  ))}
                </ol>
                {/* Plain-language explanation of this vehicle's trip (open by default for small plans) */}
                <RouteExplanation route={r} defaultOpen={plan.routes.length <= 3} />
              </div>
            ))}
          </div>

          {plan.unassigned.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <h4 className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                <AlertTriangle size={16} /> Unassigned orders
              </h4>
              <ul className="mt-2 space-y-1 text-xs text-amber-900">
                {plan.unassigned.map((u) => (
                  <li key={u.order_id}>
                    <span className="font-semibold">{u.customer}</span> ({PRIORITY_LABEL[u.priority]}): {u.reason}
                  </li>
                ))}
              </ul>

              {/* Tell the dispatcher when another vehicle could take these orders, and let them act on it */}
              <div className="mt-4 border-t border-amber-200 pt-3">
                {planOffers.length > 0 ? (
                  <VehicleAvailableOffers
                    notes={planOffers}
                    onDone={(newPlan, note) => {
                      setPlan(newPlan); // show the new plan in place of this one
                      setPhase("review");
                      const planned = note.unassigned_total - newPlan.unassigned.length;
                      setReplanNotice(
                        `New plan v${newPlan.version} with ${note.vehicle.registration}: ${planned} of ${note.unassigned_total} ` +
                          `previously unassigned orders are now planned` +
                          (newPlan.unassigned.length > 0 ? `; ${newPlan.unassigned.length} still could not be.` : ".")
                      );
                    }}
                  />
                ) : (
                  <p className="text-xs text-amber-800">
                    No other vehicle is available right now. You will be notified here, and under the bell icon at the top,
                    as soon as a vehicle becomes available that could take these orders.
                  </p>
                )}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
