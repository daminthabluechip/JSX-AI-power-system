"""Flask application factory."""
from dotenv import load_dotenv
from flask import Flask, jsonify
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

    # API routes.
    from .api.helpers import register_error_handlers
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

    register_cli(app)
    return app


def register_cli(app):
    """Custom `flask` commands."""
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete all existing data first.")
    def seed_command(reset):
        """Load the sample depot, vehicles and orders."""
        from seed.seed_data import reset as reset_data, seed

        if reset:
            reset_data()
        seed()
        click.echo("Seeded 1 depot, 10 vehicles and 50 orders.")
