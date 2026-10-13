"""Travel distance / time between locations.

The optimizer needs a table (matrix) of distance and time between every pair of points.
Two providers return it in the same format:

* HaversineProvider - straight-line estimate, works offline (default for development/tests)
* OsrmProvider      - real road network from an OSRM server

Both return (dist_m, dur_min): square lists of ints where [i][j] is "from point i to j".
"""
import math

import requests

EARTH_RADIUS_M = 6_371_000


def haversine_m(a, b):
    """Great-circle distance in metres between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


class HaversineProvider:
    """Estimate roads as straight line x detour factor, driven at an average speed."""

    def __init__(self, speed_kmh=40.0, detour=1.3):
        self.speed_kmh = speed_kmh
        self.detour = detour

    def matrix(self, coords):
        dist = [[int(haversine_m(a, b) * self.detour) for b in coords] for a in coords]
        dur = [[math.ceil(d / 1000 / self.speed_kmh * 60) for d in row] for row in dist]
        return dist, dur


class OsrmProvider:
    """Road distances from OSRM's /table API, with a per-pair cache.

    The cache matters because the free service has request limits and the matrix grows with
    the square of the number of stops; re-planning mostly reuses the same pairs.
    """

    def __init__(self, base_url="https://router.project-osrm.org", timeout=30, time_factor=1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # OSRM gives free-flow driving times (no traffic, no stops). Multiply by e.g. 1.3 to plan
        # with a safety margin for traffic; distances are not affected.
        self.time_factor = time_factor
        self._cache = {}  # ((lat, lon), (lat, lon)) -> (metres, minutes)

    @staticmethod
    def _key(p):
        return (round(p[0], 5), round(p[1], 5))

    def matrix(self, coords):
        keys = [self._key(c) for c in coords]
        missing = any((a, b) not in self._cache for a in keys for b in keys)
        if missing:
            self._fetch(coords, keys)
        n = len(keys)
        dist = [[self._cache[(keys[i], keys[j])][0] for j in range(n)] for i in range(n)]
        dur = [[self._cache[(keys[i], keys[j])][1] for j in range(n)] for i in range(n)]
        return dist, dur

    def _fetch(self, coords, keys):
        # TODO: TOOL/API CALL HERE - OSRM table service. OSRM expects "lon,lat" pairs separated
        # by ";". The public demo server is for light development use only; for production run
        # your own OSRM container (or switch to OpenRouteService, which needs an API key).
        path = ";".join(f"{lon},{lat}" for lat, lon in coords)
        resp = requests.get(f"{self.base_url}/table/v1/driving/{path}",
                            params={"annotations": "duration,distance"}, timeout=self.timeout)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != "Ok":
            raise RuntimeError(f"OSRM error: {body.get('code')} {body.get('message', '')}")
        for i, row in enumerate(body["distances"]):
            for j, metres in enumerate(row):
                seconds = body["durations"][i][j]
                self._cache[(keys[i], keys[j])] = (int(metres), math.ceil(seconds / 60 * self.time_factor))


_providers = {}


def get_provider(config):
    """Pick the provider named by ROUTING_PROVIDER in the app config (cached per setting)."""
    name = config.get("ROUTING_PROVIDER", "haversine")
    url = config.get("OSRM_URL", "https://router.project-osrm.org")
    factor = float(config.get("OSRM_TIME_FACTOR", 1.0))
    key = (name, url, factor)   # a new provider (and a fresh cache) whenever the settings change
    if key not in _providers:
        _providers[key] = OsrmProvider(url, time_factor=factor) if name == "osrm" else HaversineProvider()
    return _providers[key]
