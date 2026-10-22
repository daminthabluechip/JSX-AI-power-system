import { formatDuration, PRIORITY_LABEL, VEHICLE_TYPE_LABEL, type PlanRoute } from "@/lib/api";

const toMin = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5));
const tonnes = (kg: number) => `${(kg / 1000).toFixed(1)} t`;
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export default function RouteExplanation({ route, defaultOpen = false }: { route: PlanRoute; defaultOpen?: boolean }) {
  const { vehicle, stops } = route;
  const typeName = VEHICLE_TYPE_LABEL[vehicle.vehicle_type].toLowerCase();

  const tripMinutes = route.return_time ? toMin(route.return_time) - toMin(route.planned_departure) : null;

  const slacks = stops
    .filter((s) => s.window_end)
    .map((s) => ({ stop: s, spare: toMin(s.window_end!) - toMin(s.planned_arrival) }));
  const tightest = slacks.length ? slacks.reduce((a, b) => (b.spare < a.spare ? b : a)) : null;

  const needType = stops.filter((s) => s.required_vehicle_type);
  const urgent = stops.filter((s) => s.priority === "critical" || s.priority === "high");

  return (
    <details open={defaultOpen} className="group mt-4 rounded-lg border border-blue-100 bg-blue-50/40 text-xs">
      <summary className="cursor-pointer select-none px-3 py-2 font-semibold text-blue-700">
        How was this route planned?
      </summary>

      <div className="space-y-4 border-t border-blue-100 p-3 text-slate-700">
        <p className="leading-relaxed">
          <span className="font-semibold">{vehicle.registration}</span> ({vehicle.model ?? "vehicle"}, {typeName}) leaves
          the depot at <b>{route.planned_departure}</b> and delivers to <b>{plural(stops.length, "customer")}</b> in the
          order below
          {route.return_time ? (
            <>
              , then drives back and is home around <b>{route.return_time}</b>
            </>
          ) : null}
          .
          {route.distance_km != null && (
            <>
              {" "}The whole trip is about <b>{route.distance_km} km</b>
              {tripMinutes != null && <> and takes <b>{formatDuration(tripMinutes)}</b> including unloading</>}.
            </>
          )}
        </p>

        <div>
          <p className="mb-2 font-semibold text-slate-900">Step by step</p>
          <ol className="space-y-2 border-l-2 border-blue-200 pl-3">
            <li>
              <span className="font-semibold">{route.planned_departure}</span> Leave the depot.
            </li>
            {stops.map((s, i) => {
              const previousLeft = i === 0 ? route.planned_departure : stops[i - 1].planned_departure;
              const travel = toMin(s.planned_arrival) - toMin(previousLeft);
              const spare = s.window_end ? toMin(s.window_end) - toMin(s.planned_arrival) : null;
              return (
                <li key={s.order_id}>
                  <span className="font-semibold">{s.planned_arrival}</span> Stop {s.sequence}: <b>{s.customer}</b>
                  <span className="text-slate-500"> ({s.address})</span>
                  <div className="mt-0.5 text-slate-500">
                    {travel >= 60 ? formatDuration(travel) : `${travel} min`} after {i === 0 ? "leaving the depot" : "leaving the previous stop"}. Delivers {tonnes(s.weight_kg)}
                    {s.planned_departure !== s.planned_arrival && <>, then leaves at {s.planned_departure}</>}.
                    {s.window_start && s.window_end && (
                      <>
                        {" "}The customer accepts {s.window_start}–{s.window_end}
                        {spare != null && <>, so this is {spare >= 60 ? formatDuration(spare) : `${spare} min`} before the window closes</>}.
                      </>
                    )}
                  </div>
                </li>
              );
            })}
            {route.return_time && (
              <li>
                <span className="font-semibold">{route.return_time}</span> Back at the depot.
              </li>
            )}
          </ol>
        </div>

        <div>
          <p className="mb-1 font-semibold text-slate-900">Why it was planned this way</p>
          <ul className="list-disc space-y-1.5 pl-4 leading-relaxed">
            <li>
              <b>Who it carries:</b> these customers fit in this vehicle. It carries {tonnes(route.load_kg)} of its{" "}
              {tonnes(vehicle.weight_capacity_kg)} limit ({route.weight_utilization_pct}%) and {route.volume_m3.toFixed(1)} of{" "}
              {vehicle.volume_capacity_m3} m³ ({route.volume_utilization_pct}%). The system never loads a vehicle past either
              limit, and it uses as few vehicles as it sensibly can, so customers close together were put on the same one.
            </li>
            <li>
              <b>The order of stops:</b> chosen to keep the total driving short while still reaching every customer inside
              the time window they asked for.
              {tightest && (
                <>
                  {" "}The tightest one is <b>{tightest.stop.customer}</b>, reached with {tightest.spare >= 60 ? formatDuration(tightest.spare) : `${tightest.spare} min`} to spare.
                </>
              )}
            </li>
            <li>
              <b>The leave time:</b> {route.planned_departure} is as late as possible without making the driver wait at the
              first customer, and never before the driver&apos;s shift starts.
            </li>
            {needType.length > 0 && (
              <li>
                <b>Vehicle type:</b> {plural(needType.length, "customer")} here need a{" "}
                {VEHICLE_TYPE_LABEL[needType[0].required_vehicle_type!].toLowerCase()} vehicle, and this one is{" "}
                {vehicle.vehicle_type === needType[0].required_vehicle_type ? "exactly that" : typeName}.
              </li>
            )}
            {urgent.length > 0 && (
              <li>
                <b>Priority:</b> this route includes {urgent.map((s) => PRIORITY_LABEL[s.priority].toLowerCase()).join(", ")}{" "}
                priority {urgent.length === 1 ? "order" : "orders"}. If something cannot fit, the lowest priority orders are
                left out first.
              </li>
            )}
          </ul>
        </div>
      </div>
    </details>
  );
}
