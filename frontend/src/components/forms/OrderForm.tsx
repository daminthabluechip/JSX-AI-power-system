"use client";

import { useState } from "react";
import Modal from "@/components/ui/Modal";
import Field from "./Field";
import {
  api, ApiError, PRIORITY_LABEL, STATUS_LABEL, todayISO, VEHICLE_TYPES, VEHICLE_TYPE_LABEL,
  type Order, type OrderStatus, type Priority,
} from "@/lib/api";

export default function OrderForm({
  order,
  onClose,
  onSaved,
}: {
  order?: Order;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [values, setValues] = useState({
    customer: order?.customer ?? "",
    address: order?.address ?? "",
    latitude: order ? String(order.latitude) : "6.9271",
    longitude: order ? String(order.longitude) : "79.8612",
    weight_kg: order ? String(order.weight_kg) : "",
    volume_m3: order ? String(order.volume_m3) : "",
    priority: order?.priority ?? "medium",
    required_vehicle_type: order?.required_vehicle_type ?? "",
    target_date: order?.target_date ?? todayISO(),
    earliest_arrival: order?.earliest_arrival ?? "08:00",
    latest_arrival: order?.latest_arrival ?? "17:00",
    status: order?.status ?? "pending",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof typeof values) => (v: string) => setValues((s) => ({ ...s, [key]: v }));
  const num = (v: string) => (v === "" ? null : Number(v));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setFormError(null);
    const body = {
      customer: values.customer.trim(),
      address: values.address.trim(),
      latitude: num(values.latitude),
      longitude: num(values.longitude),
      weight_kg: num(values.weight_kg),
      volume_m3: num(values.volume_m3),
      priority: values.priority,
      required_vehicle_type: values.required_vehicle_type || null,
      target_date: values.target_date || null,
      earliest_arrival: values.earliest_arrival || null,
      latest_arrival: values.latest_arrival || null,
      ...(order ? { status: values.status } : {}),
    };
    try {
      if (order) await api.orders.update(order.id, body);
      else await api.orders.create(body);
      onSaved();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.details && typeof err.details === "object") {
        setErrors(err.details as Record<string, string>);
      }
      setFormError(err instanceof Error ? err.message : "Could not save the delivery");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={order ? `Edit order #${order.id}` : "New delivery"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Customer" name="customer" value={values.customer} onChange={set("customer")} error={errors.customer} />
          <Field label="Delivery date" name="target_date" type="date" value={values.target_date} onChange={set("target_date")} error={errors.target_date} />
        </div>
        <Field label="Delivery address" name="address" value={values.address} onChange={set("address")} error={errors.address} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Latitude" name="latitude" type="number" step="any" value={values.latitude} onChange={set("latitude")} error={errors.latitude} />
          <Field label="Longitude" name="longitude" type="number" step="any" value={values.longitude} onChange={set("longitude")} error={errors.longitude} hint="Sri Lanka is about 6-10 N, 79-82 E" />
          <Field label="Weight (kg)" name="weight_kg" type="number" step="any" value={values.weight_kg} onChange={set("weight_kg")} error={errors.weight_kg} />
          <Field label="Volume (m³)" name="volume_m3" type="number" step="any" value={values.volume_m3} onChange={set("volume_m3")} error={errors.volume_m3} />
          <Field label="Earliest arrival" name="earliest_arrival" type="time" value={values.earliest_arrival} onChange={set("earliest_arrival")} error={errors.earliest_arrival} />
          <Field label="Latest arrival" name="latest_arrival" type="time" value={values.latest_arrival} onChange={set("latest_arrival")} error={errors.latest_arrival} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Priority" name="priority" value={values.priority} onChange={set("priority")} error={errors.priority}
            options={(Object.keys(PRIORITY_LABEL) as Priority[]).map((p) => ({ value: p, label: PRIORITY_LABEL[p] }))}
          />
          <Field
            label="Required vehicle type" name="required_vehicle_type" value={values.required_vehicle_type}
            onChange={set("required_vehicle_type")} error={errors.required_vehicle_type}
            options={[{ value: "", label: "Any vehicle" }, ...VEHICLE_TYPES.map((t) => ({ value: t, label: VEHICLE_TYPE_LABEL[t] }))]}
          />
          {order && (
            <Field
              label="Status" name="status" value={values.status} onChange={set("status")} error={errors.status}
              options={(["pending", "scheduled", "in_transit", "delivered", "cancelled"] as OrderStatus[]).map((s) => ({ value: s, label: STATUS_LABEL[s] }))}
            />
          )}
        </div>
        {formError && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{formError}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 px-4 py-2 text-sm">Cancel</button>
          <button disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? "Saving..." : order ? "Save changes" : "Add delivery"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
