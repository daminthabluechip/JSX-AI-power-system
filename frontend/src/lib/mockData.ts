// Temporary mock data copied from the UI mockups.
// TODO: TOOL/API CALL HERE - delete this file once the Flask API exists and
// replace each export with a fetch in src/lib/api.ts (e.g. GET /vehicles, GET /orders).

export const dashboardStats = {
  totalVehicles: 48,
  activeDeliveries: 27,
  completedToday: 64,
  fleetUtilization: 86,
};

// Fleet utilization per weekday (percent) - bar chart on the Dashboard.
export const weeklyUtilization = [
  { day: "Mon", value: 65 },
  { day: "Tue", value: 75 },
  { day: "Wed", value: 70 },
  { day: "Thu", value: 85 },
  { day: "Fri", value: 78 },
  { day: "Sat", value: 50 },
  { day: "Sun", value: 42 },
];

export type DeliveryStatus = "In Transit" | "Scheduled" | "Delivered";

export const activeDeliveries: {
  customer: string;
  location: string;
  eta: string;
  status: DeliveryStatus;
}[] = [
  { customer: "DASUN", location: "Kandy, Alawathugoda", eta: "10:30 AM", status: "In Transit" },
  { customer: "FOOD", location: "44 Colombo 10", eta: "11:15 AM", status: "Scheduled" },
  { customer: "MEDICAL", location: "870 Kurunagala", eta: "9:45 AM", status: "Delivered" },
  { customer: "Hardware", location: "201 Main Street, Galle", eta: "12:20 PM", status: "In Transit" },
];

export const recentActivity = [
  { title: "Delivery completed", detail: "VH-3091 delivered to Summit Medical", time: "6 min ago" },
  { title: "Vehicle departed", detail: "VH-2048 left the Central Depot", time: "24 min ago" },
  { title: "Delay detected", detail: "Traffic delay on route RT-142", time: "42 min ago" },
  { title: "Route optimized", detail: "4 stops reordered, saving 24 mins", time: "1 hr ago" },
];

// ---------- Vehicles page ----------
export type VehicleStatus = "On Route" | "Available" | "Maintenance";

export const vehicleSummary = { all: 48, available: 19, onRoute: 25, maintenance: 4 };

export const vehicles: {
  id: string;
  model: string;
  driver: string;
  status: VehicleStatus;
  loadTons: number;
  capacityTons: number;
  location: string;
}[] = [
  { id: "VH-2048", model: "Volvo FH16", driver: "a", status: "On Route", loadTons: 18, capacityTons: 22, location: "A" },
  { id: "VH-1042", model: "Mercedes Actros", driver: "b", status: "Available", loadTons: 8, capacityTons: 18, location: "B" },
  { id: "VH-3091", model: "DAF XF", driver: "c", status: "On Route", loadTons: 13, capacityTons: 20, location: "C" },
  { id: "VH-2275", model: "Scania R500", driver: "d", status: "Maintenance", loadTons: 0, capacityTons: 24, location: "D" },
  { id: "VH-1189", model: "MAN TGX", driver: "e", status: "Available", loadTons: 4, capacityTons: 18, location: "E" },
];

// ---------- Deliveries page ----------
export type Priority = "Critical" | "High" | "Medium" | "Low";

export const orders: {
  id: number;
  customer: string;
  location: string;
  eta: string;
  priority: Priority;
  status: DeliveryStatus;
}[] = [
  { id: 1, customer: "DASUN", location: "KANDY, ALAWATHUGODA", eta: "10:30 AM", priority: "High", status: "In Transit" },
  { id: 2, customer: "FOOD", location: "44 COLOMBO 10", eta: "11:15 AM", priority: "Medium", status: "Scheduled" },
  { id: 3, customer: "MEDICAL", location: "870 KURUNAGALA", eta: "9:45 AM", priority: "Critical", status: "Delivered" },
  { id: 4, customer: "Hardware", location: "201 MAIN STREET, GALLE", eta: "12:20 PM", priority: "Medium", status: "In Transit" },
  { id: 5, customer: "DESHAN", location: "67 AREA AMPARA", eta: "1:00 PM", priority: "Low", status: "Scheduled" },
];

// ---------- Route Planning page ----------
export const planVehicles: {
  id: string;
  loadTons: number;
  capacityTons: number;
  status: "On Route" | "Available";
}[] = [
  { id: "VH 2048", loadTons: 18, capacityTons: 22, status: "On Route" },
  { id: "VH 1042", loadTons: 8, capacityTons: 18, status: "Available" },
  { id: "VH 3091", loadTons: 13, capacityTons: 20, status: "On Route" },
  { id: "VH 1189", loadTons: 4, capacityTons: 18, status: "Available" },
];

export const planDeliveries: {
  id: number;
  customer: string;
  due: string;
  priority: Priority;
  weightTons: number;
}[] = [
  { id: 1, customer: "DASUN", due: "10:30 AM", priority: "High", weightTons: 5.2 },
  { id: 2, customer: "FOOD", due: "11:15 AM", priority: "Medium", weightTons: 4.6 },
  { id: 3, customer: "Hardware", due: "12:20 PM", priority: "Medium", weightTons: 4.8 },
  { id: 4, customer: "DESHAN", due: "1:00 PM", priority: "Low", weightTons: 2.1 },
];

// ---------- Optimization page ----------
export type DisruptionKind = "traffic" | "breakdown" | "urgent" | "cancelled";

export const disruptions: { kind: DisruptionKind; title: string; detail: string }[] = [
  { kind: "traffic", title: "Heavy traffic & delays", detail: "18 min delay on the East Corridor" },
  { kind: "breakdown", title: "Vehicle breakdown", detail: "VH-2275 requires reassignment" },
  { kind: "urgent", title: "New urgent delivery", detail: "Summit Medical - Critical priority" },
  { kind: "cancelled", title: "Cancellation / unavailable", detail: "Harbor Foods order placed on hold" },
];

// Current (manual) vs optimized (AI) route for the same vehicle.
export const routeComparison = {
  current: {
    sequence: ["Colombo", "Kandy", "Kurunegala", "Negombo"],
    distanceKm: 120,
    time: "3h 45m",
    deliveries: 4,
    delayed: 2,
    vehicle: "VH-2048 · Volvo FH16",
  },
  optimized: {
    sequence: ["Colombo", "Negombo", "Kurunegala", "Kandy"],
    distanceKm: 95,
    time: "2h 50m",
    deliveries: 4,
    delayed: 0,
    vehicle: "VH-2048 · Volvo FH16",
  },
};

export const optimizationImpact = [
  { label: "Distance saved", value: "25 km" },
  { label: "Time saved", value: "55 minutes" },
  { label: "Fuel saving estimate", value: "12%" },
  { label: "Delay reduction", value: "2 delays avoided" },
];

export const optimizationActivity = [
  { title: "Route R7-148 recalculated", detail: "Traffic delay avoided · 14 minutes saved", time: "3 min ago" },
  { title: "Delivery reassigned to VH-1189", detail: "Capacity balanced across the active fleet", time: "32 min ago" },
  { title: "Morning plan optimized", detail: "All deliveries sequenced across 12 vehicles", time: "2 hr ago" },
];

// ---------- Live Tracking page ----------
export type LatLng = [number, number];

export const trackedVehicles: {
  id: string;
  driver: string;
  nextStop: string;
  eta: string;
  speedKmh: number;
  status: "active" | "idle";
  position: LatLng; // current GPS position (simulated)
  path: LatLng[]; // planned route polyline
}[] = [
  {
    id: "VH-2048", driver: "a", nextStop: "DASUN", eta: "10:30 AM", speedKmh: 62, status: "active",
    position: [7.2008, 79.8737],
    path: [[6.9271, 79.8612], [7.2008, 79.8737], [7.4863, 80.3647], [7.2906, 80.6337]],
  },
  {
    id: "VH-3091", driver: "c", nextStop: "MEDICAL", eta: "11:05 AM", speedKmh: 48, status: "active",
    position: [7.4863, 80.3647],
    path: [[7.4863, 80.3647], [7.2906, 80.6337]],
  },
  {
    id: "VH-1189", driver: "e", nextStop: "Hardware", eta: "1:20 PM", speedKmh: 0, status: "active",
    position: [6.9271, 79.8612],
    path: [[6.9271, 79.8612], [7.2008, 79.8737]],
  },
  {
    id: "VH-2275", driver: "d", nextStop: "-", eta: "-", speedKmh: 0, status: "idle",
    position: [6.0535, 80.221],
    path: [],
  },
];

// ---------- Reports page ----------
export const reportStats = [
  { label: "On-time delivery", value: "94.8%", note: "+2.4% vs previous period" },
  { label: "Fleet utilization", value: "86.2%", note: "+4.1% vs previous period" },
  { label: "Distance traveled", value: "24,860 km", note: "+3.8% vs previous period" },
  { label: "Average delivery time", value: "42 min", note: "-6.2% vs previous period" },
];

// Completed deliveries per point across 4 weeks (line chart).
export const deliveryTrend = [30, 28, 34, 33, 40, 38, 45, 44, 50, 52, 60, 66];

// Daily distance in km (bar chart).
export const dailyDistance = [60, 78, 66, 85, 70, 82, 62, 80, 88, 76, 90, 92];

export const aiInsights = [
  { title: "Route efficiency improved", text: "Optimized routes reduced total distance by 6.4% this month.", link: "View route analysis" },
  { title: "Peak delivery window", text: "82% of morning deliveries arrived on time versus 67% in the afternoon.", link: "View time analysis" },
  { title: "Capacity opportunity", text: "Consolidating mid-district loads could increase utilization by 8%.", link: "View recommendations" },
];
