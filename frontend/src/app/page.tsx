import Link from "next/link";
import { Truck, Package, CheckCircle2, BarChart3, Sparkles } from "lucide-react";
import StatCard from "@/components/ui/StatCard";
import FleetMapLoader from "@/components/map/FleetMapLoader";
import {
  dashboardStats,
  weeklyUtilization,
  activeDeliveries,
  recentActivity,
  trackedVehicles,
  type DeliveryStatus,
} from "@/lib/mockData";

// Badge colours per delivery status.
const STATUS_STYLE: Record<DeliveryStatus, string> = {
  "In Transit": "bg-blue-50 text-blue-600",
  Scheduled: "bg-violet-50 text-violet-600",
  Delivered: "bg-emerald-50 text-emerald-600",
};

// Dashboard page (server component).
// TODO: TOOL/API CALL HERE - fetch stats from GET /reports/summary and the lists
// from GET /orders?status=active and GET /events?limit=4 instead of mockData.
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header + primary action */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Good morning, Alex</h2>
          <p className="text-sm text-slate-500">Here&apos;s what&apos;s happening with your fleet today.</p>
        </div>
        <Link
          href="/route-planning"
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <Sparkles size={16} /> Plan a route
        </Link>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Vehicles" value={dashboardStats.totalVehicles} icon={Truck} />
        <StatCard label="Active Deliveries" value={dashboardStats.activeDeliveries} icon={Package} tone="orange" />
        <StatCard label="Completed Today" value={dashboardStats.completedToday} icon={CheckCircle2} tone="green" />
        <StatCard label="Fleet Utilization" value={`${dashboardStats.fleetUtilization}%`} icon={BarChart3} tone="purple" />
      </div>

      {/* Utilization chart (plain divs; no chart library needed) + live fleet map placeholder */}
      <div className="grid grid-cols-3 gap-4">
        <section className="col-span-2 rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Fleet utilization</h3>
          <p className="text-xs text-slate-500">Weekly vehicle performance</p>
          <div className="mt-4 flex h-48 items-end gap-4">
            {weeklyUtilization.map((d) => (
              <div key={d.day} className="flex flex-1 flex-col items-center gap-2">
                <div className="w-full rounded-t bg-blue-600" style={{ height: `${d.value}%` }} />
                <span className="text-xs text-slate-400">{d.day}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Live fleet</h3>
            <Link href="/live-tracking" className="text-xs font-semibold text-blue-600">View map →</Link>
          </div>
          {/* TODO: TOOL/API CALL HERE - render the Leaflet map component with GET /tracking/positions */}
          <div className="mt-4 h-40 overflow-hidden rounded-lg">
            <FleetMapLoader vehicles={trackedVehicles} />
          </div>
        </section>
      </div>

      {/* Active deliveries + recent activity */}
      <div className="grid grid-cols-3 gap-4">
        <section className="col-span-2 rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Active deliveries</h3>
            <Link href="/deliveries" className="text-xs font-semibold text-blue-600">View all →</Link>
          </div>
          <ul className="mt-3 divide-y divide-slate-100">
            {activeDeliveries.map((d) => (
              <li key={d.customer} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-semibold">{d.customer}</p>
                  <p className="text-xs text-slate-500">{d.location}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[d.status]}`}>
                  {d.status}
                </span>
                <span className="text-xs font-semibold">{d.eta}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="font-semibold">Recent activity</h3>
          <p className="text-xs text-slate-500">Live operational updates</p>
          <ul className="mt-3 space-y-3">
            {recentActivity.map((a) => (
              <li key={a.title} className="text-sm">
                <p className="font-semibold">{a.title}</p>
                <p className="text-xs text-slate-500">
                  {a.detail} · {a.time}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
