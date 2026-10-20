"""/demo endpoints: let someone trying out a shared demo start again with fresh sample data.

Only active when DEMO_MODE is on. On a real installation these answer 404, so nobody can wipe live data.
"""
from flask import Blueprint, current_app, jsonify

bp = Blueprint("demo", __name__, url_prefix="/demo")


@bp.get("")
def demo_status():
    """GET /demo - is this a demo installation? (the website shows a "Reset demo data" button if so)."""
    return jsonify(enabled=bool(current_app.config.get("DEMO_MODE")))


@bp.post("/reset")
def demo_reset():
    """POST /demo/reset - delete everything and load the sample data again (today +/- 1 day)."""
    if not current_app.config.get("DEMO_MODE"):
        return jsonify(error="not_found"), 404
    from seed.seed_data import ensure_demo, reset

    from ..simulator.engine import simulator

    simulator.reset()   # stop the simulator and forget its delays and positions
    reset()             # delete every row
    filled = ensure_demo()
    return jsonify(reset=True, days_filled=[d.isoformat() for d in filled])
