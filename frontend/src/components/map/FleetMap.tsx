"use client";

import { MapContainer, TileLayer, Marker, Polyline, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLng } from "@/lib/mockData";

export type MapVehicle = {
  id: string;
  position: LatLng;
  path: LatLng[];
};

type Props = {
  vehicles: MapVehicle[];
  selectedId?: string;
  onSelect?: (id: string) => void;
  className?: string;
};

// Build a round blue/green marker with CSS instead of Leaflet's default image icon
// (the default PNGs break under bundlers).
const dot = (selected: boolean) =>
  L.divIcon({
    className: "",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: `<div style="width:22px;height:22px;border-radius:50%;border:3px solid white;
      box-shadow:0 1px 4px rgba(0,0,0,.4);background:${selected ? "#2563eb" : "#16a34a"}"></div>`,
  });

// Reusable Leaflet map showing vehicle markers and their planned routes.
// Must run in the browser only, so import it through FleetMapLoader (ssr: false).
export default function FleetMap({ vehicles, selectedId, onSelect, className }: Props) {
  // Centre on Colombo-Kandy corridor (Sri Lanka) by default.
  const center: LatLng = [7.2, 80.1];

  return (
    <MapContainer center={center} zoom={9} scrollWheelZoom className={className ?? "h-full w-full"}>
      {/* TODO: TOOL/API CALL HERE - OpenStreetMap tiles are fine for development; check the OSM
          tile usage policy (or use a tile provider key) before any production deployment. */}
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {vehicles.map((v) => (
        <div key={v.id}>
          {/* Planned route as a dashed blue line */}
          {v.path.length > 1 && (
            <Polyline positions={v.path} pathOptions={{ color: "#2563eb", dashArray: "6 8", weight: 3 }} />
          )}
          <Marker
            position={v.position}
            icon={dot(v.id === selectedId)}
            eventHandlers={{ click: () => onSelect?.(v.id) }}
          >
            <Tooltip>{v.id}</Tooltip>
          </Marker>
        </div>
      ))}
    </MapContainer>
  );
}
