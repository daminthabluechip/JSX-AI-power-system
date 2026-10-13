"use client";

import { useState } from "react";
import { Pencil, Plus, Search, Trash2, Truck } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import VehicleForm from "@/components/forms/VehicleForm";
import { api, STATUS_LABEL, VEHICLE_TYPE_LABEL, type Vehicle, type VehicleStatus } from "@/lib/api";
import { useApi } from "@/lib/useApi";

// Badge colours per vehicle status.
const STATUS_STYLE: Record<VehicleStatus, string> = {
  on_route: "bg-blue-50 text-blue-600",
  available: "bg-emerald-50 text-emerald-600",
  maintenance: "bg-orange-50 text-orange-600",
};

// Vehicles page: fleet summary + searchable table, loaded from GET /vehicles and /vehicles/summary.
// Add / edit use VehicleForm (POST /vehicles, PATCH /vehicles/{id}); delete uses DELETE /vehicles/{id}.
export default function VehiclesPage() {
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Vehicle | "new" | null>(null); // which form is open
  const [deleting, setDeleting] = useState<Vehicle | null>(null);
  const vehicles = useApi(() => api.vehicles.list());
  const summary = useApi(() => api.vehicles.summary());

  // Filter by registration, model or driver (case-insensitive).
  const rows = (vehicles.data?.items ?? []).filter((v) =>
    `${v.registration} ${v.model} ${v.driver} ${v.vehicle_type}`.toLowerCase().includes(query.toLowerCase())
  );

  const strip = [
    ["All vehicles", summary.data?.all],
    ["Available", summary.data?.available],
    ["On route", summary.data?.on_route],
    ["Maintenance", summary.data?.maintenance],
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Vehicles</h2>
          <p className="text-sm text-slate-500">Manage and monitor your entire fleet.</p>
        </div>
        <button onClick={() => setEditing("new")} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Plus size={16} /> Add vehicle
        </button>
      </div>

      {vehicles.error && <ErrorBox message={vehicles.error} />}

      {/* Fleet summary strip */}
      <div className="grid grid-cols-4 divide-x divide-slate-200 rounded-xl border border-slate-200 bg-white py-4">
        {strip.map(([label, n]) => (
          <div key={label} className="flex items-center justify-center gap-3 text-sm">
            <span className="text-slate-500">{label}</span>
            <span className="text-xl font-bold">{n ?? "-"}</span>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex w-72 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400">
          <Search size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search vehicles or drivers..."
            className="w-full bg-transparent text-slate-900 outline-none"
          />
        </div>

        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-400">
            <tr>
              <th className="py-2">Vehicle</th>
              <th>Driver</th>
              <th>Status</th>
              <th>Capacity</th>
              <th>Shift</th>
              <th className="w-20"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((v) => (
              <tr key={v.id}>
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <span className="rounded-lg bg-blue-50 p-2 text-blue-600">
                      <Truck size={16} />
                    </span>
                    <div>
                      <p className="font-semibold">{v.registration}</p>
                      <p className="text-xs text-slate-500">{v.model} · {VEHICLE_TYPE_LABEL[v.vehicle_type] ?? v.vehicle_type}</p>
                    </div>
                  </div>
                </td>
                <td>{v.driver}</td>
                <td>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[v.status]}`}>
                    {STATUS_LABEL[v.status]}
                  </span>
                </td>
                <td className="text-xs text-slate-600">
                  {(v.weight_capacity_kg / 1000).toFixed(1)} t · {v.volume_capacity_m3} m³
                </td>
                <td className="text-xs text-slate-600">
                  {v.shift_start ?? "-"} – {v.shift_end ?? "-"}
                </td>
                <td>
                  <div className="flex gap-1 text-slate-400">
                    <button onClick={() => setEditing(v)} aria-label={`Edit ${v.registration}`} className="rounded p-1.5 hover:bg-slate-100 hover:text-blue-600"><Pencil size={15} /></button>
                    <button onClick={() => setDeleting(v)} aria-label={`Delete ${v.registration}`} className="rounded p-1.5 hover:bg-slate-100 hover:text-red-600"><Trash2 size={15} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {!vehicles.loading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-400">No vehicles found.</td>
              </tr>
            )}
            {vehicles.loading && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-400">Loading...</td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-400">
          Showing {rows.length} of {vehicles.data?.total ?? 0} vehicles
        </p>
      </div>

      {editing && (
        <VehicleForm
          vehicle={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { vehicles.reload(); summary.reload(); }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete vehicle"
          message={`Delete ${deleting.registration}? This cannot be undone.`}
          confirmLabel="Delete"
          onClose={() => setDeleting(null)}
          onConfirm={async () => { await api.vehicles.remove(deleting.id); vehicles.reload(); summary.reload(); }}
        />
      )}
    </div>
  );
}
