"use client";

import { Loader2, Truck } from "lucide-react";
import { useState } from "react";
import { api, PRIORITY_LABEL, VEHICLE_TYPE_LABEL, waitForPlan, type AppNotification, type Plan } from "@/lib/api";

export default function VehicleAvailableOffers({
  notes,
  onDone,
}: {
  notes: AppNotification[];
  onDone?: (plan: Plan, note: AppNotification) => void;
}) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ registration: string; plan: Plan; before: number } | null>(null);

  async function replan(note: AppNotification) {
    setBusyId(note.vehicle.id);
    setError(null);
    setResult(null);
    try {
      const out = await api.events.report(note.suggested_event);
      const plan = await waitForPlan(out.plan.id);
      if (plan.status === "failed") throw new Error(plan.error ?? "Re-planning failed");
      setResult({ registration: note.vehicle.registration, plan, before: note.unassigned_total });
      onDone?.(plan, note);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Re-planning failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-3">
      {notes.map((n) => (
        <div key={n.vehicle.id} className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
          <div className="flex items-start gap-2">
            <Truck size={16} className="mt-0.5 shrink-0 text-emerald-600" />
            <div className="flex-1">
              <p className="font-semibold">{n.message}</p>
              <ul className="mt-1 space-y-0.5 text-emerald-800">
                {n.orders.slice(0, 5).map((o) => (
                  <li key={o.order_id}>
                    {o.customer} ({PRIORITY_LABEL[o.priority]}, {(o.weight_kg / 1000).toFixed(1)} t)
                  </li>
                ))}
                {n.orders.length > 5 && <li>...and {n.orders.length - 5} more</li>}
              </ul>
              <p className="mt-1 text-emerald-700">
                {VEHICLE_TYPE_LABEL[n.vehicle.vehicle_type]}, {(n.vehicle.weight_capacity_kg / 1000).toFixed(1)} t capacity. The
                optimizer decides whether they really fit into the day.
              </p>
            </div>
          </div>
          <button
            onClick={() => replan(n)}
            disabled={busyId !== null}
            className="mt-2 flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white disabled:opacity-60"
          >
            {busyId === n.vehicle.id && <Loader2 size={13} className="animate-spin" />}
            {busyId === n.vehicle.id ? "Re-planning... about 10 seconds" : `Re-plan with ${n.vehicle.registration}`}
          </button>
        </div>
      ))}

      {error && <p className="rounded-lg bg-red-50 p-2 text-xs text-red-700">{error}</p>}
      {result && (
        <p className="rounded-lg bg-blue-50 p-2 text-xs text-blue-900">
          New plan v{result.plan.version} with {result.registration}: {result.before - result.plan.unassigned.length} of{" "}
          {result.before} unassigned orders are now planned
          {result.plan.unassigned.length > 0 ? `, ${result.plan.unassigned.length} still could not be.` : "."}
        </p>
      )}
    </div>
  );
}
