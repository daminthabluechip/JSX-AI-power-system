"""/orders endpoints: create, read, update and delete delivery orders, and import them from CSV."""
import csv
import io

from flask import Blueprint, Response, jsonify, request

from ..extensions import db
from ..models import VEHICLE_TYPES, Event, Order, Stop
from .helpers import ValidationError, clean_payload, fmt_time, paginate

bp = Blueprint("orders", __name__, url_prefix="/orders")

PRIORITIES = ["critical", "high", "medium", "low"]
STATUSES = ["pending", "scheduled", "in_transit", "delivered", "cancelled"]

SPEC = {
    "customer": {"kind": "str", "required": True},
    "address": {"kind": "str", "required": True},
    "latitude": {"kind": "num", "required": True},
    "longitude": {"kind": "num", "required": True},
    "weight_kg": {"kind": "num", "required": True, "positive": True},
    "volume_m3": {"kind": "num", "required": True, "positive": True},
    "priority": {"kind": "str", "choices": PRIORITIES},
    "target_date": {"kind": "date", "required": True},
    "earliest_arrival": {"kind": "time"},
    "latest_arrival": {"kind": "time"},
    "required_vehicle_type": {"kind": "str", "choices": VEHICLE_TYPES},   # optional: null = any vehicle
    "status": {"kind": "str", "choices": STATUSES},
}


def to_dict(o):
    """Order -> JSON-friendly dict."""
    return {
        "id": o.id,
        "customer": o.customer,
        "address": o.address,
        "latitude": o.latitude,
        "longitude": o.longitude,
        "weight_kg": o.weight_kg,
        "volume_m3": o.volume_m3,
        "priority": o.priority,
        "target_date": o.target_date.isoformat(),
        "earliest_arrival": fmt_time(o.earliest_arrival),
        "latest_arrival": fmt_time(o.latest_arrival),
        "required_vehicle_type": o.required_vehicle_type,
        "status": o.status,
    }


def check_window(data, current=None):
    """The earliest arrival must not be later than the latest arrival."""
    start = data.get("earliest_arrival", getattr(current, "earliest_arrival", None))
    end = data.get("latest_arrival", getattr(current, "latest_arrival", None))
    if start and end and start > end:
        return jsonify(error="validation_failed",
                       details={"latest_arrival": "must be after earliest_arrival"}), 400


# ---------- CSV import ----------

IMPORT_COLUMNS = ["customer", "address", "latitude", "longitude", "weight_kg", "volume_m3",
                  "priority", "target_date", "earliest_arrival", "latest_arrival", "required_vehicle_type"]
IMPORT_REQUIRED = ["customer", "address", "latitude", "longitude", "weight_kg", "volume_m3", "target_date"]
MAX_IMPORT_ROWS = 2000
TEMPLATE_ROWS = [
    ["Fresh Mart", "12 Galle Road, Colombo 03", "6.9147", "79.8523", "850", "4.5", "high", "2026-10-14", "08:00", "12:00", ""],
    ["City Pharma", "45 Peradeniya Road, Kandy", "7.2760", "80.6000", "300", "1.2", "critical", "2026-10-14", "09:00", "15:00", "refrigerated"],
]


def read_csv_upload():
    """Get the CSV text from a multipart upload (field "file") or from the raw request body."""
    if "file" in request.files:
        raw = request.files["file"].read()
    else:
        raw = request.get_data()
    if not raw.strip():
        raise ValidationError({"file": "empty: send a CSV file (multipart field 'file') or the CSV text as the body"})
    try:
        return raw.decode("utf-8-sig")   # utf-8-sig drops the BOM that Excel adds
    except UnicodeDecodeError:
        raise ValidationError({"file": "must be UTF-8 text (in Excel use 'CSV UTF-8')"})


@bp.get("/import/template")
def import_template():
    """GET /orders/import/template - a CSV with the right columns and two example rows."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(IMPORT_COLUMNS)
    writer.writerows(TEMPLATE_ROWS)
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=orders-template.csv"})


@bp.post("/import")
def import_orders():
    """POST /orders/import?skip_invalid=false - create many orders from a CSV file.

    Columns: customer, address, latitude, longitude, weight_kg, volume_m3, target_date are
    required; priority (default medium), earliest_arrival and latest_arrival (HH:MM) and
    required_vehicle_type (truck, van, refrigerated or flatbed) are optional.
    Every row is checked first. By default ONE bad row rejects the whole file and nothing is
    saved; with ?skip_invalid=true the valid rows are saved and the bad ones are reported.
    Rows are numbered like in a spreadsheet (the header is row 1).
    """
    skip_invalid = request.args.get("skip_invalid", "false").lower() == "true"
    reader = csv.DictReader(io.StringIO(read_csv_upload()))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in IMPORT_REQUIRED if c not in headers]
    if missing:
        raise ValidationError({"file": f"missing columns: {', '.join(missing)}"})

    valid, errors = [], []
    for line, raw in enumerate(reader, start=2):
        if line - 1 > MAX_IMPORT_ROWS:
            raise ValidationError({"file": f"too many rows (maximum {MAX_IMPORT_ROWS})"})
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue   # skip blank lines
        # Blank cells become null: optional fields stay empty, required ones are reported.
        body = {c: (row.get(c) or None) for c in IMPORT_COLUMNS}
        body["priority"] = (body["priority"] or "medium").lower()
        if body["required_vehicle_type"]:
            body["required_vehicle_type"] = body["required_vehicle_type"].lower()
        try:
            data = clean_payload(body, SPEC)
            if data.get("earliest_arrival") and data.get("latest_arrival")                     and data["earliest_arrival"] > data["latest_arrival"]:
                raise ValidationError({"latest_arrival": "must be after earliest_arrival"})
            valid.append(Order(**data))
        except ValidationError as err:
            errors.append({"row": line, "errors": err.errors})

    if errors and not skip_invalid:
        return jsonify(error="validation_failed", created=0, skipped=len(errors), errors=errors[:100]), 400
    db.session.add_all(valid)
    db.session.commit()
    return jsonify(created=len(valid), skipped=len(errors), errors=errors[:100]), 201


@bp.get("")
def list_orders():
    """GET /orders?q=&status=&priority=&date=&page=&per_page= - filtered, paginated list."""
    query = Order.query.order_by(Order.id)
    if status := request.args.get("status"):
        query = query.filter(Order.status == status)
    if priority := request.args.get("priority"):
        query = query.filter(Order.priority == priority)
    if day := request.args.get("date"):
        query = query.filter(Order.target_date == day)
    if q := request.args.get("q"):
        query = query.filter(Order.customer.ilike(f"%{q}%") | Order.address.ilike(f"%{q}%"))
    return paginate(query, to_dict)


@bp.get("/<int:order_id>")
def get_order(order_id):
    return jsonify(to_dict(db.get_or_404(Order, order_id)))


@bp.post("")
def create_order():
    data = clean_payload(request.get_json(silent=True), SPEC)
    if (bad := check_window(data)):
        return bad
    order = Order(**data)
    db.session.add(order)
    db.session.commit()
    return jsonify(to_dict(order)), 201


@bp.put("/<int:order_id>")
@bp.patch("/<int:order_id>")
def update_order(order_id):
    order = db.get_or_404(Order, order_id)
    data = clean_payload(request.get_json(silent=True), SPEC, partial=True)
    if (bad := check_window(data, order)):
        return bad
    for key, value in data.items():
        setattr(order, key, value)
    db.session.commit()
    return jsonify(to_dict(order))


@bp.delete("/<int:order_id>")
def delete_order(order_id):
    order = db.get_or_404(Order, order_id)
    if Stop.query.filter_by(order_id=order_id).first() or Event.query.filter_by(order_id=order_id).first():
        return jsonify(error="conflict", details={
            "message": "This order is part of existing plans. Cancel it instead of deleting it."}), 409
    db.session.delete(order)
    db.session.commit()
    return "", 204
