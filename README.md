# AI-Powered Transport Planning System

Plans which vehicle serves which customer, in what order and at what time, and re-plans when
something goes wrong. A dispatcher generates a day's plan in one click; the system keeps weight,
volume, customer time windows and driver shifts, combines deliveries onto as few vehicles as it
can, and recovers when a vehicle is delayed, breaks down, or an order is added or cancelled.

| Layer | Technology |
|---|---|
| Dashboard | Next.js 16, TypeScript, Tailwind CSS, Leaflet + OpenStreetMap |
| API | Python, Flask, SQLAlchemy, Alembic |
| Optimizer | Google OR-Tools (vehicle routing with capacities and time windows) |
| Database | PostgreSQL |
| Travel times | Offline estimate by default, OSRM for real roads |

```
Next.js dashboard ──HTTP/JSON──▶ Flask API ──▶ OR-Tools optimizer
                                     │  ▲
                                     │  └── position readings (simulator now, JXG tracking later)
                                     ├────▶ PostgreSQL
                                     └────▶ routing service (OSRM, cached)
```

## Quick start (Docker)

Needs Docker Desktop.

```bash
docker compose up --build                                  # database + API + dashboard
docker compose exec backend flask --app wsgi seed --reset  # load sample data (1 depot, 10 vehicles, 50 orders)
```

Open **http://localhost:3000**. The API is at http://127.0.0.1:5000. Use `127.0.0.1`, not
`localhost`, for the API: on Windows `localhost` tries IPv6 first and every request then waits
about 2 seconds.

Try it: **Route Planning** → Generate Route → Dispatch Route → **Live Tracking** → Start the
simulator → "Jam" a vehicle → when the alert appears, "Re-plan now".

## Development setup (without containers for the app)

Prerequisites: Python 3.12+, Node 22+, Docker (for PostgreSQL).

```powershell
# 1. Database only. It listens on port 5433, so it does not clash with a PostgreSQL on 5432.
docker compose up -d db

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # macOS/Linux: cp .env.example .env
flask --app wsgi db upgrade           # create the tables
flask --app wsgi seed --reset         # sample data
flask --app wsgi run --port 5000

# 3. Frontend (second terminal)
cd frontend
npm install
copy .env.local.example .env.local
npm run dev                           # http://localhost:3000
```

### Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://transport:transport@localhost:5433/transport` | database connection |
| `CORS_ORIGIN` | `http://localhost:3000` | dashboard address allowed to call the API |
| `ROUTING_PROVIDER` | `haversine` | `haversine` (offline estimate) or `osrm` (real road distances) |
| `OSRM_URL` | `https://router.project-osrm.org` | OSRM server (the public one is for light development use only) |
| `OSRM_TIME_FACTOR` | `1.0` | multiplier on OSRM driving times for traffic (OSRM assumes free-flowing roads); try `1.3` |
| `SOLVER_TIME_LIMIT_S` | `10` | how long the optimizer searches when generating a plan |
| `REPLAN_TIME_LIMIT_S` | `10` | same, for re-plans after a disruption |
| `TRACKING_DELAY_THRESHOLD_MIN` | `15` | minutes behind schedule before a delay alert is raised |
| `NEXT_PUBLIC_API_URL` (frontend) | `http://127.0.0.1:5000` | API address the browser calls |

## How it works

**Planning** (`backend/app/optimizer/`). `POST /plans/generate` builds a vehicle routing problem
and solves it with OR-Tools: a quick first solution, then local search until the time limit.
Weight, volume, time windows, driver shifts and vehicle types are hard rules (an order can
require a vehicle type such as `refrigerated` or `flatbed`; only vehicles of that type may serve
it). Distance, driving time and a fixed cost
per vehicle used are minimised, which is what pushes it to combine deliveries. If not every
order fits, the lowest-priority ones are dropped first and listed with the reason. A
nearest-neighbour plan is built from the same orders as a baseline, and an independent validator
re-checks every plan before it is saved.

**Re-planning** (`POST /events`). Four disruption types: `delay`, `breakdown`, `rush_order`,
`cancellation`. Each creates a new plan version (the old one is kept; compare them with
`GET /plans/{id}/compare/{other}`). The new plan starts from the old one and charges a penalty
for moving an order to a different vehicle, so a small disruption does not reshuffle the fleet.
Once a plan has been dispatched, a re-plan starts each vehicle from its latest reported position,
no earlier than "now", and only plans orders that are not yet delivered.

**Tracking.** Every position goes through one function (`tracking_service.ingest`, also
`POST /tracking/positions`). Today the built-in simulator produces them; a real tracking feed only
needs to call the same endpoint. The system compares each vehicle's position with where the plan
says it should be, raises an alert past the delay threshold, and offers a ready-to-use re-plan.

**Reports.** `GET /reports` computes on-time rate (from recorded actual arrival times),
utilization, planned distance and savings versus the baseline from stored data. Where there is no
data it says so rather than inventing a figure.

### API

| Endpoint | Purpose |
|---|---|
| `GET/POST /vehicles`, `GET/PATCH/DELETE /vehicles/{id}`, `GET /vehicles/summary` | fleet |
| `GET/POST /orders`, `GET/PATCH/DELETE /orders/{id}` | delivery orders |
| `POST /orders/import`, `GET /orders/import/template` | bulk-load orders from a CSV file |
| `POST /plans/generate` | solve in the background (returns 202 and a plan id) |
| `GET /plans`, `GET /plans/{id}` | plan with routes, stops, arrival times, utilization |
| `GET /plans/{id}/compare/{other}` | what changed between two plan versions |
| `POST /plans/{id}/dispatch` | send a plan to the vehicles |
| `POST /events`, `GET /events` | report a disruption (triggers a re-plan) |
| `GET /tracking/positions`, `GET /tracking/alerts`, `POST /tracking/positions` | live view and feed entry point |
| `POST /tracking/simulator` | `start`, `stop`, `delay`, `reset` |
| `GET /reports`, `GET /reports/export` | analytics and CSV download |

The vehicle and order lists accept `page` and `per_page`; errors are `{"error": ..., "details": ...}` with a
400 (invalid input), 404, or 409 (conflict).

## Tests and demo

The backend has about 70 automated tests. The screens were also clicked through in a real browser
(headless Chromium driven by Playwright): vehicle and order forms, CSV import, plan generation,
route maps, the simulator with a jam and live re-plan, optimization, reports and CSV export.

```bash
cd backend
python -m pytest -q --cov=app          # unit tests, every endpoint, the optimizer's targets
python scripts/demo_replan.py --reseed # plan, then trigger all four disruptions and re-plan
cd ../frontend
npm run lint && npx tsc --noEmit && npm run build
```

`demo_replan.py --reseed` **wipes and reloads the sample data**. CI (`.github/workflows/ci.yml`)
runs both test suites on every push.

### Results against the proposal's targets

Measured on the sample set (1 depot, 9 available vehicles, 50 orders with mixed time windows):

| Target | Result |
|---|---|
| Capacity violations: 0 | 0 (checked on every plan) |
| Time window violations: 0 | 0 |
| Plan generated in 30 s or less | about 10 s (the solver time limit) |
| Re-plan in 15 s or less | about 10 s |
| At least 10% shorter than a nearest-neighbour plan | 29% on the sample data (13 of 50 orders need a refrigerated or flatbed vehicle); see the note below |
| Backend test coverage 70% or more | 94% |

**Read the "% shorter" figure with care.** It compares total kilometres, but the optimizer and
the baseline do not always serve the same orders: dropping an order costs the optimizer far more
than extra driving, so it will serve an extra order even if that adds distance, while the baseline
simply leaves it out. Example on the sample data: adding two small orders moved the figure from
28.6% to 9.6%, because the plan went from serving 49 orders to 51. A fairer measure is
kilometres per delivered order, or comparing plans that serve the same set of orders; agree which
with your mentor before reporting it as a headline number.

### Straight-line estimate vs real roads (OSRM)

Both were run on the sample data (the OSRM figures against the public demo server):

| | Estimate (default) | OSRM, free-flow times | OSRM, `OSRM_TIME_FACTOR=1.3` |
|---|---|---|---|
| Vehicles used | 6 | 5 | 6 |
| Plan distance | 1310 km (about 1325 km if driven on real roads) | 1008 km | 1202 km |
| Shorter than baseline | 35% | 54% | 42% |
| Plan / re-plan time | 10 s / 10 s | 11 s / 10 s | 11 s / 10 s |

Road distances match the estimate on average, but individual trips differ by -20% to +60%, so
real roads give a noticeably better plan. OSRM's driving times are free-flow (about 30% faster than
the estimate's 40 km/h), which lets the optimizer pack more onto fewer vehicles; set
`OSRM_TIME_FACTOR` above 1 to leave a margin for traffic. A larger margin gives more robust plans
but leaves more orders unassigned after a breakdown. The public OSRM server is meant for light
development use and limits request size (typically about 100 points); run your own OSRM
container for production or for larger problems. Results are cached per pair of points, so
re-plans do not call OSRM again.

## Project layout

```
backend/
  app/api/         HTTP endpoints          app/models/    database tables
  app/optimizer/   OR-Tools model, baseline, validator
  app/services/    plans, routing, tracking, reports
  app/simulator/   vehicle simulator       migrations/    Alembic
  seed/            sample data             tests/  scripts/
frontend/src/
  app/             one folder per screen   components/    layout, forms, map, ui
  lib/api.ts       every backend call lives here
```

## Known limits and open items

- **Live tracking** uses the simulator. Integrating JXG's tracking system means calling
  `POST /tracking/positions` from an adapter (marked `TODO: TOOL/API CALL HERE` in the code).
- **Road geometry.** Travel times default to a straight-line estimate; set `ROUTING_PROVIDER=osrm`
  for real roads (tested against the public OSRM server). Vehicle movement on the map is still
  drawn as straight lines between stops.
- **Addresses are not geocoded**: delivery coordinates are entered by hand.
- **Single depot.** Planning from several depots is out of scope.
- **Simulator state is in memory**, so it resets when the API restarts, and the API must run as
  one process (the Docker image already does).
- A re-plan after a delay uses the delay measured at that moment; if the jam continues, another
  alert follows.
- No authentication: the dashboard shows a fixed user.
