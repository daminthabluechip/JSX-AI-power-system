"use client";

import dynamic from "next/dynamic";

const FleetMapLoader = dynamic(() => import("./FleetMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-100 text-xs text-slate-400">
      Loading map...
    </div>
  ),
});

export default FleetMapLoader;
