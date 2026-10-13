from app import create_app
from app.config import TestConfig
from app.extensions import db


def test_health_and_tables_create():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()  # proves every model definition is valid
    assert app.test_client().get("/health").get_json() == {"status": "ok"}
