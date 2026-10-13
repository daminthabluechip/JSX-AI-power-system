"use client";

import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Field from "./Field";
import { api, ApiError, STATUS_LABEL, VEHICLE_TYPES, VEHICLE_TYPE_LABEL, type Vehicle } from "@/lib/api";

// Add a vehicle (vehicle = undefined) or edit one. Weights are typed in tonnes and sent as kg.
export default function VehicleForm({
  vehicle,
  onClose,
  onSaved,
}: {
  vehicle?: Vehicle;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [values, setValues] = useState({
    registration: vehicle?.registration ?? "",
    model: vehicle?.model ?? "",
    driver: vehicle?.driver ?? "",
    vehicle_type: vehicle?.vehicle_type ?? "truck",
    capacityT: vehicle ? String(vehicle.weight_capacity_kg / 1000) : "",
    volume: vehicle ? String(vehicle.volume_capacity_m3) : "",
    shift_start: vehicle?.shift_start ?? "07:00",
    shift_end: vehicle?.shift_end ?? "19:00",
    status: vehicle?.status ?? "available",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof typeof values) => (v: string) => setValues((s) => ({ ...s, [key]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setFormError(null);
    const body = {
      registration: values.registration.trim(),
      model: values.model.trim() || null,
      driver: values.driver.trim() || null,
      vehicle_type: values.vehicle_type,
      weight_capacity_kg: values.capacityT === "" ? null : Number(values.capacityT) * 1000,
      volume_capacity_m3: values.volume === "" ? null : Number(values.volume),
      shift_start: values.shift_start || null,
      shift_end: values.shift_end || null,
      status: values.status,
    };
    try {
      // POST /vehicles to create, PATCH /vehicles/{id} to edit
      if (vehicle) await api.vehicles.update(vehicle.id, body);
      else await api.vehicles.create(body);
      onSaved();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details && typeof err.details === "object") {
        // The backend names the field that failed; show each message under its input.
        const map: Record<string, string> = {};
        const rename: Record<string, string> = { weight_capacity_kg: "capacityT", volume_capacity_m3: "volume" };
        Object.entries(err.details as Record<string, string>).forEach(([k, m]) => (map[rename[k] ?? k] = m));
        setErrors(map);
      }
      setFormError(err instanceof Error ? err.message : "Could not save the vehicle");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={vehicle ? `Edit ${vehicle.registration}` : "Add vehicle"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Registration" name="registration" value={values.registration} onChange={set("registration")} error={errors.registration} hint="e.g. VH-2048" />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Model" name="model" value={values.model} onChange={set("model")} error={errors.model} />
          <Field label="Driver" name="driver" value={values.driver} onChange={set("driver")} error={errors.driver} />
          <Field label="Weight capacity (tonnes)" name="capacityT" type="number" step="0.1" value={values.capacityT} onChange={set("capacityT")} error={errors.capacityT} />
          <Field label="Volume capacity (m³)" name="volume" type="number" step="0.1" value={values.volume} onChange={set("volume")} error={errors.volume} />
          <Field label="Shift start" name="shift_start" type="time" value={values.shift_start} onChange={set("shift_start")} error={errors.shift_start} />
          <Field label="Shift end" name="shift_end" type="time" value={values.shift_end} onChange={set("shift_end")} error={errors.shift_end} />
        </div>
        <Field
          label="Vehicle type" name="vehicle_type" value={values.vehicle_type} onChange={set("vehicle_type")} error={errors.vehicle_type}
          options={VEHICLE_TYPES.map((t) => ({ value: t, label: VEHICLE_TYPE_LABEL[t] }))}
          hint="Orders can require a type, e.g. medicine needs a refrigerated vehicle"
        />
        <Field
          label="Status" name="status" value={values.status} onChange={set("status")} error={errors.status}
          options={(["available", "on_route", "maintenance"] as const).map((s) => ({ value: s, label: STATUS_LABEL[s] }))}
        />
        {formError && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{formError}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm">Cancel</button>
          <button disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? "Saving..." : vehicle ? "Save changes" : "Add vehicle"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
