import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request

from repositories.authority_repository import (
    get_authority_advice_history,
    get_authority_map_locations,
)
from services.analytics_service import (
    build_authority_analytics,
)
from services.authority_rag_service import (
    generate_authority_advice_offline,
)


# ============================================================
# BLUEPRINT
# ============================================================

authority_bp = Blueprint(
    "authority",
    __name__,
    url_prefix="/api/authority",
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def _json_safe_value(value: Any) -> Any:
    """
    Convert database values into JSON-safe values.

    Handles:
    - Decimal
    - date
    - datetime
    - dictionaries
    - lists
    - tuples
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


def _parse_date(
    value: Any,
    field_name: str,
) -> date:
    """
    Convert a YYYY-MM-DD value into a Python date.

    Raises a clear error when the value is missing or invalid.
    """

    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string in "
            "YYYY-MM-DD format."
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    try:
        return date.fromisoformat(value)

    except ValueError as exc:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc


def _validate_date_range(
    start_date: date,
    end_date: date,
) -> None:
    """Ensure the selected reporting period is valid."""

    if start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date."
        )


def _validate_authority_id(
    authority_id: int,
) -> None:
    """Ensure the authority ID is valid."""

    if authority_id <= 0:
        raise ValueError(
            "authority_id must be greater than zero."
        )


def _parse_limit(
    value: Any,
    default: int = 20,
    maximum: int = 100,
) -> int:
    """Parse and control the advice-history limit."""

    if value is None:
        return default

    try:
        limit = int(value)

    except (TypeError, ValueError) as exc:
        raise ValueError(
            "limit must be an integer."
        ) from exc

    if limit <= 0:
        raise ValueError(
            "limit must be greater than zero."
        )

    return min(
        limit,
        maximum,
    )


def _parse_saved_json(
    value: Any,
) -> Any:
    """
    Parse JSON stored in MySQL.

    Depending on the connector, a JSON column may be returned
    as a string, bytes, dictionary or list.
    """

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, bytes):
        value = value.decode(
            "utf-8"
        )

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)

    except json.JSONDecodeError:
        return value


def _error_response(
    message: str,
    status_code: int,
):
    """Create a consistent JSON error response."""

    return jsonify(
        {
            "success": False,
            "error": message,
        }
    ), status_code


# ============================================================
# GET AUTHORITY ANALYTICS
# ============================================================

@authority_bp.get(
    "/<int:authority_id>/analytics"
)
def get_authority_analytics(
    authority_id: int,
):
    """
    Return authority analytics for a selected period.

    Example:
    GET /api/authority/1/analytics
        ?start_date=2026-01-01
        &end_date=2026-12-31
    """

    try:
        _validate_authority_id(
            authority_id
        )

        start_date = _parse_date(
            request.args.get(
                "start_date"
            ),
            "start_date",
        )

        end_date = _parse_date(
            request.args.get(
                "end_date"
            ),
            "end_date",
        )

        _validate_date_range(
            start_date,
            end_date,
        )

        analytics = build_authority_analytics(
            authority_id=authority_id,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(
            {
                "success": True,
                "analytics": _json_safe_value(
                    analytics
                ),
            }
        ), 200

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
# GENERATE OFFLINE AUTHORITY ADVICE
# ============================================================

@authority_bp.post(
    "/<int:authority_id>/advice"
)
def generate_authority_advice(
    authority_id: int,
):
    """
    Run the complete offline Community Authority RAG pipeline.

    Expected JSON body:

    {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "language": "en"
    }
    """

    try:
        _validate_authority_id(
            authority_id
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

        start_date = _parse_date(
            payload.get(
                "start_date"
            ),
            "start_date",
        )

        end_date = _parse_date(
            payload.get(
                "end_date"
            ),
            "end_date",
        )

        _validate_date_range(
            start_date,
            end_date,
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

        result = generate_authority_advice_offline(
            authority_id=authority_id,
            start_date=start_date,
            end_date=end_date,
            response_language=language,
        )

        return jsonify(
            {
                "success": True,
                "message": (
                    "Community Authority advice was "
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
# GET ADVICE HISTORY
# ============================================================

@authority_bp.get(
    "/<int:authority_id>/advice-history"
)
def get_advice_history(
    authority_id: int,
):
    """
    Return previously generated advice runs.

    Example:
    GET /api/authority/1/advice-history?limit=20
    """

    try:
        _validate_authority_id(
            authority_id
        )

        limit = _parse_limit(
            request.args.get(
                "limit"
            )
        )

        rows = get_authority_advice_history(
            authority_id=authority_id,
            limit=limit,
        )

        history: list[dict[str, Any]] = []

        for row in rows:
            history_item = dict(row)

            raw_recommendations = (
                history_item.pop(
                    "recommendations_json",
                    None,
                )
            )

            history_item["result"] = (
                _parse_saved_json(
                    raw_recommendations
                )
            )

            limitations_text = (
                history_item.get(
                    "limitations_text"
                )
            )

            if isinstance(
                limitations_text,
                str,
            ):
                history_item["limitations"] = [
                    line.strip()
                    for line in (
                        limitations_text.splitlines()
                    )
                    if line.strip()
                ]

            else:
                history_item[
                    "limitations"
                ] = []

            history.append(
                _json_safe_value(
                    history_item
                )
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
# GET AUTHORITY MAP LOCATIONS
# ============================================================

@authority_bp.get(
    "/<int:authority_id>/map-locations"
)
def get_map_locations(
    authority_id: int,
):
    """
    Return report and assignment locations for the map.

    Example:
    GET /api/authority/1/map-locations
    """

    try:
        _validate_authority_id(
            authority_id
        )

        locations = (
            get_authority_map_locations(
                authority_id=authority_id
            )
        )

        safe_locations = (
            _json_safe_value(
                locations
            )
        )

        return jsonify(
            {
                "success": True,
                "count": len(
                    safe_locations
                ),
                "locations": safe_locations,
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