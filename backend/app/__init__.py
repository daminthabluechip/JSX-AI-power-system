"""Flask application factory."""
import hmac

from dotenv import load_dotenv

from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import Config
from .extensions import db, migrate


def create_app(config_class=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Let the Next.js dashboard call this API from the browser.
    CORS(app, origins=app.config["CORS_ORIGIN"])

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic can see every table.
    from . import models  # noqa: F401

    @app.get("/health")
    def health():
        """Simple health check (used by the dashboard status indicator)."""
        return jsonify(status="ok")

    @app.before_request
    def require_api_key():
        """If an API key is configured, refuse any request that does not carry it. /health stays open (the
        host uses it to check the service is alive) and so does OPTIONS (browser pre-flight checks)."""
        key = app.config.get("API_KEY")
        if not key or request.method == "OPTIONS" or request.path == "/health":
            return None
        if not hmac.compare_digest(request.headers.get("X-API-Key", ""), key):
            return jsonify(error="unauthorized", details={"message": "missing or wrong API key"}), 401
        return None

    # API routes.
    from .api.helpers import register_error_handlers
    from .api.demo import bp as demo_bp
    from .api.events import bp as events_bp
    from .api.notifications import bp as notifications_bp
    from .api.orders import bp as orders_bp
    from .api.plans import bp as plans_bp
    from .api.reports import bp as reports_bp
    from .api.tracking import bp as tracking_bp
    from .api.vehicles import bp as vehicles_bp

    register_error_handlers(app)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(demo_bp)

    register_cli(app)
    return app


def register_cli(app):
    """Custom `flask` commands."""
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete all existing data first.")
    @click.option("--demo", is_flag=True, help="Only fill in what is missing (safe to run on every start-up).")
    def seed_command(reset, demo):
        """Load the sample depot, vehicles and orders."""
        from seed.seed_data import ensure_demo, reset as reset_data, seed

        if demo:
            filled = ensure_demo()
            click.echo(f"Demo data ready (added orders for {len(filled)} day(s)).")
            return
        if reset:
            reset_data()
        seed()
        click.echo("Seeded 1 depot, 10 vehicles and 50 orders.")
