from datetime import date
from decimal import Decimal
from typing import Any

from repositories.authority_repository import (
    get_assignment_metrics,
    get_authority_scope,
    get_cleanup_category_breakdown,
    get_cleanup_metrics,
    get_report_metrics,
)


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert MySQL numeric values into Python floats."""

    if value is None:
        return default

    if isinstance(value, Decimal):
        return float(value)

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _to_int(
    value: Any,
    default: int = 0,
) -> int:
    """Safely convert MySQL numeric values into Python integers."""

    if value is None:
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


def _percentage(
    numerator: float,
    denominator: float,
) -> float:
    """
    Calculate a percentage safely.

    Returns zero when the denominator is zero.
    """

    if denominator <= 0:
        return 0.0

    return round(
        (numerator / denominator) * 100,
        2,
    )


def _normalise_category_breakdown(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert category weight values into JSON-safe numbers."""

    normalised_rows: list[dict[str, Any]] = []

    for row in rows:
        normalised_rows.append(
            {
                "category_id": _to_int(
                    row.get("category_id")
                ),
                "category_code": row.get(
                    "category_code"
                ),
                "category_name": row.get(
                    "category_name"
                ),
                "weight_kg": round(
                    _to_float(row.get("weight_kg")),
                    2,
                ),
            }
        )

    return normalised_rows


def _calculate_data_quality(
    scope: dict[str, Any],
    report_metrics: dict[str, Any],
    assignment_metrics: dict[str, Any],
    cleanup_metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate basic analytics-data completeness.

    This checks whether the required database queries returned
    the important fields needed by the authority RAG system.
    """

    checks = [
        scope.get("authority_id") is not None,
        scope.get("authority_user_id") is not None,
        scope.get("region_id") is not None,
        bool(scope.get("authority_name")),
        bool(scope.get("region_name")),

        report_metrics.get("submitted_reports") is not None,
        report_metrics.get("unresolved_reports") is not None,
        report_metrics.get("completed_reports") is not None,
        report_metrics.get("critical_open_reports") is not None,
        report_metrics.get("high_open_reports") is not None,

        assignment_metrics.get("active_assignments") is not None,
        assignment_metrics.get("completed_assignments") is not None,
        assignment_metrics.get("overdue_assignments") is not None,
        assignment_metrics.get("active_employee_count") is not None,

        cleanup_metrics.get(
            "total_waste_collected_kg"
        ) is not None,
        cleanup_metrics.get(
            "recycled_waste_kg"
        ) is not None,
        cleanup_metrics.get(
            "composted_waste_kg"
        ) is not None,
        cleanup_metrics.get(
            "properly_disposed_kg"
        ) is not None,
        cleanup_metrics.get(
            "hazardous_waste_kg"
        ) is not None,
    ]

    completed_checks = sum(
        1 for check in checks if check
    )

    completeness_percent = round(
        (completed_checks / len(checks)) * 100,
        2,
    )

    if completeness_percent >= 80:
        status = "complete"

    elif completeness_percent >= 50:
        status = "partial"

    else:
        status = "insufficient"

    return {
        "completeness_percent": completeness_percent,
        "status": status,
    }


def build_authority_analytics(
    authority_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Build analytics for one approved Community-Based Authority.

    The result is used by:
    - the authority dashboard;
    - the rule engine;
    - the authority retriever;
    - the offline RAG service;
    - Gemini later.
    """

    if not isinstance(authority_id, int):
        raise TypeError(
            "authority_id must be an integer."
        )

    if authority_id <= 0:
        raise ValueError(
            "authority_id must be greater than zero."
        )

    if not isinstance(start_date, date):
        raise TypeError(
            "start_date must be a date object."
        )

    if not isinstance(end_date, date):
        raise TypeError(
            "end_date must be a date object."
        )

    if start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date."
        )

    scope_row = get_authority_scope(
        authority_id
    )

    if scope_row is None:
        raise ValueError(
            "Approved community authority was not found."
        )

    report_metrics = get_report_metrics(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
    )

    assignment_metrics = get_assignment_metrics(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
    )

    cleanup_metrics = get_cleanup_metrics(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
    )

    category_rows = get_cleanup_category_breakdown(
        authority_id=authority_id,
        start_date=start_date,
        end_date=end_date,
    )

    submitted_reports = _to_int(
        report_metrics.get("submitted_reports")
    )

    unresolved_reports = _to_int(
        report_metrics.get("unresolved_reports")
    )

    completed_reports = _to_int(
        report_metrics.get("completed_reports")
    )

    rejected_reports = _to_int(
        report_metrics.get("rejected_reports")
    )

    critical_open_reports = _to_int(
        report_metrics.get(
            "critical_open_reports"
        )
    )

    high_open_reports = _to_int(
        report_metrics.get(
            "high_open_reports"
        )
    )

    average_resolution_hours = round(
        _to_float(
            report_metrics.get(
                "average_resolution_hours"
            )
        ),
        2,
    )

    active_assignments = _to_int(
        assignment_metrics.get(
            "active_assignments"
        )
    )

    completed_assignments = _to_int(
        assignment_metrics.get(
            "completed_assignments"
        )
    )

    overdue_assignments = _to_int(
        assignment_metrics.get(
            "overdue_assignments"
        )
    )

    active_employee_count = _to_int(
        assignment_metrics.get(
            "active_employee_count"
        )
    )

    total_waste_collected_kg = round(
        _to_float(
            cleanup_metrics.get(
                "total_waste_collected_kg"
            )
        ),
        2,
    )

    recycled_waste_kg = round(
        _to_float(
            cleanup_metrics.get(
                "recycled_waste_kg"
            )
        ),
        2,
    )

    composted_waste_kg = round(
        _to_float(
            cleanup_metrics.get(
                "composted_waste_kg"
            )
        ),
        2,
    )

    properly_disposed_kg = round(
        _to_float(
            cleanup_metrics.get(
                "properly_disposed_kg"
            )
        ),
        2,
    )

    hazardous_waste_kg = round(
        _to_float(
            cleanup_metrics.get(
                "hazardous_waste_kg"
            )
        ),
        2,
    )

    estimated_co2_reduction_kg = round(
        _to_float(
            cleanup_metrics.get(
                "estimated_co2_reduction_kg"
            )
        ),
        2,
    )

    total_assignments = (
        active_assignments
        + completed_assignments
    )

    report_completion_rate = _percentage(
        completed_reports,
        submitted_reports,
    )

    unresolved_report_rate = _percentage(
        unresolved_reports,
        submitted_reports,
    )

    recycling_share = _percentage(
        recycled_waste_kg,
        total_waste_collected_kg,
    )

    compostable_share = _percentage(
        composted_waste_kg,
        total_waste_collected_kg,
    )

    hazardous_share = _percentage(
        hazardous_waste_kg,
        total_waste_collected_kg,
    )

    overdue_assignment_rate = _percentage(
        overdue_assignments,
        total_assignments,
    )

    data_quality = _calculate_data_quality(
        scope=scope_row,
        report_metrics=report_metrics,
        assignment_metrics=assignment_metrics,
        cleanup_metrics=cleanup_metrics,
    )

    scope = {
        "authority_id": _to_int(
            scope_row.get("authority_id")
        ),
        "authority_user_id": _to_int(
            scope_row.get("authority_user_id")
        ),
        "authority_name": scope_row.get(
            "authority_name"
        ),
        "organization_name": scope_row.get(
            "organization_name"
        ),
        "region_id": _to_int(
            scope_row.get("region_id")
        ),
        "region_name": scope_row.get(
            "region_name"
        ),
        "region_type": scope_row.get(
            "region_type"
        ),
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
    }

    reports = {
        "submitted": submitted_reports,
        "unresolved": unresolved_reports,
        "completed": completed_reports,
        "rejected": rejected_reports,
        "critical_open": critical_open_reports,
        "high_open": high_open_reports,
        "average_resolution_hours": (
            average_resolution_hours
        ),
    }

    assignments = {
        "active": active_assignments,
        "completed": completed_assignments,
        "overdue": overdue_assignments,
        "active_employees": active_employee_count,
    }

    waste = {
        "total_collected_kg": (
            total_waste_collected_kg
        ),
        "recycled_kg": recycled_waste_kg,
        "composted_kg": composted_waste_kg,
        "properly_disposed_kg": (
            properly_disposed_kg
        ),
        "hazardous_kg": hazardous_waste_kg,
        "estimated_co2_reduction_kg": (
            estimated_co2_reduction_kg
        ),
        "category_breakdown": (
            _normalise_category_breakdown(
                category_rows
            )
        ),
    }

    indicators = {
        "report_completion_rate_percent": (
            report_completion_rate
        ),
        "unresolved_report_rate_percent": (
            unresolved_report_rate
        ),
        "recycling_share_percent": (
            recycling_share
        ),
        "compostable_share_percent": (
            compostable_share
        ),
        "hazardous_share_percent": (
            hazardous_share
        ),
        "overdue_assignment_rate_percent": (
            overdue_assignment_rate
        ),
        "data_completeness_percent": (
            data_quality["completeness_percent"]
        ),
    }

    return {
        "scope": scope,
        "reports": reports,
        "assignments": assignments,
        "waste": waste,
        "indicators": indicators,
        "data_quality": data_quality,
    }