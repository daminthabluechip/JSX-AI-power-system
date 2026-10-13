"use client";

import { useState } from "react";
import Modal from "./Modal";

// "Are you sure?" dialog. onConfirm may throw: the message is shown inside the dialog
// (e.g. the backend refuses to delete a vehicle that plans refer to).
export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onClose,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      <p className="text-sm text-slate-600">{message}</p>
      {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <button onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm">Cancel</button>
        <button onClick={run} disabled={busy} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
          {busy ? "Working..." : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
