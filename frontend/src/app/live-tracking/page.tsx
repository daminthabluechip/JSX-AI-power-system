"use client";

import { useState } from "react";
import { Search, Truck } from "lucide-react";
import FleetMapLoader from "@/components/map/FleetMapLoader";
import { trackedVehicles } from "@/lib/mockData";

// Live Tracking page: vehicle list on the left, map on the right, details for the selected vehicle.
// TODO: TOOL/API CALL HERE - replace trackedVehicles with GET /tracking/positions and refresh it
// every few seconds (polling, or SSE/WebSocket later). The backend simulator feeds this
// endpoint until JXG's real tracking feed is available.
export default function LiveTrackingPage() {
  const [tab, setTab] = useState<"active" | "all">("active");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(trackedVehicles[0].id);

  const activeCount = trackedVehicles.filter((v) => v.status === "active").length;
  const list = trackedVehicles.filter(
    (v) => (tab === "all" || v.status === "active") && v.id.toLowerCase().includes(query.toLowerCase())
  );
  const selected = trackedVehicles.find((v) => v.id === selectedId) ?? trackedVehicles[0];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Live Tracking</h2>
          <p className="text-sm text-slate-500">Monitor vehicles and deliveries in real time.</p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-600">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Live updates
        </span>
      </div>

      <div className="flex h-[520px] gap-4">
        {/* Vehicle list */}
        <aside className="flex w-72 shrink-0 flex-col rounded-xl border border-slate-200 bg-white">
          <div className="p-3">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400">
              <Search size={14} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Find a vehicle..."
                className="w-full bg-transparent text-slate-900 outline-none"
              />
            </div>
            <div className="mt-3 flex border-b border-slate-200 text-xs font-medium">
              {(["active", "all"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`-mb-px flex-1 border-b-2 pb-2 capitalize ${
                    tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500"
                  }`}
                >
                  {t} ({t === "active" ? activeCount : trackedVehicles.length})
                </button>
              ))}
            </div>
          </div>
          <ul className="flex-1 overflow-y-auto">
            {list.map((v) => (
              <li key={v.id}>
                <button
                  onClick={() => setSelectedId(v.id)}
                  className={`flex w-full items-center gap-3 border-l-2 px-3 py-3 text-left text-sm ${
                    v.id === selectedId ? "border-blue-600 bg-blue-50/50" : "border-transparent"
                  }`}
                >
                  <span className="rounded-lg bg-blue-50 p-2 text-blue-600"><Truck size={14} /></span>
                  <span className="flex-1">
                    <span className="block font-semibold">{v.id}</span>
                    <span className="block text-xs text-slate-500">Next: {v.nextStop}</span>
                  </span>
                  <span className="text-xs font-semibold">{v.eta}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Map + selected-vehicle card */}
        <div className="relative flex-1 overflow-hidden rounded-xl border border-slate-200">
          <FleetMapLoader vehicles={trackedVehicles} selectedId={selectedId} onSelect={setSelectedId} />
          <div className="absolute inset-x-4 bottom-4 z-[1000] flex items-center gap-8 rounded-xl bg-white p-4 text-xs shadow-lg">
            <div>
              <p className="text-sm font-bold">{selected.id}</p>
              <p className="text-slate-500">Vehicle</p>
            </div>
            <div><p className="text-slate-500">Driver</p><p className="font-semibold">{selected.driver}</p></div>
            <div><p className="text-slate-500">Speed</p><p className="font-semibold">{selected.speedKmh} km/h</p></div>
            <div><p className="text-slate-500">Next stop</p><p className="font-semibold">{selected.nextStop}</p></div>
            <div><p className="text-slate-500">ETA</p><p className="font-semibold text-blue-600">{selected.eta}</p></div>
          </div>
        </div>
      </div>

      {/* Data that the tracking feed provides */}
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 text-xs">
        <div>
          <p className="text-sm font-semibold">Tracking integration</p>
          <p className="text-slate-500">Live telemetry continuously improves route accuracy and execution.</p>
        </div>
        <div className="flex gap-2 text-slate-600">
          {["Current location", "Vehicle movement", "Operational status", "Actual travel times", "Delivery progress"].map((t) => (
            <span key={t} className="rounded-full bg-slate-50 px-2 py-1">{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
