"use client";

import { useState } from "react";
import { AlertTriangle, ChevronRight, CheckCircle2, Sparkles, Wrench, Zap, XCircle } from "lucide-react";
import {
  disruptions,
  routeComparison,
  optimizationImpact,
  optimizationActivity,
  type DisruptionKind,
} from "@/lib/mockData";

// Icon + colour for each disruption type.
const KIND_STYLE: Record<DisruptionKind, { icon: typeof Zap; box: string }> = {
  traffic: { icon: AlertTriangle, box: "bg-red-50 text-red-500" },
  breakdown: { icon: Wrench, box: "bg-orange-50 text-orange-500" },
  urgent: { icon: Zap, box: "bg-blue-50 text-blue-600" },
  cancelled: { icon: XCircle, box: "bg-violet-50 text-violet-600" },
};

// One side of the comparison (current or optimized).
function RouteCard({
  title,
  badge,
  data,
  good,
}: {
  title: string;
  badge: string;
  data: typeof routeComparison.current;
  good: boolean; // true = optimized (green), false = current (red)
}) {
  const accent = good ? "border-t-emerald-500" : "border-t-red-400";
  return (
    <div className={`rounded-xl border border-t-2 border-slate-200 bg-white p-5 ${accent}`}>
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">{title}</h4>
        <span className={`rounded-full px-2 py-0.5 text-xs ${good ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
          {badge}
        </span>
      </div>
      <p className="mt-3 rounded-lg bg-slate-50 p-2 text-xs font-medium">{data.sequence.join(" → ")}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div><dt className="text-slate-500">Total distance</dt><dd className="text-base font-bold">{data.distanceKm} km</dd></div>
        <div><dt className="text-slate-500">Estimated travel time</dt><dd className="text-base font-bold">{data.time}</dd></div>
        <div><dt className="text-slate-500">Deliveries</dt><dd className="text-base font-bold">{data.deliveries}</dd></div>
        <div>
          <dt className="text-slate-500">Delayed deliveries</dt>
          <dd className={`text-base font-bold ${good ? "text-emerald-600" : "text-red-500"}`}>{data.delayed} delayed</dd>
        </div>
      </dl>
      <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
        Vehicle assigned: <span className="font-semibold text-slate-900">{data.vehicle}</span>
      </p>
    </div>
  );
}

// Optimization page: pick a disruption, see the AI re-plan, compare routes, confirm.
export default function OptimizationPage() {
  const [selected, setSelected] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const event = disruptions[selected];

  function confirmRoute() {
    // TODO: TOOL/API CALL HERE - POST /events with the selected disruption (this triggers the
    // re-plan), then POST /plans/{newPlanId}/confirm and compare versions with
    // GET /plans/{id}/compare/{other} to fill the comparison and impact figures below.
    setConfirmed(true);
  }

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

      <div className="grid grid-cols-2 gap-4">
        {/* Disruption list */}
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Active disruptions</h3>
              <p className="text-xs text-slate-500">Select an event to review its operational impact</p>
            </div>
            <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-500">{disruptions.length} active</span>
          </div>
          {/* TODO: TOOL/API CALL HERE - load open events with GET /events?status=open */}
          <ul className="mt-3 space-y-2">
            {disruptions.map((d, i) => {
              const { icon: Icon, box } = KIND_STYLE[d.kind];
              return (
                <li key={d.title}>
                  <button
                    onClick={() => { setSelected(i); setConfirmed(false); }}
                    className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm ${
                      selected === i ? "border-blue-300 bg-blue-50/50" : "border-slate-200"
                    }`}
                  >
                    <span className={`rounded-lg p-2 ${box}`}><Icon size={16} /></span>
                    <span className="flex-1">
                      <span className="block font-semibold">{d.title}</span>
                      <span className="block text-xs text-slate-500">{d.detail}</span>
                    </span>
                    <ChevronRight size={16} className="text-slate-400" />
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        {/* AI recalibration result */}
        <section className="rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 p-5 text-white">
          <div className="flex items-center gap-2">
            <Sparkles size={18} />
            <div>
              <h3 className="font-semibold">Instant route recalibration</h3>
              <p className="text-xs text-blue-100">AI response for the selected disruption</p>
            </div>
          </div>
          <p className="mt-4 rounded-lg bg-white/10 p-3 text-xs">
            Selected event<br /><span className="text-sm font-semibold">{event.title}</span>
          </p>
          <div className="my-5 text-center">
            <CheckCircle2 size={32} className="mx-auto rounded-full bg-white/20 p-1.5" />
            <p className="mt-2 font-semibold">Updated plan ready</p>
            <p className="text-xs text-blue-100">3 routes recalculated and 5 deliveries reassigned with no missed time windows</p>
          </div>
          {/* Mock figures: will come from the re-plan result. */}
          <dl className="grid grid-cols-3 divide-x divide-white/20 rounded-lg bg-white/10 py-3 text-center text-xs">
            <div><dt className="text-blue-100">Affected routes</dt><dd className="text-xl font-bold">3</dd></div>
            <div><dt className="text-blue-100">At-risk deliveries</dt><dd className="text-xl font-bold">2</dd></div>
            <div><dt className="text-blue-100">Potential delay</dt><dd className="text-xl font-bold">26 min</dd></div>
          </dl>
          <button
            onClick={confirmRoute}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-white py-2 text-sm font-semibold text-blue-700"
          >
            <CheckCircle2 size={16} /> {confirmed ? "Optimized successfully" : "Apply optimization"}
          </button>
        </section>
      </div>

      {/* Route comparison */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Route Comparison</h3>
            <p className="text-xs text-slate-500">See how AI optimization improves the selected route.</p>
          </div>
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-600">Optimization complete</span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <RouteCard title="Current Route" badge="Current" data={routeComparison.current} good={false} />
          <RouteCard title="Optimized Route" badge="Recommended" data={routeComparison.optimized} good />
        </div>

        {/* TODO: TOOL/API CALL HERE - replace this schematic with the Leaflet map showing both
            polylines (GET /plans/{id} routes + stops). */}
        <div className="mt-4 rounded-lg bg-slate-50 p-4">
          <p className="text-sm font-semibold">Route map</p>
          <svg viewBox="0 0 600 140" className="mt-2 h-36 w-full rounded bg-emerald-50/40">
            <path d="M40 110 C180 60 260 40 330 55 S 520 40 560 40" stroke="#ef4444" strokeWidth="3" strokeDasharray="8 6" fill="none" />
            <path d="M40 110 C120 130 220 100 330 55 S 480 20 560 40" stroke="#16a34a" strokeWidth="3" fill="none" />
            <text x="30" y="128" fontSize="11">START Colombo</text>
            <text x="480" y="30" fontSize="11">DESTINATION Kandy</text>
          </svg>
          <p className="mt-1 flex gap-4 text-xs text-slate-500">
            <span><span className="text-red-500">---</span> Current route</span>
            <span><span className="text-emerald-600">━</span> Optimized route</span>
          </p>
        </div>

        {/* Impact figures */}
        <div className="mt-4 grid grid-cols-4 gap-3">
          {optimizationImpact.map((i) => (
            <div key={i.label} className="rounded-lg border border-slate-200 p-3 text-xs">
              <p className="text-slate-500">{i.label}</p>
              <p className="text-base font-bold">{i.value}</p>
            </div>
          ))}
        </div>

        {confirmed && (
          <p className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">
            <CheckCircle2 size={16} /> Optimized route confirmed. The updated plan is ready to be dispatched.
          </p>
        )}
      </section>

      {/* Activity log */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="font-semibold">Optimization activity</h3>
        <p className="text-xs text-slate-500">Recent automated planning decisions</p>
        {/* TODO: TOOL/API CALL HERE - load history with GET /events?handled=true&limit=3 */}
        <ul className="mt-3 grid grid-cols-3 gap-4 text-sm">
          {optimizationActivity.map((a) => (
            <li key={a.title}>
              <p className="font-semibold">{a.title}</p>
              <p className="text-xs text-slate-500">{a.detail} · {a.time}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
