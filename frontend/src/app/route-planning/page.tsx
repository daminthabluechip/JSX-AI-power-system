"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { planDeliveries, planVehicles, type Priority } from "@/lib/mockData";

const PRIORITY_STYLE: Record<Priority, string> = {
  Critical: "bg-red-50 text-red-600",
  High: "bg-orange-50 text-orange-600",
  Medium: "bg-blue-50 text-blue-600",
  Low: "bg-slate-100 text-slate-600",
};

// Small helper: toggle an id in a list of selected ids.
const toggle = <T,>(list: T[], item: T) =>
  list.includes(item) ? list.filter((x) => x !== item) : [...list, item];

// Route Planning page: pick vehicles + deliveries, then generate and dispatch a plan.
export default function RoutePlanningPage() {
  const [vehicleIds, setVehicleIds] = useState<string[]>(["VH 2048", "VH 1042"]);
  const [deliveryIds, setDeliveryIds] = useState<number[]>([1, 2, 3]);
  const [planned, setPlanned] = useState(true); // true once a plan has been generated

  const chosenVehicles = planVehicles.filter((v) => vehicleIds.includes(v.id));
  const chosenDeliveries = planDeliveries.filter((d) => deliveryIds.includes(d.id));
  const totalCapacity = chosenVehicles.reduce((s, v) => s + v.capacityTons, 0);
  const totalLoad = chosenDeliveries.reduce((s, d) => s + d.weightTons, 0);

  // Selections make the previous plan stale, so hide the result until regenerated.
  const changeVehicles = (id: string) => { setVehicleIds((l) => toggle(l, id)); setPlanned(false); };
  const changeDeliveries = (id: number) => { setDeliveryIds((l) => toggle(l, id)); setPlanned(false); };

  const canPlan = chosenVehicles.length > 0 && chosenDeliveries.length > 0;

  function regenerate() {
    // TODO: TOOL/API CALL HERE - POST /plans/generate with
    // { vehicle_ids: vehicleIds, order_ids: deliveryIds, date }, then poll
    // GET /plans/{id} until the OR-Tools job finishes and show its real totals.
    setPlanned(true);
  }

  function dispatch() {
    // TODO: TOOL/API CALL HERE - POST /plans/{id}/dispatch to send the plan to the vehicles.
    alert("Dispatch is not connected to the backend yet.");
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">AI Route Planning</h2>
        <p className="text-sm text-slate-500">Build an optimized delivery plan in a few simple steps.</p>
      </div>

      {/* Step indicator (step 2 is active in the mockup) */}
      <ol className="mx-auto flex max-w-xl items-center gap-4 text-xs font-medium">
        {["Select resources", "Review route", "Dispatch"].map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-2">
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full text-white ${
                i < 2 ? "bg-blue-600" : "bg-slate-300"
              }`}
            >
              {i + 1}
            </span>
            <span className={i < 2 ? "text-slate-900" : "text-slate-400"}>{label}</span>
            {i < 2 && <span className="h-px flex-1 bg-slate-200" />}
          </li>
        ))}
      </ol>

      <div className="grid grid-cols-3 items-start gap-4">
        <div className="col-span-2 space-y-4">
          {/* Vehicles */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Select vehicles</h3>
                <p className="text-xs text-slate-500">
                  {chosenVehicles.length} selected · {totalCapacity} t combined capacity
                </p>
              </div>
              <button
                onClick={() => { setVehicleIds(planVehicles.map((v) => v.id)); setPlanned(false); }}
                className="text-xs font-semibold text-blue-600"
              >
                Select all
              </button>
            </div>
            <ul className="mt-3 space-y-2">
              {/* TODO: TOOL/API CALL HERE - load the fleet with GET /vehicles?status=available,on_route */}
              {planVehicles.map((v) => (
                <li key={v.id}>
                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${
                      vehicleIds.includes(v.id) ? "border-blue-300 bg-blue-50/50" : "border-slate-200"
                    }`}
                  >
                    <input type="checkbox" checked={vehicleIds.includes(v.id)} onChange={() => changeVehicles(v.id)} />
                    <div className="flex-1">
                      <p className="font-semibold">{v.id}</p>
                      <p className="text-xs text-slate-500">{v.loadTons} / {v.capacityTons} t loaded</p>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        v.status === "Available" ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600"
                      }`}
                    >
                      {v.status}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </section>

          {/* Deliveries */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Select deliveries</h3>
                <p className="text-xs text-slate-500">
                  {chosenDeliveries.length} selected · {totalLoad.toFixed(1)} t total load
                </p>
              </div>
              <button
                onClick={() => { setDeliveryIds(planDeliveries.map((d) => d.id)); setPlanned(false); }}
                className="text-xs font-semibold text-blue-600"
              >
                Select all
              </button>
            </div>
            <ul className="mt-3 space-y-2">
              {/* TODO: TOOL/API CALL HERE - load pending orders with GET /orders?status=pending&date= */}
              {planDeliveries.map((d) => (
                <li key={d.id}>
                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${
                      deliveryIds.includes(d.id) ? "border-blue-300 bg-blue-50/50" : "border-slate-200"
                    }`}
                  >
                    <input type="checkbox" checked={deliveryIds.includes(d.id)} onChange={() => changeDeliveries(d.id)} />
                    <div className="flex-1">
                      <p className="font-semibold">{d.customer}</p>
                      <p className="text-xs text-slate-500">{d.id} · Due {d.due}</p>
                    </div>
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLE[d.priority]}`}>
                      {d.priority}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Route summary panel */}
        <aside className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-blue-600" />
            <div>
              <h3 className="text-sm font-semibold">Route summary</h3>
              <p className="text-xs text-slate-500">AI-powered optimization</p>
            </div>
          </div>

          {planned && canPlan ? (
            <>
              <div className="my-5 text-center">
                <CheckCircle2 size={32} className="mx-auto rounded-full bg-emerald-50 p-1.5 text-emerald-600" />
                <p className="mt-2 text-sm font-semibold">Route optimized</p>
                <p className="text-xs text-slate-500">Your plan is ready to review and dispatch.</p>
              </div>
              {/* Mock figures: the real ones will come from the plan returned by the optimizer. */}
              <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200 text-xs">
                {[
                  ["Vehicles", chosenVehicles.length],
                  ["Stops", chosenDeliveries.length],
                  ["Est. distance", "84 km"],
                  ["Est. time", "3h 24m"],
                ].map(([k, v]) => (
                  <div key={k} className="bg-white p-3">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="mt-1 text-base font-bold">{v}</dd>
                  </div>
                ))}
              </dl>
            </>
          ) : (
            <p className="my-8 text-center text-xs text-slate-400">
              {canPlan ? "Selection changed. Regenerate the route." : "Select at least one vehicle and one delivery."}
            </p>
          )}

          <button
            onClick={regenerate}
            disabled={!canPlan}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Sparkles size={14} /> Regenerate Route
          </button>
          <button
            onClick={dispatch}
            disabled={!planned || !canPlan}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 py-2 text-sm font-semibold text-blue-600 hover:bg-blue-50 disabled:opacity-50"
          >
            <ArrowRight size={14} /> Dispatch Route
          </button>
        </aside>
      </div>
    </div>
  );
}
