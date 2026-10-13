"use client";

import { useState } from "react";
import { MapPin, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ImportOrders from "@/components/forms/ImportOrders";
import OrderForm from "@/components/forms/OrderForm";
import {
  api, PRIORITY_LABEL, STATUS_LABEL, todayISO, VEHICLE_TYPE_LABEL,
  type Order, type OrderStatus, type Priority,
} from "@/lib/api";
import { useApi } from "@/lib/useApi";

const STATUS_STYLE: Record<OrderStatus, string> = {
  pending: "bg-slate-100 text-slate-600",
  scheduled: "bg-violet-50 text-violet-600",
  in_transit: "bg-blue-50 text-blue-600",
  delivered: "bg-emerald-50 text-emerald-600",
  cancelled: "bg-red-50 text-red-600",
};

const PRIORITY_STYLE: Record<Priority, string> = {
  critical: "bg-red-50 text-red-600",
  high: "bg-orange-50 text-orange-600",
  medium: "bg-blue-50 text-blue-600",
  low: "bg-slate-100 text-slate-600",
};

const TABS: ("all" | OrderStatus)[] = ["all", "pending", "scheduled", "in_transit", "delivered"];

// Deliveries page: status tabs, search, priority filter and the orders table (GET /orders).
// The ETA column comes from the newest plan for today (planned arrival of each stop).
// New / edit use OrderForm (POST /orders, PATCH /orders/{id}); delete uses DELETE /orders/{id}.
export default function DeliveriesPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("all");
  const [priority, setPriority] = useState<"all" | Priority>("all");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Order | "new" | null>(null); // which form is open
  const [deleting, setDeleting] = useState<Order | null>(null);
  const [importing, setImporting] = useState(false);

  const orders = useApi(() => api.orders.list(todayISO()));

  // Planned arrival per order from the newest finished plan, if one exists.
  const etas = useApi(async () => {
    const { items } = await api.plans.list(todayISO());
    const latest = items.find((p) => p.status === "ready" || p.status === "dispatched");
    const map: Record<number, string> = {};
    if (latest) {
      const plan = await api.plans.get(latest.id);
      plan.routes.forEach((r) => r.stops.forEach((s) => (map[s.order_id] = s.planned_arrival)));
    }
    return map;
  });

  const all = orders.data?.items ?? [];
  const rows = all.filter(
    (o) =>
      (tab === "all" || o.status === tab) &&
      (priority === "all" || o.priority === priority) &&
      `${o.id} ${o.customer}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Deliveries</h2>
          <p className="text-sm text-slate-500">Track and manage all customer orders for today.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setImporting(true)} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold hover:bg-slate-50">
            <Upload size={16} /> Import CSV
          </button>
          <button onClick={() => setEditing("new")} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus size={16} /> New delivery
          </button>
        </div>
      </div>

      {orders.error && <ErrorBox message={orders.error} />}

      {/* Status tabs with counts */}
      <div className="flex gap-6 border-b border-slate-200 text-sm">
        {TABS.map((t) => {
          const count = t === "all" ? all.length : all.filter((o) => o.status === t).length;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`-mb-px border-b-2 pb-2 font-medium ${
                tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500"
              }`}
            >
              {t === "all" ? "All orders" : STATUS_LABEL[t]}
              <span className="ml-1 rounded bg-slate-100 px-1.5 text-xs">{count}</span>
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
            {(Object.keys(PRIORITY_LABEL) as Priority[]).map((p) => (
              <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>
            ))}
          </select>
        </div>

        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-400">
            <tr>
              <th className="py-2">Order</th>
              <th>Customer</th>
              <th>Delivery location</th>
              <th>Window</th>
              <th>ETA</th>
              <th>Priority</th>
              <th>Status</th>
              <th className="w-20"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((o) => (
              <tr key={o.id}>
                <td className="py-3 font-semibold">{o.id}</td>
                <td className="font-semibold">
                  {o.customer}
                  {o.required_vehicle_type && (
                    <span className="ml-2 rounded bg-cyan-50 px-1.5 py-0.5 text-[10px] font-medium text-cyan-700">
                      {VEHICLE_TYPE_LABEL[o.required_vehicle_type]} only
                    </span>
                  )}
                </td>
                <td>
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <MapPin size={14} className="text-slate-400" /> {o.address}
                  </span>
                </td>
                <td className="text-xs text-slate-500">
                  {o.earliest_arrival ?? "-"} – {o.latest_arrival ?? "-"}
                </td>
                <td className="font-medium">{etas.data?.[o.id] ?? "-"}</td>
                <td>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLE[o.priority]}`}>
                    {PRIORITY_LABEL[o.priority]}
                  </span>
                </td>
                <td>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[o.status]}`}>
                    {STATUS_LABEL[o.status]}
                  </span>
                </td>
                <td>
                  <div className="flex gap-1 text-slate-400">
                    <button onClick={() => setEditing(o)} aria-label={`Edit order ${o.id}`} className="rounded p-1.5 hover:bg-slate-100 hover:text-blue-600"><Pencil size={15} /></button>
                    <button onClick={() => setDeleting(o)} aria-label={`Delete order ${o.id}`} className="rounded p-1.5 hover:bg-slate-100 hover:text-red-600"><Trash2 size={15} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {!orders.loading && rows.length === 0 && (
              <tr>
                <td colSpan={8} className="py-6 text-center text-slate-400">No deliveries found.</td>
              </tr>
            )}
            {orders.loading && (
              <tr>
                <td colSpan={8} className="py-6 text-center text-slate-400">Loading...</td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-400">
          Showing {rows.length} of {all.length} deliveries
        </p>
      </div>

      {importing && <ImportOrders onClose={() => setImporting(false)} onImported={() => orders.reload()} />}
      {editing && (
        <OrderForm
          order={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { orders.reload(); etas.reload(); }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete delivery"
          message={`Delete the order for ${deleting.customer}? This cannot be undone.`}
          confirmLabel="Delete"
          onClose={() => setDeleting(null)}
          onConfirm={async () => { await api.orders.remove(deleting.id); orders.reload(); }}
        />
      )}
    </div>
  );
}
