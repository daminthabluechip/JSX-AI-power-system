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

    # TODO: register blueprints here as they are built, e.g.
    # from .api.vehicles import bp as vehicles_bp; app.register_blueprint(vehicles_bp)

    return app
