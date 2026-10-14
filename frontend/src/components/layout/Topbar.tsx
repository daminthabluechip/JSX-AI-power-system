"use client";

import Link from "next/link";
import { useState } from "react";
import { Bell, Search } from "lucide-react";
import VehicleAvailableOffers from "@/components/notifications/VehicleAvailableOffers";
import { api, type Plan } from "@/lib/api";
import { usePolling } from "@/lib/useApi";

// Top bar: global search on the left, system status + notifications on the right.
// The bell shows how many things need attention (checked every 6 seconds).
export default function Topbar() {
  const [open, setOpen] = useState(false);
  const [newPlan, setNewPlan] = useState<Plan | null>(null); // set after a re-plan from the menu
  const notifications = usePolling(() => api.notifications.list(), 6000);
  const items = notifications.data?.items ?? [];

  return (
    <header className="relative z-[1500] flex h-14 items-center justify-between border-b border-slate-200 bg-white px-8">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Search size={16} />
        {/* TODO: TOOL/API CALL HERE - wire global search to GET /orders?q= and GET /vehicles?q= */}
        <input
          placeholder="Search anything..."
          className="w-64 bg-transparent outline-none placeholder:text-slate-400"
        />
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-600">
        {/* TODO: TOOL/API CALL HERE - replace with a real health check (GET /health) */}
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          All systems operational
        </span>

        <div className="relative">
          <button
            onClick={() => setOpen((o) => !o)}
            aria-label={`Notifications${items.length ? ` (${items.length})` : ""}`}
            className="relative rounded-full p-1.5 text-slate-500 hover:bg-slate-100"
          >
            <Bell size={18} />
            {items.length > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-emerald-600 px-1 text-[10px] font-bold text-white">
                {items.length}
              </span>
            )}
          </button>

          {open && (
            <>
              {/* invisible layer behind the menu: a click anywhere else closes it */}
              <button aria-label="Close notifications" className="fixed inset-0 cursor-default" onClick={() => setOpen(false)} />
              <div className="absolute right-0 top-10 max-h-[75vh] w-96 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
                <p className="mb-3 text-sm font-semibold text-slate-900">Notifications</p>
                {items.length === 0 && !newPlan && (
                  <p className="py-4 text-center text-xs text-slate-400">
                    Nothing needs your attention. You will be told here when a vehicle becomes available while orders are unassigned.
                  </p>
                )}
                {items.length > 0 && <VehicleAvailableOffers notes={items} onDone={(plan) => setNewPlan(plan)} />}
                {newPlan && (
                  <Link
                    href={`/route-planning?plan=${newPlan.id}`}
                    onClick={() => setOpen(false)}
                    className="mt-3 block rounded-lg border border-blue-200 px-3 py-2 text-center text-xs font-semibold text-blue-700 hover:bg-blue-50"
                  >
                    View the new plan (v{newPlan.version}) →
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
