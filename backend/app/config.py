"""App configuration, read from environment variables (see .env.example)."""
import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://transport:transport@localhost:5432/transport",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")


class TestConfig(Config):
    """Tests use an in-memory SQLite database so they need no running PostgreSQL."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
