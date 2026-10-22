const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5000";

export type LatLng = [number, number];

export const VEHICLE_TYPES = ["truck", "van", "refrigerated", "flatbed"] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];
export const VEHICLE_TYPE_LABEL: Record<VehicleType, string> = {
  truck: "Truck", van: "Van", refrigerated: "Refrigerated", flatbed: "Flatbed",
};

export type VehicleStatus = "available" | "on_route" | "maintenance";
export type OrderStatus = "pending" | "scheduled" | "in_transit" | "delivered" | "cancelled";
export type Priority = "critical" | "high" | "medium" | "low";

export type Vehicle = {
  id: number;
  registration: string;
  model: string | null;
  vehicle_type: VehicleType;
  driver: string | null;
  weight_capacity_kg: number;
  volume_capacity_m3: number;
  shift_start: string | null;
  shift_end: string | null;
  status: VehicleStatus;
};

export type Order = {
  id: number;
  customer: string;
  address: string;
  latitude: number;
  longitude: number;
  weight_kg: number;
  volume_m3: number;
  priority: Priority;
  target_date: string;
  earliest_arrival: string | null;
  latest_arrival: string | null;
  required_vehicle_type: VehicleType | null;
  status: OrderStatus;
};

export type PlanSummary = {
  id: number;
  planning_date: string;
  version: number;
  status: "queued" | "solving" | "ready" | "failed" | "dispatched";
  error: string | null;
  total_distance_km: number | null;
  total_time_min: number | null;
  solve_time_s: number | null;
  baseline_distance_km: number | null;
  distance_saved_pct: number | null;
  served: number;
  baseline_served: number | null;
  distance_saved_per_order_pct: number | null;
};

export type PlanStop = {
  sequence: number;
  order_id: number;
  customer: string;
  address: string;
  latitude: number;
  longitude: number;
  priority: Priority;
  window_start: string | null;
  window_end: string | null;
  weight_kg: number;
  required_vehicle_type: VehicleType | null;
  planned_arrival: string;
  planned_departure: string;
};

export type PlanRoute = {
  id: number;
  path: LatLng[];
  vehicle: {
    id: number;
    registration: string;
    model: string | null;
    driver: string | null;
    vehicle_type: VehicleType;
    weight_capacity_kg: number;
    volume_capacity_m3: number;
  };
  planned_departure: string;
  return_time: string | null;
  distance_km: number | null;
  load_kg: number;
  volume_m3: number;
  weight_utilization_pct: number;
  volume_utilization_pct: number;
  stops: PlanStop[];
};

export type Plan = PlanSummary & {
  depot: { name: string; latitude: number; longitude: number } | null;
  routes: PlanRoute[];
  unassigned: { order_id: number; customer: string; priority: Priority; reason: string }[];
};

export type PlanChange = {
  order_id: number;
  customer: string | null;
  change: "rescheduled" | "reassigned" | "dropped" | "completed" | "removed" | "now_assigned" | "added";
  before: { vehicle: string; sequence: number; arrival: string } | null;
  after: { vehicle: string; sequence: number; arrival: string } | null;
};

export type PlanComparison = {
  before: PlanSummary;
  after: PlanSummary;
  distance_delta_km: number | null;
  time_delta_min: number | null;
  vehicles_used: { before: number; after: number };
  unassigned: { before: number; after: number };
  unchanged_orders: number;
  changes: PlanChange[];
};

export type TrackedVehicle = {
  vehicle_id: number;
  registration: string;
  driver: string | null;
  active: boolean;
  state: "waiting" | "driving" | "at_stop" | "stopped" | "finished" | "idle";
  latitude: number;
  longitude: number;
  speed_kmh: number;
  recorded_at: string | null;
  lag_minutes: number;
  next_stop: { order_id: number; customer: string; eta: string } | null;
  plan_id: number | null;
  path: LatLng[];
};

export type SimulatorStatus = {
  running: boolean;
  speed: number;
  sim_minute: number;
  sim_time: string;
  delays: Record<string, number>;
};

export type DelayAlert = {
  vehicle_id: number;
  registration: string;
  lag_minutes: number;
  plan_id: number;
  message: string;
  suggested_event: Record<string, unknown>;
};

export type Report = {
  from: string;
  to: string;
  days: number;
  kpis: {
    on_time_pct: number | null;
    measured_deliveries: number;
    late_deliveries: number;
    avg_delay_min: number | null;
    utilization_pct: number | null;
    planned_km: number | null;
    distance_saved_pct: number | null;
    delivered: number;
    orders: number;
  };
  daily: {
    date: string;
    orders: number;
    delivered: number;
    late: number;
    on_time_pct: number | null;
    planned_km: number | null;
    utilization_pct: number | null;
  }[];
  insights: { title: string; text: string; link: { label: string; href: string } }[];
};

export type ImportResult = {
  created: number;
  skipped: number;
  errors: { row: number; errors: Record<string, string> }[];
};

export type EventType = "delay" | "breakdown" | "rush_order" | "cancellation" | "vehicle_available";

export type AppNotification = {
  type: "vehicle_available";
  plan_id: number;
  vehicle: { id: number; registration: string; model: string | null; vehicle_type: VehicleType; weight_capacity_kg: number };
  orders: { order_id: number; customer: string; priority: Priority; weight_kg: number }[];
  unassigned_total: number;
  message: string;
  suggested_event: Record<string, unknown>;
};

export type DisruptionEvent = {
  id: number;
  type: EventType;
  vehicle_id: number | null;
  order_id: number | null;
  delay_minutes: number | null;
  occurred_at: string | null;
  handled_by_plan_id: number | null;
};

export class ApiError extends Error {
  constructor(message: string, public status: number, public details?: unknown) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Cannot reach the API at ${BASE}. Is the Flask server running?`, 0);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const message =
      body?.details?.message ??
      (body?.error === "validation_failed" ? "Please fix the highlighted fields" : body?.error) ??
      `Request failed (${res.status})`;
    throw new ApiError(message, res.status, body?.details);
  }
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
const patch = <T>(path: string, data: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(data) });
const del = (path: string) => request<void>(path, { method: "DELETE" });

export const api = {
  vehicles: {
    list: () => request<{ items: Vehicle[]; total: number }>("/vehicles?per_page=200"),
    summary: () =>
      request<{ all: number; available: number; on_route: number; maintenance: number }>("/vehicles/summary"),
    create: (vehicle: Record<string, unknown>) => post<Vehicle>("/vehicles", vehicle),
    update: (id: number, changes: Record<string, unknown>) => patch<Vehicle>(`/vehicles/${id}`, changes),
    remove: (id: number) => del(`/vehicles/${id}`),
  },
  orders: {
    list: (date?: string) =>
      request<{ items: Order[]; total: number }>(`/orders?per_page=200${date ? `&date=${date}` : ""}`),
    create: (order: Record<string, unknown>) => post<Order>("/orders", order),
    update: (id: number, changes: Record<string, unknown>) => patch<Order>(`/orders/${id}`, changes),
    remove: (id: number) => del(`/orders/${id}`),
    templateUrl: `${BASE}/orders/import/template`,
    importCsv: async (file: File, skipInvalid: boolean): Promise<ImportResult & { rejected: boolean }> => {
      let res: Response;
      try {
        res = await fetch(`${BASE}/orders/import?skip_invalid=${skipInvalid}`, {
          method: "POST",
          headers: { "Content-Type": "text/csv" },
          body: file,
        });
      } catch {
        throw new ApiError(`Cannot reach the API at ${BASE}. Is the Flask server running?`, 0);
      }
      const body = await res.json().catch(() => null);
      if (res.ok || (res.status === 400 && Array.isArray(body?.errors))) {
        return { created: body.created, skipped: body.skipped, errors: body.errors, rejected: !res.ok };
      }
      throw new ApiError(body?.details?.file ?? body?.error ?? `Import failed (${res.status})`, res.status);
    },
  },
  plans: {
    generate: (body: { date: string; vehicle_ids?: number[]; order_ids?: number[]; time_limit_s?: number }) =>
      post<PlanSummary>("/plans/generate", body),
    get: (id: number) => request<Plan>(`/plans/${id}`),
    list: (date?: string) => request<{ items: PlanSummary[] }>(`/plans${date ? `?date=${date}` : ""}`),
    compare: (id: number, otherId: number) => request<PlanComparison>(`/plans/${id}/compare/${otherId}`),
    dispatch: (id: number) => post<PlanSummary>(`/plans/${id}/dispatch`),
  },
  reports: {
    get: (days: number) => request<Report>(`/reports?days=${days}`),
    exportCsv: async (days: number) => {
      const res = await fetch(`${BASE}/reports/export?days=${days}`, { cache: "no-store" });
      if (!res.ok) throw new ApiError(`Export failed (${res.status})`, res.status);
      return res.blob();
    },
  },
  tracking: {
    positions: () =>
      request<{ plan_id: number | null; items: TrackedVehicle[]; simulator: SimulatorStatus }>("/tracking/positions"),
    alerts: () => request<{ items: DelayAlert[] }>("/tracking/alerts"),
    simulator: (body: Record<string, unknown>) => post<SimulatorStatus>("/tracking/simulator", body),
  },
  demo: {
    status: () => request<{ enabled: boolean }>("/demo"),
    reset: () => post<{ reset: boolean }>("/demo/reset"),
  },
  notifications: {
    list: () => request<{ items: AppNotification[] }>("/notifications"),
  },
  events: {
    list: (limit = 20) => request<{ items: DisruptionEvent[] }>(`/events?limit=${limit}`),
    report: (body: Record<string, unknown>) =>
      post<{ event: DisruptionEvent; plan: PlanSummary; replaces_plan_id: number }>("/events", body),
  },
};

export async function waitForPlan(id: number, intervalMs = 1000, timeoutMs = 120_000): Promise<Plan> {
  const started = Date.now();
  for (;;) {
    const plan = await api.plans.get(id);
    if (plan.status !== "queued" && plan.status !== "solving") return plan;
    if (Date.now() - started > timeoutMs) throw new ApiError("Planning is taking too long", 0);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export const todayISO = () => new Date().toLocaleDateString("en-CA");

export const STATUS_LABEL: Record<string, string> = {
  available: "Available",
  on_route: "On Route",
  maintenance: "Maintenance",
  pending: "Pending",
  scheduled: "Scheduled",
  in_transit: "In Transit",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export const PRIORITY_LABEL: Record<Priority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const formatDuration = (minutes: number | null) =>
  minutes == null ? "-" : `${Math.floor(minutes / 60)}h ${String(Math.round(minutes % 60)).padStart(2, "0")}m`;
