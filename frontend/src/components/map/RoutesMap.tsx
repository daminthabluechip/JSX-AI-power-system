"use client";

import { useEffect } from "react";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLng, PlanRoute } from "@/lib/api";
import { routeColor } from "./routeColors";

type Props = {
  routes: PlanRoute[];
  depot: { name: string; latitude: number; longitude: number } | null;
  hiddenVehicleIds?: number[]; // routes switched off in the legend
  className?: string;
};

// A numbered circle for a stop, in the colour of its route.
const stopIcon = (n: number, color: string) =>
  L.divIcon({
    className: "",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: `<div style="width:22px;height:22px;border-radius:50%;background:${color};color:#fff;border:2px solid #fff;
      box-shadow:0 1px 3px rgba(0,0,0,.4);font:600 11px sans-serif;display:flex;align-items:center;justify-content:center">${n}</div>`,
  });

const depotIcon = L.divIcon({
  className: "",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  html: `<div style="width:24px;height:24px;background:#0f172a;color:#fff;border:2px solid #fff;border-radius:4px;
    box-shadow:0 1px 3px rgba(0,0,0,.5);font:700 12px sans-serif;display:flex;align-items:center;justify-content:center">D</div>`,
});

// Zoom the map to fit every visible point whenever the routes change.
function FitToRoutes({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) map.fitBounds(points, { padding: [30, 30] });
  }, [map, points]);
  return null;
}

// Shows every route of a plan: coloured line per vehicle, numbered stops, depot marker.
// Browser-only (Leaflet), so pages import it through RoutesMapLoader.
export default function RoutesMap({ routes, depot, hiddenVehicleIds = [], className }: Props) {
  const visible = routes.map((r, i) => ({ route: r, color: routeColor(i) })).filter(({ route }) => !hiddenVehicleIds.includes(route.vehicle.id));
  const points: LatLng[] = visible.flatMap(({ route }) => route.path);
  if (depot) points.push([depot.latitude, depot.longitude]);

  return (
    <MapContainer center={[7.2, 80.1]} zoom={9} scrollWheelZoom className={className ?? "h-full w-full"}>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitToRoutes points={points} />

      {visible.map(({ route, color }) => (
        <div key={route.id}>
          <Polyline positions={route.path} pathOptions={{ color, weight: 4, opacity: 0.8 }} />
          {route.stops.map((s) => (
            <Marker key={s.order_id} position={[s.latitude, s.longitude]} icon={stopIcon(s.sequence, color)}>
              <Tooltip>
                {route.vehicle.registration} · stop {s.sequence}: {s.customer} · arrives {s.planned_arrival}
              </Tooltip>
            </Marker>
          ))}
        </div>
      ))}

      {depot && (
        <Marker position={[depot.latitude, depot.longitude]} icon={depotIcon} zIndexOffset={1000}>
          <Tooltip>{depot.name}</Tooltip>
        </Marker>
      )}
    </MapContainer>
  );
}
