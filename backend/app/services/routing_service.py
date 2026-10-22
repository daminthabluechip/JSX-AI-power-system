import math

import requests

EARTH_RADIUS_M = 6_371_000


def haversine_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


class HaversineProvider:
    def __init__(self, speed_kmh=40.0, detour=1.3):
        self.speed_kmh = speed_kmh
        self.detour = detour

    def matrix(self, coords):
        dist = [[int(haversine_m(a, b) * self.detour) for b in coords] for a in coords]
        dur = [[math.ceil(d / 1000 / self.speed_kmh * 60) for d in row] for row in dist]
        return dist, dur


class OsrmProvider:
    def __init__(self, base_url="https://router.project-osrm.org", timeout=30, time_factor=1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.time_factor = time_factor
        self._cache = {}

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
    name = config.get("ROUTING_PROVIDER", "haversine")
    url = config.get("OSRM_URL", "https://router.project-osrm.org")
    factor = float(config.get("OSRM_TIME_FACTOR", 1.0))
    key = (name, url, factor)
    if key not in _providers:
        _providers[key] = OsrmProvider(url, time_factor=factor) if name == "osrm" else HaversineProvider()
    return _providers[key]
