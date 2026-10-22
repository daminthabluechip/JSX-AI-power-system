from flask import Blueprint, current_app, jsonify

bp = Blueprint("demo", __name__, url_prefix="/demo")


@bp.get("")
def demo_status():
    return jsonify(enabled=bool(current_app.config.get("DEMO_MODE")))


@bp.post("/reset")
def demo_reset():
    if not current_app.config.get("DEMO_MODE"):
        return jsonify(error="not_found"), 404
    from seed.seed_data import ensure_demo, reset

    from ..simulator.engine import simulator

    simulator.reset()
    reset()
    filled = ensure_demo()
    return jsonify(reset=True, days_filled=[d.isoformat() for d in filled])
