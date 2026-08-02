import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request

from repositories.household_repository import (
    get_household_advice_by_id,
    get_household_advice_history,
)
from services.household_rag_service import (
    generate_household_advice_offline,
)


# ============================================================
# BLUEPRINT
# ============================================================

household_bp = Blueprint(
    "household",
    __name__,
    url_prefix="/api/household",
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def _json_safe_value(
    value: Any,
) -> Any:
    """
    Convert database values into JSON-safe values.

    Handles Decimal, date, datetime, dictionaries,
    lists and tuples.
    """

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
    """
    Convert stored MySQL JSON into a Python object.

    Depending on the database connector, JSON may be returned
    as a string, bytes, dictionary or list.
    """

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
    """Validate and return a positive integer."""

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
    """Validate the advice-history result limit."""

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
    """Return errors using one consistent JSON format."""

    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), status_code


# ============================================================
# GENERATE HOUSEHOLD ADVICE
# ============================================================

@household_bp.post(
    "/<int:user_id>/advice"
)
def generate_household_advice(
    user_id: int,
):
    """
    Generate Household RAG advice from a completed detection.

    Request:

    POST /api/household/2/advice

    JSON body:

    {
        "detection_session_id": 1,
        "language": "en"
    }
    """

    try:
        user_id = _validate_positive_integer(
            user_id,
            "user_id",
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

        detection_session_id = (
            _validate_positive_integer(
                payload.get(
                    "detection_session_id"
                ),
                "detection_session_id",
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

        # The offline formatter currently supports English.
        if language == "bn":
            raise ValueError(
                "Bangla household advice will be enabled "
                "during Gemini integration. Use 'en' for now."
            )

        result = generate_household_advice_offline(
            user_id=user_id,
            detection_session_id=(
                detection_session_id
            ),
            response_language=language,
        )

        return jsonify(
            {
                "success": True,
                "message": (
                    "Household waste guidance was "
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
# GET HOUSEHOLD ADVICE HISTORY
# ============================================================

@household_bp.get(
    "/<int:user_id>/advice-history"
)
def get_advice_history(
    user_id: int,
):
    """
    Return previously generated Household RAG advice.

    Example:

    GET /api/household/2/advice-history?limit=20
    """

    try:
        user_id = _validate_positive_integer(
            user_id,
            "user_id",
        )

        limit = _parse_limit(
            request.args.get("limit")
        )

        rows = get_household_advice_history(
            user_id=user_id,
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
# GET ONE HOUSEHOLD ADVICE RECORD
# ============================================================

@household_bp.get(
    "/<int:user_id>/advice/<int:advice_id>"
)
def get_advice_by_id(
    user_id: int,
    advice_id: int,
):
    """
    Return one Household RAG result.

    The query also confirms that the advice belongs
    to the supplied household user.

    Example:

    GET /api/household/2/advice/1
    """

    try:
        user_id = _validate_positive_integer(
            user_id,
            "user_id",
        )

        advice_id = _validate_positive_integer(
            advice_id,
            "advice_id",
        )

        row = get_household_advice_by_id(
            advice_id=advice_id,
            user_id=user_id,
        )

        if row is None:
            return _error_response(
                (
                    "Household advice was not found, "
                    "or it does not belong to this user."
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