"use client";

import { useState } from "react";
import { Plus, Search, Truck } from "lucide-react";
import { vehicles, vehicleSummary, type VehicleStatus } from "@/lib/mockData";

// Badge colours per vehicle status.
const STATUS_STYLE: Record<VehicleStatus, string> = {
  "On Route": "bg-blue-50 text-blue-600",
  Available: "bg-emerald-50 text-emerald-600",
  Maintenance: "bg-orange-50 text-orange-600",
};

// Vehicles page: fleet summary + searchable table.
// TODO: TOOL/API CALL HERE - load vehicles with GET /vehicles and summary counts
// with GET /vehicles/summary; "Add vehicle" should POST /vehicles.
export default function VehiclesPage() {
  const [query, setQuery] = useState("");

  // Filter by vehicle id, model or driver (case-insensitive).
  const rows = vehicles.filter((v) =>
    `${v.id} ${v.model} ${v.driver}`.toLowerCase().includes(query.toLowerCase())
  );

  const summary = [
    ["All vehicles", vehicleSummary.all],
    ["Available", vehicleSummary.available],
    ["On route", vehicleSummary.onRoute],
    ["Maintenance", vehicleSummary.maintenance],
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Vehicles</h2>
          <p className="text-sm text-slate-500">Manage and monitor your entire fleet.</p>
        </div>
        <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Plus size={16} /> Add vehicle
        </button>
      </div>

      {/* Fleet summary strip */}
      <div className="grid grid-cols-4 divide-x divide-slate-200 rounded-xl border border-slate-200 bg-white py-4">
        {summary.map(([label, n]) => (
          <div key={label} className="flex items-center justify-center gap-3 text-sm">
            <span className="text-slate-500">{label}</span>
            <span className="text-xl font-bold">{n}</span>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400 w-72">
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
              <th>Current location</th>
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
                      <p className="font-semibold">{v.id}</p>
                      <p className="text-xs text-slate-500">{v.model}</p>
                    </div>
                  </div>
                </td>
                <td>{v.driver}</td>
                <td>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[v.status]}`}>
                    {v.status}
                  </span>
                </td>
                <td>
                  {/* Load bar: loaded tons / capacity tons */}
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full bg-blue-600"
                        style={{ width: `${(v.loadTons / v.capacityTons) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500">
                      {v.loadTons} / {v.capacityTons} t
                    </span>
                  </div>
                </td>
                <td>{v.location}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-slate-400">No vehicles found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
