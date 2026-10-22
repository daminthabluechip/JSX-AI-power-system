import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE") or Path(__file__).resolve().parent.parent / ".env")


def _database_url():
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://transport:transport@localhost:5433/transport")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    API_KEY = os.getenv("API_KEY") or None
    DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
    ROUTING_PROVIDER = os.getenv("ROUTING_PROVIDER", "haversine")
    OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
    OSRM_TIME_FACTOR = float(os.getenv("OSRM_TIME_FACTOR", "1.0"))
    SOLVER_TIME_LIMIT_S = int(os.getenv("SOLVER_TIME_LIMIT_S", "10"))
    REPLAN_TIME_LIMIT_S = int(os.getenv("REPLAN_TIME_LIMIT_S", "10"))
    TRACKING_DELAY_THRESHOLD_MIN = int(os.getenv("TRACKING_DELAY_THRESHOLD_MIN", "15"))
    PLAN_SYNC = False


class TestConfig(Config):
    TESTING = True
    API_KEY = None
    DEMO_MODE = False
    ROUTING_PROVIDER = "haversine"
    OSRM_TIME_FACTOR = 1.0
    PLAN_SYNC = True
    SOLVER_TIME_LIMIT_S = 3
    REPLAN_TIME_LIMIT_S = 2
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
