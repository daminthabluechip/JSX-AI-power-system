"use client";

import { useState } from "react";
import { MapPin, Plus, Search } from "lucide-react";
import { orders, type DeliveryStatus, type Priority } from "@/lib/mockData";

const STATUS_STYLE: Record<DeliveryStatus, string> = {
  "In Transit": "bg-blue-50 text-blue-600",
  Scheduled: "bg-violet-50 text-violet-600",
  Delivered: "bg-emerald-50 text-emerald-600",
};

const PRIORITY_STYLE: Record<Priority, string> = {
  Critical: "bg-red-50 text-red-600",
  High: "bg-orange-50 text-orange-600",
  Medium: "bg-blue-50 text-blue-600",
  Low: "bg-slate-100 text-slate-600",
};

const TABS: ("All orders" | DeliveryStatus)[] = ["All orders", "Scheduled", "In Transit", "Delivered"];

// Deliveries page: status tabs, search, priority filter and the orders table.
// TODO: TOOL/API CALL HERE - load orders with GET /orders?status=&priority=&q=
// (server-side filtering + pagination); "New delivery" should POST /orders.
export default function DeliveriesPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("All orders");
  const [priority, setPriority] = useState<"all" | Priority>("all");
  const [query, setQuery] = useState("");

  // Apply the three filters together.
  const rows = orders.filter(
    (o) =>
      (tab === "All orders" || o.status === tab) &&
      (priority === "all" || o.priority === priority) &&
      `${o.id} ${o.customer}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Deliveries</h2>
          <p className="text-sm text-slate-500">Track and manage all customer orders.</p>
        </div>
        <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Plus size={16} /> New delivery
        </button>
      </div>

      {/* Status tabs with counts */}
      <div className="flex gap-6 border-b border-slate-200 text-sm">
        {TABS.map((t) => {
          const count = t === "All orders" ? orders.length : orders.filter((o) => o.status === t).length;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`-mb-px border-b-2 pb-2 font-medium ${
                tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500"
              }`}
            >
              {t} <span className="ml-1 rounded bg-slate-100 px-1.5 text-xs">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex w-72 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400">
            <Search size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search customer or order ID..."
              className="w-full bg-transparent text-slate-900 outline-none"
            />
          </div>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as "all" | Priority)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="all">All priorities</option>
            {(Object.keys(PRIORITY_STYLE) as Priority[]).map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>

        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-400">
            <tr>
              <th className="py-2">Order</th>
              <th>Customer</th>
              <th>Delivery location</th>
              <th>ETA</th>
              <th>Priority</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((o) => (
              <tr key={o.id}>
                <td className="py-3 font-semibold">{o.id}</td>
                <td className="font-semibold">{o.customer}</td>
                <td>
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <MapPin size={14} className="text-slate-400" /> {o.location}
                  </span>
                </td>
                <td>{o.eta}</td>
                <td>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLE[o.priority]}`}>
                    {o.priority}
                  </span>
                </td>
                <td>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[o.status]}`}>
                    {o.status}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-400">No deliveries found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
