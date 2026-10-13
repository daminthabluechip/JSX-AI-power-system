"""The routing providers. OSRM is tested against a fake server so the tests need no network."""
import pytest

from app.services import routing_service
from app.services.routing_service import HaversineProvider, OsrmProvider, get_provider, haversine_m

COLOMBO, KANDY = (6.9271, 79.8612), (7.2906, 80.6337)


class FakeResponse:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._body


def fake_osrm(monkeypatch, body=None, calls=None):
    """Replace requests.get with a canned OSRM /table answer (2 points: 100 km, 3600 s)."""
    body = body or {"code": "Ok", "distances": [[0, 100000], [100000, 0]], "durations": [[0, 3600], [3600, 0]]}

    def fake_get(url, params=None, timeout=None):
        if calls is not None:
            calls.append(url)
        return FakeResponse(body)

    monkeypatch.setattr(routing_service.requests, "get", fake_get)


def test_haversine_distance_is_realistic():
    assert 90_000 < haversine_m(COLOMBO, KANDY) < 100_000      # Colombo-Kandy is about 94 km in a straight line
    assert haversine_m(COLOMBO, COLOMBO) == 0


def test_haversine_matrix_shape_and_detour():
    dist, dur = HaversineProvider(speed_kmh=60, detour=1.5).matrix([COLOMBO, KANDY])
    assert dist[0][0] == 0 and dist[0][1] == dist[1][0]
    assert dist[0][1] == pytest.approx(haversine_m(COLOMBO, KANDY) * 1.5, abs=2)   # detour applied to distance
    assert dur[0][1] == pytest.approx(dist[0][1] / 1000, abs=1)                    # 60 km/h = 1 km per minute


def test_osrm_sends_lon_lat_order_and_parses_the_answer(monkeypatch):
    seen = []
    fake_osrm(monkeypatch, calls=seen)
    dist, dur = OsrmProvider("http://osrm.test/").matrix([COLOMBO, KANDY])
    assert "79.8612,6.9271;80.6337,7.2906" in seen[0]          # OSRM wants longitude first
    assert dist == [[0, 100000], [100000, 0]] and dur == [[0, 60], [60, 0]]   # seconds -> minutes


def test_osrm_caches_pairs_and_only_asks_for_new_points(monkeypatch):
    seen = []
    fake_osrm(monkeypatch, calls=seen)
    provider = OsrmProvider()
    provider.matrix([COLOMBO, KANDY])
    provider.matrix([COLOMBO, KANDY])
    assert len(seen) == 1                                       # second call served from the cache
    provider.matrix([KANDY, COLOMBO])                            # same pairs, other order: still cached
    assert len(seen) == 1


def test_osrm_time_factor_scales_times_but_not_distances(monkeypatch):
    fake_osrm(monkeypatch)
    dist, dur = OsrmProvider(time_factor=1.5).matrix([COLOMBO, KANDY])
    assert dist[0][1] == 100000 and dur[0][1] == 90             # 60 min x 1.5


def test_osrm_errors_are_raised_not_swallowed(monkeypatch):
    fake_osrm(monkeypatch, body={"code": "NoRoute", "message": "no route found"})
    with pytest.raises(RuntimeError, match="NoRoute"):
        OsrmProvider().matrix([COLOMBO, KANDY])

    monkeypatch.setattr(routing_service.requests, "get", lambda *a, **k: FakeResponse({}, status=503))
    with pytest.raises(RuntimeError, match="503"):
        OsrmProvider().matrix([COLOMBO, KANDY])


def test_provider_choice_follows_the_config():
    assert isinstance(get_provider({"ROUTING_PROVIDER": "haversine"}), HaversineProvider)
    osrm = get_provider({"ROUTING_PROVIDER": "osrm", "OSRM_URL": "http://a.test", "OSRM_TIME_FACTOR": 1.3})
    assert isinstance(osrm, OsrmProvider) and osrm.time_factor == 1.3
    assert get_provider({"ROUTING_PROVIDER": "osrm", "OSRM_URL": "http://b.test"}) is not osrm   # new settings, new provider
