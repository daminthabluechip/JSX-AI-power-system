// Typed client for the Flask API. Every backend call in the app goes through this file.
// The base URL comes from NEXT_PUBLIC_API_URL (see frontend/.env.local.example).

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5000";

// ---------- types (mirror the JSON the backend returns) ----------

export type LatLng = [number, number]; // [latitude, longitude]

// Kinds of vehicle; an order can require one of them (e.g. medicine needs "refrigerated").
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
  required_vehicle_type: VehicleType | null; // null = any vehicle may deliver it
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
};

export type PlanStop = {
  sequence: number;
  order_id: number;
  customer: string;
  address: string;
  latitude: number;
  longitude: number;
  priority: Priority;
  window_start: string | null; // the customer's delivery window, "HH:MM"
  window_end: string | null;
  weight_kg: number;
  required_vehicle_type: VehicleType | null;
  planned_arrival: string;
  planned_departure: string;
};

export type PlanRoute = {
  id: number;
  path: LatLng[]; // start point -> stops in order -> depot, for drawing the route
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
  return_time: string | null; // back at the depot
  distance_km: number | null; // driving distance of this vehicle's whole trip
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
  lag_minutes: number; // minutes behind the plan (0 = on time)
  next_stop: { order_id: number; customer: string; eta: string } | null;
  plan_id: number | null;
  path: LatLng[]; // planned route: start -> stops -> depot
};

export type SimulatorStatus = {
  running: boolean;
  speed: number; // simulated minutes per real second
  sim_minute: number;
  sim_time: string; // HH:MM
  delays: Record<string, number>;
};

export type DelayAlert = {
  vehicle_id: number;
  registration: string;
  lag_minutes: number;
  plan_id: number;
  message: string;
  suggested_event: Record<string, unknown>; // body to POST to /events to re-plan
};

export type Report = {
  from: string;
  to: string;
  days: number;
  kpis: {
    on_time_pct: number | null; // share of tracked deliveries that arrived within the customer's window
    measured_deliveries: number;
    late_deliveries: number;
    avg_delay_min: number | null;
    utilization_pct: number | null;
    planned_km: number | null;
    distance_saved_pct: number | null; // vs. the nearest-neighbour baseline
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
  skipped: number; // rows with errors
  errors: { row: number; errors: Record<string, string> }[]; // row numbers like a spreadsheet (header = 1)
};

export type EventType = "delay" | "breakdown" | "rush_order" | "cancellation" | "vehicle_available";

// Something the dispatcher should know about. Today: a vehicle became available that could take
// orders the latest plan had to leave unassigned.
export type AppNotification = {
  type: "vehicle_available";
  plan_id: number; // the plan that has the unassigned orders
  vehicle: { id: number; registration: string; model: string | null; vehicle_type: VehicleType; weight_capacity_kg: number };
  orders: { order_id: number; customer: string; priority: Priority; weight_kg: number }[]; // what it could take
  unassigned_total: number;
  message: string;
  suggested_event: Record<string, unknown>; // body to POST to /events to re-plan with this vehicle
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

// ---------- low-level request ----------

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
    // Network failure: the backend is not running, or CORS blocked the call.
    throw new ApiError(`Cannot reach the API at ${BASE}. Is the Flask server running?`, 0);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // Prefer a human-readable message from the backend (conflicts); field errors stay in `details`.
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

// ---------- endpoints ----------

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
    // date is optional (YYYY-MM-DD); omit to list every day
    list: (date?: string) =>
      request<{ items: Order[]; total: number }>(`/orders?per_page=200${date ? `&date=${date}` : ""}`),
    create: (order: Record<string, unknown>) => post<Order>("/orders", order),
    update: (id: number, changes: Record<string, unknown>) => patch<Order>(`/orders/${id}`, changes),
    remove: (id: number) => del(`/orders/${id}`),
    // Link for the downloadable CSV template (opened directly by the browser).
    templateUrl: `${BASE}/orders/import/template`,
    // Upload a CSV file. The backend answers 400 with the row errors when the file has bad rows
    // (unless skipInvalid), so that response is returned to the caller instead of thrown.
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
      // Whole-file problems (missing columns, empty file, wrong encoding, too large)
      throw new ApiError(body?.details?.file ?? body?.error ?? `Import failed (${res.status})`, res.status);
    },
  },
  plans: {
    // Starts the optimizer in the background; poll get() until status is ready/failed.
    generate: (body: { date: string; vehicle_ids?: number[]; order_ids?: number[]; time_limit_s?: number }) =>
      post<PlanSummary>("/plans/generate", body),
    get: (id: number) => request<Plan>(`/plans/${id}`),
    list: (date?: string) => request<{ items: PlanSummary[] }>(`/plans${date ? `?date=${date}` : ""}`),
    compare: (id: number, otherId: number) => request<PlanComparison>(`/plans/${id}/compare/${otherId}`),
    dispatch: (id: number) => post<PlanSummary>(`/plans/${id}/dispatch`),
  },
  reports: {
    get: (days: number) => request<Report>(`/reports?days=${days}`),
    // Returns the CSV file contents as a Blob, ready to be saved by the browser.
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
    // action: start {time?, speed?} | stop | delay {vehicle_id, minutes} | reset
    simulator: (body: Record<string, unknown>) => post<SimulatorStatus>("/tracking/simulator", body),
  },
  demo: {
    // enabled = this is a shared demo installation (the backend's DEMO_MODE is on)
    status: () => request<{ enabled: boolean }>("/demo"),
    // delete everything and load the sample data again
    reset: () => post<{ reset: boolean }>("/demo/reset"),
  },
  notifications: {
    list: () => request<{ items: AppNotification[] }>("/notifications"),
  },
  events: {
    list: (limit = 20) => request<{ items: DisruptionEvent[] }>(`/events?limit=${limit}`),
    // Applies the disruption and starts a re-plan; returns the new plan to poll.
    report: (body: Record<string, unknown>) =>
      post<{ event: DisruptionEvent; plan: PlanSummary; replaces_plan_id: number }>("/events", body),
  },
};

/** Poll a plan until the optimizer finishes (status ready or failed). */
export async function waitForPlan(id: number, intervalMs = 1000, timeoutMs = 120_000): Promise<Plan> {
  const started = Date.now();
  for (;;) {
    const plan = await api.plans.get(id);
    if (plan.status !== "queued" && plan.status !== "solving") return plan;
    if (Date.now() - started > timeoutMs) throw new ApiError("Planning is taking too long", 0);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

// ---------- display helpers ----------

export const todayISO = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time

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
