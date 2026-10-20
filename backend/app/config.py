"""App configuration, read from environment variables (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env BEFORE the Config class below is defined: its settings are read from the
# environment at the moment this file is imported, so loading .env later (e.g. inside create_app)
# would be too late and the file would be silently ignored. Variables already set in the real
# environment (Docker, CI, a shell) are not overwritten, so they win over .env. ENV_FILE lets a
# different file be used (the tests do this).
load_dotenv(os.getenv("ENV_FILE") or Path(__file__).resolve().parent.parent / ".env")


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://transport:transport@localhost:5433/transport",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024   # uploads (CSV import) larger than 2 MB are rejected
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
    # "haversine" (offline estimate) or "osrm" (real roads, see services/routing_service.py)
    ROUTING_PROVIDER = os.getenv("ROUTING_PROVIDER", "haversine")
    OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
    # Multiplier on OSRM driving times to allow for traffic (OSRM itself assumes free-flowing roads).
    OSRM_TIME_FACTOR = float(os.getenv("OSRM_TIME_FACTOR", "1.0"))
    SOLVER_TIME_LIMIT_S = int(os.getenv("SOLVER_TIME_LIMIT_S", "10"))
    REPLAN_TIME_LIMIT_S = int(os.getenv("REPLAN_TIME_LIMIT_S", "10"))  # target: re-plan in <= 15 s
    TRACKING_DELAY_THRESHOLD_MIN = int(os.getenv("TRACKING_DELAY_THRESHOLD_MIN", "15"))
    PLAN_SYNC = False  # False: solve in a background thread; True: solve inside the request


class TestConfig(Config):
    """Tests use an in-memory SQLite database so they need no running PostgreSQL."""
    TESTING = True
    # Tests must never depend on the network or on what a developer put in .env
    ROUTING_PROVIDER = "haversine"
    OSRM_TIME_FACTOR = 1.0
    PLAN_SYNC = True
    SOLVER_TIME_LIMIT_S = 3
    REPLAN_TIME_LIMIT_S = 2
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
