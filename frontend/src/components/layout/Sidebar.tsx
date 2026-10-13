"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Truck,
  Package,
  Route,
  Sparkles,
  MapPin,
  BarChart3,
  LifeBuoy,
} from "lucide-react";

// Navigation items, in the same order as the design mockups.
const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/vehicles", label: "Vehicles", icon: Truck },
  { href: "/deliveries", label: "Deliveries", icon: Package },
  { href: "/route-planning", label: "Route Planning", icon: Route },
  { href: "/optimization", label: "Optimization", icon: Sparkles },
  { href: "/live-tracking", label: "Live Tracking", icon: MapPin, live: true },
  { href: "/reports", label: "Reports", icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();

  // "/" must match exactly; other items match any nested path.
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
      <h1 className="px-2 py-3 text-lg font-bold leading-tight text-slate-900">
        AI-Powered
        <br />
        Transport Planner
      </h1>

      <nav className="mt-4 flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon, live }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
              isActive(href)
                ? "bg-blue-50 text-blue-600"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Icon size={16} />
            <span className="flex-1">{label}</span>
            {/* Green dot = live data indicator (Live Tracking only) */}
            {live && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
          </Link>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-4">
        <div className="rounded-xl bg-blue-50 p-4">
          <LifeBuoy size={16} className="text-blue-600" />
          <p className="mt-2 text-sm font-semibold">Need help?</p>
          <p className="mt-1 text-xs text-slate-500">
            Visit our support center for guides and answers.
          </p>
          <a href="#" className="mt-2 inline-block text-xs font-semibold text-blue-600">
            Get support
          </a>
        </div>

        {/* TODO: TOOL/API CALL HERE - replace with the logged-in user once auth exists. */}
        <div className="flex items-center gap-2 px-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-bold">
            AH
          </div>
          <div className="text-xs">
            <p className="font-semibold">Alex Harrison</p>
            <p className="text-slate-500">Operations Manager</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
