"use client";

import Link from "next/link";
import { useState } from "react";
import { CheckCircle2, Download, Gauge, Route, Sparkles, Timer } from "lucide-react";
import ErrorBox from "@/components/ui/ErrorBox";
import StatCard from "@/components/ui/StatCard";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";

const RANGES = [{ days: 7, label: "Last 7 days" }, { days: 30, label: "Last 30 days" }, { days: 90, label: "Last 90 days" }];
const pct = (v: number | null) => (v == null ? "-" : `${v}%`);
const shortDate = (iso: string) => new Date(iso + "T00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" });

// Reports & Analytics: every figure comes from GET /reports (plans + tracked deliveries).
// A figure with no data behind it shows "-" rather than a made-up number.
export default function ReportsPage() {
  const [days, setDays] = useState(30);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const report = useApi(() => api.reports.get(days), [days]);

  const data = report.data;
  const k = data?.kpis;
  const daily = data?.daily ?? [];
  const maxOrders = Math.max(1, ...daily.map((d) => d.orders));
  const maxKm = Math.max(1, ...daily.map((d) => d.planned_km ?? 0));

  async function exportReport() {
    setExporting(true);
    setExportError(null);
    try {
      const blob = await api.reports.exportCsv(days); // GET /reports/export
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-last-${days}-days.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold">Reports &amp; Analytics</h2>
          <p className="text-sm text-slate-500">Performance insights across your transport operations.</p>
        </div>
        <div className="flex gap-2 text-sm">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
            {RANGES.map((r) => <option key={r.days} value={r.days}>{r.label}</option>)}
          </select>
          <button onClick={exportReport} disabled={exporting || daily.length === 0} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 font-semibold disabled:opacity-50">
            <Download size={15} /> {exporting ? "Exporting..." : "Export report"}
          </button>
        </div>
      </div>

      {report.error && <ErrorBox message={report.error} />}
      {exportError && <ErrorBox message={exportError} />}

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="On-time delivery" value={pct(k?.on_time_pct ?? null)} icon={Timer}
          note={k?.measured_deliveries ? `${k.measured_deliveries - k.late_deliveries} of ${k.measured_deliveries} tracked deliveries` : "no tracked deliveries yet"} />
        <StatCard label="Fleet utilization" value={pct(k?.utilization_pct ?? null)} icon={Gauge} tone="purple" note="average load vs weight capacity" />
        <StatCard label="Planned distance" value={k?.planned_km == null ? "-" : `${Math.round(k.planned_km).toLocaleString()} km`} icon={Route} tone="green"
          note={`${k?.orders ?? 0} orders in range`} />
        <StatCard label="Distance saved" value={pct(k?.distance_saved_pct ?? null)} icon={CheckCircle2} tone="orange" note="vs a nearest-neighbour plan" />
      </div>

      {!report.loading && daily.length === 0 && !report.error && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          There is no data in this range yet. <Link href="/route-planning" className="font-semibold underline">Create and dispatch a plan</Link>, then run the simulator on Live Tracking to see results here.
        </div>
      )}

      {daily.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <section className="col-span-2 rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Delivery performance</h3>
                <p className="text-xs text-slate-500">Orders per day by outcome</p>
              </div>
              <div className="flex gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-blue-600" /> On time</span>
                <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-orange-500" /> Late</span>
                <span className="flex items-center gap-1"><i className="h-2 w-2 rounded-full bg-slate-300" /> Not delivered</span>
              </div>
            </div>
            <div className="mt-4 flex h-48 items-end gap-2">
              {daily.map((d) => {
                const onTime = Math.max(0, d.delivered - d.late);
                const notDone = Math.max(0, d.orders - d.delivered);
                const h = (n: number) => `${(n / maxOrders) * 100}%`;
                return (
                  <div key={d.date} className="flex h-full flex-1 flex-col items-center justify-end gap-1" title={`${d.date}: ${d.delivered}/${d.orders} delivered, ${d.late} late`}>
                    <div className="flex w-full max-w-12 flex-1 flex-col justify-end overflow-hidden rounded-t">
                      <div style={{ height: h(notDone) }} className="bg-slate-300" />
                      <div style={{ height: h(d.late) }} className="bg-orange-500" />
                      <div style={{ height: h(onTime) }} className="bg-blue-600" />
                    </div>
                    <span className="text-xs text-slate-400">{shortDate(d.date)}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="font-semibold">Planned distance</h3>
            <p className="text-xs text-slate-500">Kilometres in each day&apos;s plan</p>
            <div className="mt-4 flex h-48 items-end gap-2">
              {daily.map((d) => (
                <div key={d.date} className="flex h-full flex-1 flex-col items-center justify-end gap-1" title={`${d.date}: ${d.planned_km ?? "no plan"} km`}>
                  <span className="text-[10px] font-semibold">{d.planned_km == null ? "" : Math.round(d.planned_km)}</span>
                  <div className="w-full max-w-12 rounded-t bg-blue-500" style={{ height: `${((d.planned_km ?? 0) / maxKm) * 80}%` }} />
                  <span className="text-xs text-slate-400">{shortDate(d.date)}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* Rule-based insights computed by the backend from the same data */}
      {(data?.insights.length ?? 0) > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-blue-600" />
            <div>
              <h3 className="font-semibold">Performance insights</h3>
              <p className="text-xs text-slate-500">Observations drawn from your fleet data</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4">
            {data!.insights.map((i) => (
              <div key={i.title} className="rounded-lg border border-slate-200 p-4 text-sm">
                <p className="font-semibold">{i.title}</p>
                <p className="mt-1 text-xs text-slate-500">{i.text}</p>
                <Link href={i.link.href} className="mt-3 inline-block text-xs font-semibold text-blue-600">{i.link.label} →</Link>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
