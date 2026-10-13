import { Bell, Search } from "lucide-react";

// Top bar: global search on the left, system status + notifications on the right.
export default function Topbar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-8">
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
        <Bell size={18} className="text-slate-500" />
      </div>
    </header>
  );
}
