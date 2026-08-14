import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request

from repositories.employee_repository import (
    get_employee_advice_by_id,
    get_employee_advice_history,
    get_employee_assignments,
)
from services.employee_rag_service import (
    generate_employee_advice_offline,
)


# ============================================================
# BLUEPRINT
# ============================================================

employee_bp = Blueprint(
    "employee",
    __name__,
    url_prefix="/api/employee",
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def _json_safe_value(
    value: Any,
) -> Any:
    """Convert database values into JSON-safe values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe_value(item)
            for item in value
        ]

    return value


def _parse_saved_json(
    value: Any,
) -> Any:
    """Convert stored MySQL JSON into Python data."""

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, bytes):
        value = value.decode("utf-8")

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)

    except json.JSONDecodeError:
        return value


def _validate_positive_integer(
    value: Any,
    field_name: str,
) -> int:
    """Validate a positive integer."""

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    try:
        number = int(value)

    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be a positive integer."
        ) from exc

    if number <= 0:
        raise ValueError(
            f"{field_name} must be greater than zero."
        )

    return number


def _parse_limit(
    value: Any,
    default: int = 20,
    maximum: int = 100,
) -> int:
    """Validate a query result limit."""

    if value is None:
        return default

    limit = _validate_positive_integer(
        value,
        "limit",
    )

    return min(limit, maximum)


def _error_response(
    message: str,
    status_code: int,
):
    """Return errors in one consistent JSON format."""

    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), status_code


# ============================================================
# GET EMPLOYEE ASSIGNMENTS
# ============================================================

@employee_bp.get(
    "/<int:employee_id>/assignments"
)
def get_assignments(
    employee_id: int,
):
    """
    Return the employee's cleanup assignments.

    Example:

    GET /api/employee/1/assignments
    """

    try:
        employee_id = _validate_positive_integer(
            employee_id,
            "employee_id",
        )

        limit = _parse_limit(
            request.args.get("limit"),
            default=50,
        )

        assignments = get_employee_assignments(
            employee_id=employee_id,
            limit=limit,
        )

        return jsonify(
            {
                "success": True,
                "count": len(assignments),
                "assignments": _json_safe_value(
                    assignments
                ),
            }
        ), 200

    except ValueError as exc:
        return _error_response(
            str(exc),
            400,
        )

    except Exception as exc:
        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# GENERATE EMPLOYEE RAG ADVICE
# ============================================================

@employee_bp.post(
    "/<int:employee_id>/advice"
)
def generate_employee_advice(
    employee_id: int,
):
    """
    Generate work instructions for an employee assignment.

    Example request:

    POST /api/employee/1/advice

    JSON body:

    {
        "assignment_id": 1,
        "language": "en"
    }
    """

    try:
        employee_id = _validate_positive_integer(
            employee_id,
            "employee_id",
        )

        payload = request.get_json(
            silent=True
        )

        if payload is None:
            raise ValueError(
                "A JSON request body is required."
            )

        if not isinstance(payload, dict):
            raise ValueError(
                "The JSON request body must be an object."
            )

        assignment_id = (
            _validate_positive_integer(
                payload.get("assignment_id"),
                "assignment_id",
            )
        )

        language = payload.get(
            "language",
            "en",
        )

        if not isinstance(language, str):
            raise ValueError(
                "language must be a string."
            )

        language = language.strip().lower()

        if language not in {
            "en",
            "bn",
        }:
            raise ValueError(
                "language must be 'en' or 'bn'."
            )

        if language == "bn":
            raise ValueError(
                "Bangla Employee guidance will be enabled "
                "during Gemini integration. Use 'en' for now."
            )

        result = generate_employee_advice_offline(
            employee_id=employee_id,
            assignment_id=assignment_id,
            response_language=language,
        )

        return jsonify(
            {
                "success": True,
                "message": (
                    "Employee work guidance was "
                    "generated successfully."
                ),
                **_json_safe_value(result),
            }
        ), 201

    except ValueError as exc:
        return _error_response(
            str(exc),
            400,
        )

    except TypeError as exc:
        return _error_response(
            str(exc),
            400,
        )

    except Exception as exc:
        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# GET EMPLOYEE ADVICE HISTORY
# ============================================================

@employee_bp.get(
    "/<int:employee_id>/advice-history"
)
def get_advice_history(
    employee_id: int,
):
    """
    Return saved Employee RAG advice.

    Example:

    GET /api/employee/1/advice-history
    """

    try:
        employee_id = _validate_positive_integer(
            employee_id,
            "employee_id",
        )

        limit = _parse_limit(
            request.args.get("limit"),
            default=20,
        )

        rows = get_employee_advice_history(
            employee_id=employee_id,
            limit=limit,
        )

        history: list[dict[str, Any]] = []

        for row_value in rows:
            row = dict(row_value)

            stored_response = row.pop(
                "response_json",
                None,
            )

            row["result"] = _parse_saved_json(
                stored_response
            )

            history.append(
                _json_safe_value(row)
            )

        return jsonify(
            {
                "success": True,
                "count": len(history),
                "history": history,
            }
        ), 200

    except ValueError as exc:
        return _error_response(
            str(exc),
            400,
        )

    except Exception as exc:
        return _error_response(
            str(exc),
            500,
        )


# ============================================================
# GET ONE EMPLOYEE ADVICE RECORD
# ============================================================

@employee_bp.get(
    "/<int:employee_id>/advice/<int:advice_id>"
)
def get_advice_by_id(
    employee_id: int,
    advice_id: int,
):
    """
    Return one Employee RAG result.

    It also confirms that the advice belongs
    to the selected employee.

    Example:

    GET /api/employee/1/advice/3
    """

    try:
        employee_id = _validate_positive_integer(
            employee_id,
            "employee_id",
        )

        advice_id = _validate_positive_integer(
            advice_id,
            "advice_id",
        )

        row = get_employee_advice_by_id(
            advice_id=advice_id,
            employee_id=employee_id,
        )

        if row is None:
            return _error_response(
                (
                    "Employee advice was not found, "
                    "or it does not belong to this employee."
                ),
                404,
            )

        advice = dict(row)

        stored_response = advice.pop(
            "response_json",
            None,
        )

        advice["result"] = _parse_saved_json(
            stored_response
        )

        return jsonify(
            {
                "success": True,
                "advice": _json_safe_value(
                    advice
                ),
            }
        ), 200

    except ValueError as exc:
        return _error_response(
            str(exc),
            400,
        )

    except Exception as exc:
        return _error_response(
            str(exc),
            500,
        )