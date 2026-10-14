"use client";

import Link from "next/link";
import { BarChart3, CheckCircle2, Package, Sparkles, Truck } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import StatCard from "@/components/ui/StatCard";
import FleetMapLoader from "@/components/map/FleetMapLoader";
import { api, STATUS_LABEL, todayISO, type EventType, type OrderStatus } from "@/lib/api";
import { usePolling, useApi } from "@/lib/useApi";

const STATUS_STYLE: Record<OrderStatus, string> = {
  pending: "bg-slate-100 text-slate-600",
  scheduled: "bg-violet-50 text-violet-600",
  in_transit: "bg-blue-50 text-blue-600",
  delivered: "bg-emerald-50 text-emerald-600",
  cancelled: "bg-red-50 text-red-600",
};

const EVENT_TITLE: Record<EventType, string> = {
  delay: "Delay reported", breakdown: "Vehicle breakdown", rush_order: "Rush order added", cancellation: "Order cancelled",
  vehicle_available: "Vehicle became available",
};

// "5 min ago" style text for the activity list. Event times are stored in UTC.
function timeAgo(iso: string | null) {
  if (!iso) return "";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso.endsWith("Z") ? iso : iso + "Z").getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  return minutes < 1440 ? `${Math.round(minutes / 60)} hr ago` : `${Math.round(minutes / 1440)} d ago`;
}

// Dashboard: every figure comes from the API (vehicles, today's orders, the newest plan,
// recent events and live positions).
export default function DashboardPage() {
  const summary = useApi(() => api.vehicles.summary());
  const orders = useApi(() => api.orders.list(todayISO()));
  const events = useApi(() => api.events.list(4));
  const latestPlan = useApi(async () => {
    const { items } = await api.plans.list(todayISO());
    const latest = items.find((p) => p.status === "ready" || p.status === "dispatched");
    return latest ? api.plans.get(latest.id) : null;
  });
  const tracking = usePolling(() => api.tracking.positions(), 3000);

  const all = orders.data?.items ?? [];
  const count = (s: OrderStatus) => all.filter((o) => o.status === s).length;
  const routes = latestPlan.data?.routes ?? [];
  const avgUtilization = routes.length
    ? Math.round(routes.reduce((s, r) => s + r.weight_utilization_pct, 0) / routes.length)
    : null;

  // Planned arrival per order from the newest plan, shown next to each delivery.
  const eta: Record<number, string> = {};
  routes.forEach((r) => r.stops.forEach((s) => (eta[s.order_id] = s.planned_arrival)));
  const activeOrders = all.filter((o) => ["in_transit", "scheduled", "pending"].includes(o.status)).slice(0, 4);

  const trackedVehicles = (tracking.data?.items ?? [])
    .filter((v) => v.active)
    .map((v) => ({ id: v.registration, position: [v.latitude, v.longitude] as [number, number], path: v.path }));

  const error = summary.error ?? orders.error;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Good morning, Alex</h2>
          <p className="text-sm text-slate-500">Here&apos;s what&apos;s happening with your fleet today.</p>
        </div>
        <Link href="/route-planning" className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Sparkles size={16} /> Plan a route
        </Link>
      </div>

      {error && <ErrorBox message={error} />}

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Vehicles" value={summary.data?.all ?? "-"} icon={Truck}
          note={summary.data ? `${summary.data.available} available · ${summary.data.maintenance} in maintenance` : undefined} />
        <StatCard label="Active Deliveries" value={count("in_transit")} icon={Package} tone="orange"
          note={`${count("pending") + count("scheduled")} waiting to be dispatched`} />
        <StatCard label="Completed Today" value={count("delivered")} icon={CheckCircle2} tone="green"
          note={`of ${all.length} orders today`} />
        <StatCard label="Fleet Utilization" value={avgUtilization == null ? "-" : `${avgUtilization}%`} icon={BarChart3} tone="purple"
          note={avgUtilization == null ? "no plan yet" : "average load of the latest plan"} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Per-vehicle load of the newest plan */}
        <section className="col-span-2 rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Fleet utilization</h3>
          <p className="text-xs text-slate-500">Load of each vehicle in the latest plan (% of weight capacity)</p>
          {routes.length === 0 ? (
            <p className="mt-10 text-center text-sm text-slate-400">
              No plan for today yet. <Link href="/route-planning" className="font-semibold text-blue-600">Create one</Link>
            </p>
          ) : (
            <div className="mt-4 flex h-48 gap-4">
              {routes.map((r) => (
                <div key={r.id} className="flex h-full flex-1 flex-col items-center gap-1">
                  <span className="text-xs font-semibold">{Math.round(r.weight_utilization_pct)}%</span>
                  {/* The bar's height is a percentage of this area, which needs a definite height (flex-1 in a fixed-height column) */}
                  <div className="flex w-full max-w-16 flex-1 items-end">
                    <div className="w-full rounded-t bg-blue-600" style={{ height: `${Math.min(100, r.weight_utilization_pct)}%` }} />
                  </div>
                  <span className="text-xs text-slate-400">{r.vehicle.registration.replace("VH-", "")}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Live fleet</h3>
              <p className="text-xs text-slate-500">{trackedVehicles.length} vehicles currently active</p>
            </div>
            <Link href="/live-tracking" className="text-xs font-semibold text-blue-600">View map →</Link>
          </div>
          <div className="mt-4 h-40 overflow-hidden rounded-lg">
            <FleetMapLoader vehicles={trackedVehicles} />
          </div>
        </section>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <section className="col-span-2 rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Active deliveries</h3>
            <Link href="/deliveries" className="text-xs font-semibold text-blue-600">View all →</Link>
          </div>
          <ul className="mt-3 divide-y divide-slate-100">
            {activeOrders.map((o) => (
              <li key={o.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-semibold">{o.customer}</p>
                  <p className="text-xs text-slate-500">{o.address}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[o.status]}`}>{STATUS_LABEL[o.status]}</span>
                <span className="w-14 text-right text-xs font-semibold">{eta[o.id] ?? "-"}</span>
              </li>
            ))}
            {activeOrders.length === 0 && <li className="py-6 text-center text-sm text-slate-400">Nothing in progress.</li>}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Recent activity</h3>
          <p className="text-xs text-slate-500">Disruptions and the re-plans they triggered</p>
          <ul className="mt-3 space-y-3">
            {(events.data?.items ?? []).map((e) => (
              <li key={e.id} className="text-sm">
                <p className="font-semibold">{EVENT_TITLE[e.type]}</p>
                <p className="text-xs text-slate-500">
                  {e.vehicle_id ? `Vehicle #${e.vehicle_id}` : `Order #${e.order_id}`}
                  {e.delay_minutes ? ` · +${e.delay_minutes} min` : ""} · {timeAgo(e.occurred_at)}
                </p>
              </li>
            ))}
            {!events.loading && (events.data?.items.length ?? 0) === 0 && <li className="text-xs text-slate-400">No events yet.</li>}
          </ul>
        </section>
      </div>
    </div>
  );
}
