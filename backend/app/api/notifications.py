from flask import Blueprint, jsonify

from ..services.notification_service import vehicle_available_notifications

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.get("")
def list_notifications():
    return jsonify(items=vehicle_available_notifications())
