from datetime import date

from flask import Blueprint, Response, jsonify, request

from ..services.report_service import build_report, report_csv
from .helpers import ValidationError

bp = Blueprint("reports", __name__, url_prefix="/reports")


def parse_params():
    days = request.args.get("days", 30, type=int)
    if not 1 <= days <= 365:
        raise ValidationError({"days": "between 1 and 365"})
    try:
        today = date.fromisoformat(request.args["today"]) if "today" in request.args else None
    except ValueError:
        raise ValidationError({"today": "expected YYYY-MM-DD"})
    return days, today


@bp.get("")
def report():
    days, today = parse_params()
    return jsonify(build_report(days, today))


@bp.get("/export")
def export():
    days, today = parse_params()
    csv = report_csv(build_report(days, today))
    return Response(csv, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=report-last-{days}-days.csv"})
