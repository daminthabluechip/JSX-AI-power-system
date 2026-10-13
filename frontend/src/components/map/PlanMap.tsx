"use client";

import { useState } from "react";
import RoutesMapLoader from "./RoutesMapLoader";
import { routeColor } from "./routeColors";
import type { Plan } from "@/lib/api";

// A plan's routes on a map with a legend. Click a vehicle in the legend to hide or show its route.
export default function PlanMap({ plan, heightClass = "h-[420px]" }: { plan: Plan; heightClass?: string }) {
  const [hidden, setHidden] = useState<number[]>([]);
  const toggle = (id: number) => setHidden((h) => (h.includes(id) ? h.filter((x) => x !== id) : [...h, id]));

  return (
    <div className="space-y-2">
      <div className={`overflow-hidden rounded-xl border border-slate-200 ${heightClass}`}>
        <RoutesMapLoader routes={plan.routes} depot={plan.depot} hiddenVehicleIds={hidden} />
      </div>
      <ul className="flex flex-wrap gap-2 text-xs">
        {plan.routes.map((r, i) => {
          const off = hidden.includes(r.vehicle.id);
          return (
            <li key={r.id}>
              <button
                onClick={() => toggle(r.vehicle.id)}
                title={off ? "Show this route" : "Hide this route"}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${off ? "border-slate-200 text-slate-400" : "border-slate-300 text-slate-700"}`}
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: off ? "#cbd5e1" : routeColor(i) }} />
                {r.vehicle.registration} · {r.stops.length} stops
              </button>
            </li>
          );
        })}
        <li className="flex items-center gap-1.5 px-1 text-slate-500">
          <span className="flex h-4 w-4 items-center justify-center rounded-sm bg-slate-900 text-[9px] font-bold text-white">D</span> depot
        </li>
      </ul>
    </div>
  );
}
