import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from db import execute, fetch_all, fetch_one


# ============================================================
# AUTHORITY INFORMATION
# ============================================================

def get_authority_scope(
    authority_id: int,
) -> dict[str, Any] | None:
    """
    Return the approved authority account and assigned region.

    The authority_user_id is needed when an advice run is saved,
    because authority_advice_runs requires requested_by_user_id.
    """

    return fetch_one(
        """
        SELECT
            ca.authority_id,
            ca.user_id AS authority_user_id,
            ca.assigned_region_id AS region_id,
            u.full_name AS authority_name,
            ca.organization_name,
            r.region_name,
            r.region_type

        FROM community_authorities AS ca

        JOIN users AS u
            ON u.user_id = ca.user_id

        JOIN regions AS r
            ON r.region_id = ca.assigned_region_id

        WHERE ca.authority_id = %s
          AND ca.approval_status = 'approved'
        """,
        (authority_id,),
    )


# ============================================================
# REPORT ANALYTICS
# ============================================================

def get_report_metrics(
    authority_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Calculate citizen-report statistics for a selected period."""

    result = fetch_one(
        """
        SELECT
            COUNT(*) AS submitted_reports,

            SUM(
                CASE
                    WHEN report_status IN (
                        'submitted',
                        'under_review',
                        'assigned',
                        'in_progress'
                    )
                    THEN 1
                    ELSE 0
                END
            ) AS unresolved_reports,

            SUM(
                CASE
                    WHEN report_status = 'completed'
                    THEN 1
                    ELSE 0
                END
            ) AS completed_reports,

            SUM(
                CASE
                    WHEN report_status = 'rejected'
                    THEN 1
                    ELSE 0
                END
            ) AS rejected_reports,

            SUM(
                CASE
                    WHEN report_status IN (
                        'submitted',
                        'under_review',
                        'assigned',
                        'in_progress'
                    )
                    AND estimated_severity = 'critical'
                    THEN 1
                    ELSE 0
                END
            ) AS critical_open_reports,

            SUM(
                CASE
                    WHEN report_status IN (
                        'submitted',
                        'under_review',
                        'assigned',
                        'in_progress'
                    )
                    AND estimated_severity = 'high'
                    THEN 1
                    ELSE 0
                END
            ) AS high_open_reports,

            AVG(
                CASE
                    WHEN report_status = 'completed'
                         AND completed_at IS NOT NULL
                    THEN TIMESTAMPDIFF(
                        HOUR,
                        submitted_at,
                        completed_at
                    )
                END
            ) AS average_resolution_hours

        FROM waste_reports

        WHERE authority_id = %s
          AND DATE(submitted_at) BETWEEN %s AND %s
        """,
        (
            authority_id,
            start_date,
            end_date,
        ),
    )

    return result or {}


# ============================================================
# EMPLOYEE AND ASSIGNMENT ANALYTICS
# ============================================================

def get_assignment_metrics(
    authority_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Calculate employee and task statistics.

    An assignment is overdue when:
    - due_at has passed;
    - the task has not been completed or cancelled.
    """

    result = fetch_one(
        """
        SELECT
            COUNT(
                DISTINCT CASE
                    WHEN ta.assignment_status IN (
                        'assigned',
                        'accepted',
                        'in_progress'
                    )
                    THEN ta.assignment_id
                END
            ) AS active_assignments,

            COUNT(
                DISTINCT CASE
                    WHEN ta.assignment_status = 'completed'
                    THEN ta.assignment_id
                END
            ) AS completed_assignments,

            COUNT(
                DISTINCT CASE
                    WHEN ta.due_at IS NOT NULL
                         AND ta.due_at < NOW()
                         AND ta.assignment_status IN (
                             'assigned',
                             'accepted',
                             'in_progress'
                         )
                    THEN ta.assignment_id
                END
            ) AS overdue_assignments,

            COUNT(
                DISTINCT e.employee_id
            ) AS active_employee_count

        FROM employees AS e

        LEFT JOIN task_assignments AS ta
            ON ta.employee_id = e.employee_id
           AND DATE(ta.assigned_at) BETWEEN %s AND %s

        WHERE e.authority_id = %s
          AND e.employment_status = 'active'
        """,
        (
            start_date,
            end_date,
            authority_id,
        ),
    )

    return result or {}


# ============================================================
# CLEANUP ANALYTICS
# ============================================================

def get_cleanup_metrics(
    authority_id: int,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Return verified cleanup totals for this authority.

    The per-class breakdown is the canonical source for handling totals
    because it is what the Employee completion workflow writes. Older
    verified cleanup records without a class breakdown fall back to the
    summary values stored on cleanup_records.
    """

    result = fetch_one(
        """
        SELECT
            COALESCE(
                SUM(
                    CASE
                        WHEN cb.cleanup_id IS NOT NULL
                            THEN cb.total_waste_kg
                        ELSE cr.total_waste_kg
                    END
                ),
                0
            ) AS total_waste_collected_kg,

            COALESCE(
                SUM(
                    CASE
                        WHEN cb.cleanup_id IS NOT NULL
                            THEN cb.recycled_waste_kg
                        ELSE cr.recycled_waste_kg
                    END
                ),
                0
            ) AS recycled_waste_kg,

            COALESCE(
                SUM(
                    CASE
                        WHEN cb.cleanup_id IS NOT NULL
                            THEN cb.composted_waste_kg
                        ELSE cr.composted_waste_kg
                    END
                ),
                0
            ) AS composted_waste_kg,

            COALESCE(
                SUM(
                    CASE
                        WHEN cb.cleanup_id IS NOT NULL
                            THEN cb.properly_disposed_kg
                        ELSE cr.properly_disposed_kg
                    END
                ),
                0
            ) AS properly_disposed_kg,

            COALESCE(
                SUM(
                    CASE
                        WHEN cb.cleanup_id IS NOT NULL
                            THEN cb.hazardous_waste_kg
                        ELSE cr.hazardous_waste_kg
                    END
                ),
                0
            ) AS hazardous_waste_kg,

            COALESCE(
                SUM(cr.estimated_co2_reduction_kg),
                0
            ) AS estimated_co2_reduction_kg

        FROM cleanup_records AS cr

        JOIN task_assignments AS ta
            ON ta.assignment_id = cr.assignment_id

        LEFT JOIN (
            SELECT
                ccb.cleanup_id,

                SUM(ccb.weight_kg)
                    AS total_waste_kg,

                SUM(
                    CASE
                        WHEN ccb.handling_method = 'recycled'
                            THEN ccb.weight_kg
                        ELSE 0
                    END
                ) AS recycled_waste_kg,

                SUM(
                    CASE
                        WHEN ccb.handling_method = 'composted'
                            THEN ccb.weight_kg
                        ELSE 0
                    END
                ) AS composted_waste_kg,

                SUM(
                    CASE
                        WHEN ccb.handling_method IN (
                            'special_collection',
                            'controlled_disposal'
                        )
                            THEN ccb.weight_kg
                        ELSE 0
                    END
                ) AS properly_disposed_kg,

                SUM(
                    CASE
                        WHEN wc.category_code = 'HAZARDOUS'
                            THEN ccb.weight_kg
                        ELSE 0
                    END
                ) AS hazardous_waste_kg

            FROM cleanup_class_breakdown AS ccb

            JOIN waste_categories AS wc
                ON wc.category_id = ccb.category_id

            GROUP BY ccb.cleanup_id
        ) AS cb
            ON cb.cleanup_id = cr.cleanup_id

        WHERE ta.assigned_by_authority_id = %s
          AND cr.verification_status = 'verified'
          AND DATE(cr.cleaned_at) BETWEEN %s AND %s
        """,
        (
            authority_id,
            start_date,
            end_date,
        ),
    )

    return result or {}

def get_cleanup_category_breakdown(
    authority_id: int,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """
    Return verified collected weight grouped by broad category.

    Examples:
    - Compostable Waste
    - E-Waste
    - Recyclable Plastic
    """

    return fetch_all(
        """
        SELECT
            wc.category_id,
            wc.category_code,
            wc.category_name,
            COALESCE(
                SUM(ccb.weight_kg),
                0
            ) AS weight_kg

        FROM cleanup_class_breakdown AS ccb

        JOIN cleanup_records AS cr
            ON cr.cleanup_id = ccb.cleanup_id

        JOIN task_assignments AS ta
            ON ta.assignment_id = cr.assignment_id

        JOIN waste_categories AS wc
            ON wc.category_id = ccb.category_id

        WHERE ta.assigned_by_authority_id = %s
          AND cr.verification_status = 'verified'
          AND DATE(cr.cleaned_at) BETWEEN %s AND %s

        GROUP BY
            wc.category_id,
            wc.category_code,
            wc.category_name

        ORDER BY weight_kg DESC
        """,
        (
            authority_id,
            start_date,
            end_date,
        ),
    )


# ============================================================
# AUTHORITY ADVICE RULES
# ============================================================

def get_active_advice_rules() -> list[dict[str, Any]]:
    """
    Return active and transparent analytics rules.

    These rules are evaluated before RAG retrieval or Gemini.
    """

    return fetch_all(
        """
        SELECT
            advice_rule_id,
            rule_code,
            title,
            indicator_code,
            comparison_operator,
            threshold_value_1,
            threshold_value_2,
            minimum_sample_size,
            advice_category,
            priority,
            recommendation_template,
            rationale_template,
            requires_human_review

        FROM authority_advice_rules

        WHERE is_active = 1

        ORDER BY
            FIELD(
                priority,
                'critical',
                'high',
                'medium',
                'low'
            ),
            advice_rule_id
        """
    )


# ============================================================
# ANALYTICS SNAPSHOT STORAGE
# ============================================================

def save_analytics_snapshot(
    analytics: dict[str, Any],
    period_type: str = "custom",
) -> int:
    """
    Save or update analytics for one authority and period.

    The unique authority/region/period combination prevents
    duplicate snapshots for the same selected date range.
    """

    allowed_period_types = {
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "yearly",
        "custom",
    }

    if period_type not in allowed_period_types:
        raise ValueError(
            f"Unsupported period_type: {period_type}"
        )

    scope = analytics["scope"]
    reports = analytics["reports"]
    assignments = analytics["assignments"]
    waste = analytics["waste"]
    data_quality = analytics["data_quality"]

    snapshot_id = execute(
        """
        INSERT INTO authority_analytics_snapshots (
            authority_id,
            region_id,
            period_type,
            period_start,
            period_end,

            submitted_reports,
            unresolved_reports,
            completed_reports,
            critical_open_reports,
            high_open_reports,
            average_resolution_hours,

            total_waste_collected_kg,
            recycled_waste_kg,
            composted_waste_kg,
            properly_disposed_kg,
            hazardous_waste_kg,
            estimated_co2_reduction_kg,

            active_employee_count,
            completed_assignment_count,
            overdue_assignment_count,

            data_completeness_percent
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s
        )

        ON DUPLICATE KEY UPDATE
            snapshot_id = LAST_INSERT_ID(snapshot_id),

            submitted_reports =
                VALUES(submitted_reports),

            unresolved_reports =
                VALUES(unresolved_reports),

            completed_reports =
                VALUES(completed_reports),

            critical_open_reports =
                VALUES(critical_open_reports),

            high_open_reports =
                VALUES(high_open_reports),

            average_resolution_hours =
                VALUES(average_resolution_hours),

            total_waste_collected_kg =
                VALUES(total_waste_collected_kg),

            recycled_waste_kg =
                VALUES(recycled_waste_kg),

            composted_waste_kg =
                VALUES(composted_waste_kg),

            properly_disposed_kg =
                VALUES(properly_disposed_kg),

            hazardous_waste_kg =
                VALUES(hazardous_waste_kg),

            estimated_co2_reduction_kg =
                VALUES(estimated_co2_reduction_kg),

            active_employee_count =
                VALUES(active_employee_count),

            completed_assignment_count =
                VALUES(completed_assignment_count),

            overdue_assignment_count =
                VALUES(overdue_assignment_count),

            data_completeness_percent =
                VALUES(data_completeness_percent),

            calculated_at = CURRENT_TIMESTAMP
        """,
        (
            scope["authority_id"],
            scope["region_id"],
            period_type,
            scope["period_start"],
            scope["period_end"],

            reports["submitted"],
            reports["unresolved"],
            reports["completed"],
            reports["critical_open"],
            reports["high_open"],
            reports["average_resolution_hours"],

            waste["total_collected_kg"],
            waste["recycled_kg"],
            waste["composted_kg"],
            waste["properly_disposed_kg"],
            waste["hazardous_kg"],
            waste.get("estimated_co2_reduction_kg"),

            assignments["active_employees"],
            assignments["completed"],
            assignments["overdue"],

            data_quality["completeness_percent"],
        ),
    )

    if snapshot_id:
        return snapshot_id

    # Safety fallback in case the connector does not return
    # LAST_INSERT_ID() after an upsert.
    existing = fetch_one(
        """
        SELECT snapshot_id

        FROM authority_analytics_snapshots

        WHERE authority_id = %s
          AND region_id = %s
          AND period_type = %s
          AND period_start = %s
          AND period_end = %s
        """,
        (
            scope["authority_id"],
            scope["region_id"],
            period_type,
            scope["period_start"],
            scope["period_end"],
        ),
    )

    if existing is None:
        raise RuntimeError(
            "The analytics snapshot could not be saved."
        )

    return int(existing["snapshot_id"])


# ============================================================
# AUTHORITY ADVICE-RUN STORAGE
# ============================================================

def create_authority_advice_run(
    authority_id: int,
    region_id: int,
    snapshot_id: int,
    request_uuid: str,
    requested_by_user_id: int,
    response_language: str = "en",
    gemini_model: str | None = None,
    prompt_version: str = "offline-rule-based-1.0",
) -> int:
    """
    Create a new advice-run record.

    Offline callers can use the defaults unchanged. Gemini callers
    can record the exact model and prompt version used for the run.
    """

    advice_run_id = execute(
        """
        INSERT INTO authority_advice_runs (
            authority_id,
            region_id,
            snapshot_id,
            request_uuid,
            requested_by_user_id,
            advice_status,
            gemini_model,
            prompt_version,
            response_language
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            'processing',
            %s,
            %s,
            %s
        )
        """,
        (
            authority_id,
            region_id,
            snapshot_id,
            request_uuid,
            requested_by_user_id,
            gemini_model,
            prompt_version,
            response_language,
        ),
    )

    if not advice_run_id:
        raise RuntimeError(
            "The authority advice run could not be created."
        )

    return advice_run_id


def _json_default(value: Any) -> Any:
    """
    Convert database-specific values into JSON-safe values.

    This handles Decimal, date and datetime values.
    """

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def complete_authority_advice_run(
    advice_run_id: int,
    executive_summary: str,
    advice_response: dict[str, Any],
    limitations: list[str],
) -> None:
    """
    Save the completed offline-grounded recommendation.

    The result remains marked needs_human_review because an
    authority must review operational or infrastructure advice.
    """

    execute(
        """
        UPDATE authority_advice_runs

        SET
            advice_status = 'needs_human_review',
            executive_summary = %s,
            recommendations_json = %s,
            limitations_text = %s,
            error_message = NULL

        WHERE advice_run_id = %s
        """,
        (
            executive_summary,
            json.dumps(
                advice_response,
                ensure_ascii=False,
                default=_json_default,
            ),
            "\n".join(
                dict.fromkeys(limitations)
            ),
            advice_run_id,
        ),
    )


def fail_authority_advice_run(
    advice_run_id: int,
    error_message: str,
) -> None:
    """Mark an authority advice run as failed."""

    execute(
        """
        UPDATE authority_advice_runs

        SET
            advice_status = 'failed',
            error_message = %s

        WHERE advice_run_id = %s
        """,
        (
            error_message,
            advice_run_id,
        ),
    )


# ============================================================
# ADVICE AUDIT LINKS
# ============================================================

def save_authority_rule_links(
    advice_run_id: int,
    triggered_rules: list[dict[str, Any]],
) -> None:
    """
    Store every analytics rule used in an advice run.

    This explains why each recommendation was generated.
    """

    for rule in triggered_rules:
        trigger_explanation = (
            f"{rule['indicator_code']} was "
            f"{rule['trigger_value']}. "
            f"{rule['rationale']}"
        )

        execute(
            """
            INSERT INTO authority_advice_rule_links (
                advice_run_id,
                advice_rule_id,
                trigger_value,
                trigger_explanation
            )
            VALUES (
                %s,
                %s,
                %s,
                %s
            )

            ON DUPLICATE KEY UPDATE
                trigger_value =
                    VALUES(trigger_value),

                trigger_explanation =
                    VALUES(trigger_explanation)
            """,
            (
                advice_run_id,
                rule["advice_rule_id"],
                rule["trigger_value"],
                trigger_explanation,
            ),
        )


def save_authority_knowledge_links(
    advice_run_id: int,
    knowledge_rows: list[dict[str, Any]],
    exact_region_id: int,
) -> None:
    """
    Save the verified authority knowledge used in an advice run.

    The method records whether the information was:
    - specific to the authority's region; or
    - national Bangladesh fallback knowledge.
    """

    for rank, knowledge in enumerate(
        knowledge_rows,
        start=1,
    ):
        knowledge_region_id = knowledge.get("region_id")

        retrieval_method = (
            "exact_region_and_topic"
            if knowledge_region_id == exact_region_id
            else "national_topic_fallback"
        )

        execute(
            """
            INSERT INTO
                authority_advice_authority_knowledge_links (
                    advice_run_id,
                    authority_knowledge_id,
                    retrieval_rank,
                    retrieval_method,
                    retrieval_reason
                )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s
            )

            ON DUPLICATE KEY UPDATE
                retrieval_rank =
                    VALUES(retrieval_rank),

                retrieval_method =
                    VALUES(retrieval_method),

                retrieval_reason =
                    VALUES(retrieval_reason)
            """,
            (
                advice_run_id,
                knowledge["authority_knowledge_id"],
                rank,
                retrieval_method,
                (
                    "Retrieved for authority topic: "
                    f"{knowledge['topic_code']}."
                ),
            ),
        )


# ============================================================
# ADVICE HISTORY
# ============================================================

def get_authority_advice_history(
    authority_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return previously generated authority advice records."""

    safe_limit = min(
        max(int(limit), 1),
        100,
    )

    return fetch_all(
        """
        SELECT
            advice_run_id,
            authority_id,
            region_id,
            snapshot_id,
            request_uuid,
            advice_status,
            gemini_model,
            prompt_version,
            response_language,
            executive_summary,
            recommendations_json,
            limitations_text,
            error_message,
            generated_at,
            reviewed_by_user_id,
            reviewed_at

        FROM authority_advice_runs

        WHERE authority_id = %s

        ORDER BY generated_at DESC

        LIMIT %s
        """,
        (
            authority_id,
            safe_limit,
        ),
    )


# ============================================================
# AUTHORITY PROMPT TEMPLATE
# ============================================================

def get_active_authority_prompt_template(
    language_code: str = "en",
) -> dict[str, Any] | None:
    """Return the newest active Authority system prompt template.

    The database currently stores the Authority prompt as an English
    system prompt. If a requested language-specific row is unavailable,
    callers can fall back to the active English template.
    """

    language_code = str(language_code or "en").strip().lower()

    row = fetch_one(
        """
        SELECT
            prompt_template_id,
            template_name,
            template_version,
            language_code,
            system_prompt,
            is_active,
            created_at

        FROM authority_prompt_templates

        WHERE is_active = 1
          AND language_code = %s

        ORDER BY created_at DESC, prompt_template_id DESC
        LIMIT 1
        """,
        (language_code,),
    )

    if row is not None or language_code == "en":
        return row

    return fetch_one(
        """
        SELECT
            prompt_template_id,
            template_name,
            template_version,
            language_code,
            system_prompt,
            is_active,
            created_at

        FROM authority_prompt_templates

        WHERE is_active = 1
          AND language_code = 'en'

        ORDER BY created_at DESC, prompt_template_id DESC
        LIMIT 1
        """
    )


# ============================================================
# GOOGLE MAP LOCATIONS
# ============================================================

def get_authority_map_locations(
    authority_id: int,
) -> list[dict[str, Any]]:
    """
    Return complaints and assigned cleaning locations.

    The Flask API will later send these coordinates to React
    for the Google Maps interface.
    """

    return fetch_all(
        """
        SELECT
            authority_id,
            report_id,
            title,
            description,
            address_text,
            latitude,
            longitude,
            estimated_severity,
            report_status,
            submitted_at,
            assignment_id,
            assignment_status,
            assignment_priority,
            employee_id,
            employee_name

        FROM v_authority_map_locations

        WHERE authority_id = %s

        ORDER BY submitted_at DESC
        """,
        (authority_id,),
    )


# ============================================================
# VERIFIED FACILITIES
# ============================================================

def get_verified_facilities(
    region_id: int,
) -> list[dict[str, Any]]:
    """
    Return verified facilities for the authority's region.

    Unverified or inactive facilities are blocked by the view.
    """

    return fetch_all(
        """
        SELECT *

        FROM v_verified_disposal_facilities

        WHERE region_id = %s

        ORDER BY facility_name
        """,
        (region_id,),
    )