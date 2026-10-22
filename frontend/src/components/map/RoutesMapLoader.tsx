"use client";

import dynamic from "next/dynamic";

const RoutesMapLoader = dynamic(() => import("./RoutesMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-100 text-xs text-slate-400">Loading map...</div>
  ),
});

export default RoutesMapLoader;
