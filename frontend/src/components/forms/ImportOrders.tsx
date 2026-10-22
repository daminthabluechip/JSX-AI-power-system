"use client";

import { Download, Upload } from "lucide-react";
import { useState } from "react";
import Modal from "@/components/ui/Modal";
import { api, type ImportResult } from "@/lib/api";

export default function ImportOrders({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [skipInvalid, setSkipInvalid] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<(ImportResult & { rejected: boolean }) | null>(null);

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const out = await api.orders.importCsv(file, skipInvalid);
      setResult(out);
      if (out.created > 0) onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  const done = result && !result.rejected;

  return (
    <Modal title="Import deliveries from CSV" onClose={onClose}>
      <div className="space-y-4 text-sm">
        <p className="text-slate-600">
          Required columns: customer, address, latitude, longitude, weight_kg, volume_m3, target_date.
          Optional: priority, earliest_arrival, latest_arrival, required_vehicle_type (truck, van, refrigerated or flatbed).{" "}
          <a href={api.orders.templateUrl} className="inline-flex items-center gap-1 font-semibold text-blue-600">
            <Download size={13} /> Download template
          </a>
        </p>

        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
            setError(null);
          }}
          className="block w-full rounded-lg border border-slate-200 p-2 text-xs file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:font-semibold file:text-blue-600"
        />
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" checked={skipInvalid} onChange={(e) => setSkipInvalid(e.target.checked)} />
          Skip rows with errors and import the rest (otherwise one bad row rejects the whole file)
        </label>

        {error && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}

        {result && (
          <div className={`rounded-lg p-3 text-xs ${done && result.skipped === 0 ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
            <p className="font-semibold">
              {result.rejected
                ? `File rejected: ${result.skipped} row(s) have errors. Nothing was imported.`
                : `Imported ${result.created} deliveries${result.skipped ? `, skipped ${result.skipped} with errors` : ""}.`}
            </p>
            {result.errors.length > 0 && (
              <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
                {result.errors.slice(0, 20).map((e) => (
                  <li key={e.row}>
                    <span className="font-semibold">Row {e.row}:</span>{" "}
                    {Object.entries(e.errors).map(([field, msg]) => `${field} ${msg}`).join("; ")}
                  </li>
                ))}
                {result.errors.length > 20 && <li>...and {result.errors.length - 20} more rows.</li>}
              </ul>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2">{done ? "Close" : "Cancel"}</button>
          <button onClick={run} disabled={!file || busy} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50">
            <Upload size={15} /> {busy ? "Importing..." : "Import"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
