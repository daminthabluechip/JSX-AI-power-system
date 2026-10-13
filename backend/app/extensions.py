"""Shared Flask extension objects (created here, attached to the app in create_app)."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()      # database access
migrate = Migrate()    # Alembic migrations (flask db ...)
