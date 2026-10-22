from datetime import date, time

from flask import jsonify, request
from sqlalchemy.exc import IntegrityError

from ..extensions import db


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return jsonify(error="validation_failed", details=err.errors), 400

    @app.errorhandler(IntegrityError)
    def handle_integrity(_):
        db.session.rollback()
        return jsonify(error="conflict", details={"message": "This record is still referenced by other data"}), 409

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify(error="not_found"), 404


def parse_time(value):
    return None if value in (None, "") else time.fromisoformat(value)


def parse_date(value):
    return date.fromisoformat(value)


def fmt_time(t):
    return t.strftime("%H:%M") if t else None


def clean_payload(data, spec, partial=False):
    if not isinstance(data, dict):
        raise ValidationError({"body": "JSON object expected"})

    errors, out = {}, {}
    for name, rules in spec.items():
        if name not in data:
            if rules.get("required") and not partial:
                errors[name] = "required"
            continue
        if data[name] is None:
            if rules.get("required"):
                errors[name] = "required"
            else:
                out[name] = None
            continue

        value, kind = data[name], rules["kind"]
        try:
            if kind == "num":
                value = float(value)
                if rules.get("positive") and value <= 0:
                    raise ValueError("must be greater than 0")
            elif kind == "time":
                value = parse_time(value)
            elif kind == "date":
                value = parse_date(value)
            else:
                value = str(value).strip()
                if rules.get("required") and not value:
                    raise ValueError("must not be empty")
            if "choices" in rules and value not in rules["choices"]:
                raise ValueError(f"must be one of {rules['choices']}")
        except (ValueError, TypeError) as exc:
            errors[name] = str(exc)
            continue
        out[name] = value

    if errors:
        raise ValidationError(errors)
    return out


def paginate(query, serializer):
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 200)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        items=[serializer(x) for x in result.items],
        total=result.total,
        page=page,
        per_page=per_page,
    )
