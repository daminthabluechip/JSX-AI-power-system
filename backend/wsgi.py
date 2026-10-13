"""Entry point: `flask --app wsgi run --debug`."""
from app import create_app

app = create_app()
