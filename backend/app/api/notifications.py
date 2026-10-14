"""/notifications: things the dispatcher should know about right now."""
from flask import Blueprint, jsonify

from ..services.notification_service import vehicle_available_notifications

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.get("")
def list_notifications():
    """GET /notifications - e.g. "VH-5120 is available and could take 2 of the 3 unassigned orders".

    Computed on every call (nothing is stored), so the list is always current. Each item carries
    `suggested_event`, the body to POST to /events to re-plan with that vehicle.
    """
    return jsonify(items=vehicle_available_notifications())
