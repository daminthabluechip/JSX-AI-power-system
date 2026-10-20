"""What a shared / hosted installation needs: database URL format, API key, always-current demo data."""
from datetime import date, timedelta

import pytest

from app import create_app
from app.config import TestConfig, _database_url
from app.extensions import db
from app.models import Depot, Order, Vehicle
from seed.seed_data import ensure_demo


class KeyedConfig(TestConfig):
    API_KEY = "s3cret"


class DemoConfig(TestConfig):
    DEMO_MODE = True


def fresh_app(config):
    app = create_app(config)
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    return app, ctx


# ---------- database address ----------

@pytest.mark.parametrize("given,expected", [
    ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),      # what Render / Heroku give
    ("postgresql://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),
    ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),      # already right: unchanged
    ("sqlite:///x.db", "sqlite:///x.db"),
])
def test_database_url_is_made_sqlalchemy_ready(monkeypatch, given, expected):
    monkeypatch.setenv("DATABASE_URL", given)
    assert _database_url() == expected


# ---------- API key ----------

def test_api_key_guard():
    app, ctx = fresh_app(KeyedConfig)
    try:
        c = app.test_client()
        assert c.get("/health").status_code == 200                                    # host health check stays open
        assert c.get("/vehicles").status_code == 401                                  # no key
        assert c.get("/vehicles", headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.get("/vehicles", headers={"X-API-Key": "s3cret"}).status_code == 200
        assert c.post("/vehicles", json={}).status_code == 401                        # writes are protected too
        assert c.options("/vehicles").status_code != 401                              # browser pre-flight is not blocked
        assert c.get("/vehicles").get_json()["error"] == "unauthorized"
    finally:
        db.session.remove(); db.drop_all(); ctx.pop()


def test_no_key_configured_means_open(client):
    assert client.get("/vehicles").status_code == 200


# ---------- demo data ----------

def test_ensure_demo_fills_three_days_and_is_safe_to_repeat(app):
    filled = ensure_demo()
    today = date.today()
    assert filled == [today - timedelta(days=1), today, today + timedelta(days=1)]
    assert Depot.query.count() == 1 and Vehicle.query.count() == 10 and Order.query.count() == 150

    assert ensure_demo() == []                                    # nothing missing: nothing added
    assert Depot.query.count() == 1 and Vehicle.query.count() == 10 and Order.query.count() == 150


def test_ensure_demo_keeps_existing_data_and_only_fills_gaps(app):
    ensure_demo()
    Order.query.filter_by(target_date=date.today()).delete()      # e.g. the day rolled over / orders were used up
    db.session.add(Order(customer="Keep me", address="x", latitude=7, longitude=80, weight_kg=1, volume_m3=1,
                         target_date=date.today() - timedelta(days=1)))
    db.session.commit()

    assert ensure_demo() == [date.today()]                        # only today was empty
    assert Order.query.filter_by(customer="Keep me").count() == 1  # nothing was wiped
    assert Order.query.filter_by(target_date=date.today()).count() == 50


def test_demo_endpoints_are_off_on_a_real_installation(client):
    assert client.get("/demo").get_json() == {"enabled": False}
    assert client.post("/demo/reset").status_code == 404           # nobody can wipe live data


def test_demo_reset_restores_the_sample_data():
    app, ctx = fresh_app(DemoConfig)
    try:
        c = app.test_client()
        assert c.get("/demo").get_json() == {"enabled": True}
        ensure_demo()
        c.post("/vehicles", json={"registration": "VH-EXTRA", "weight_capacity_kg": 1000, "volume_capacity_m3": 5})
        Order.query.filter_by(target_date=date.today()).update({"status": "delivered"})
        db.session.commit()

        res = c.post("/demo/reset")
        assert res.status_code == 200 and res.get_json()["reset"] is True
        assert Vehicle.query.count() == 10 and Vehicle.query.filter_by(registration="VH-EXTRA").count() == 0
        assert Order.query.filter_by(target_date=date.today(), status="pending").count() == 50
    finally:
        db.session.remove(); db.drop_all(); ctx.pop()
