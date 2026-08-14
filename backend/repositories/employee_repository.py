import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from db import execute, fetch_all, fetch_one


# ============================================================
# JSON HELPER
# ============================================================

def _json_default(value: Any) -> Any:
    """Convert MySQL values into JSON-safe values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


# ============================================================
# EMPLOYEE ACCOUNT AND SCOPE
# ============================================================

def get_employee_scope(
    employee_id: int,
) -> dict[str, Any] | None:
    """
    Return an active employee, their authority,
    and their registered region.
    """

    return fetch_one(
        """
        SELECT
            e.employee_id,
            e.user_id,
            e.authority_id,
            e.employee_code,
            e.job_title,
            e.employment_status,

            u.full_name AS employee_name,
            u.email,
            u.phone,
            u.region_id,

            ca.organization_name,
            ca.approval_status
                AS authority_approval_status,

            r.region_name,
            r.region_type

        FROM employees AS e

        JOIN users AS u
            ON u.user_id = e.user_id

        JOIN community_authorities AS ca
            ON ca.authority_id = e.authority_id

        LEFT JOIN regions AS r
            ON r.region_id = u.region_id

        WHERE e.employee_id = %s
          AND e.employment_status = 'active'
          AND u.account_status = 'active'
          AND ca.approval_status = 'approved'

        LIMIT 1
        """,
        (employee_id,),
    )


# ============================================================
# EMPLOYEE ASSIGNMENTS
# ============================================================

def get_employee_assignment(
    assignment_id: int,
    employee_id: int,
) -> dict[str, Any] | None:
    """
    Return one assignment belonging to the employee.
    """

    return fetch_one(
        """
        SELECT
            ta.assignment_id,
            ta.report_id,
            ta.employee_id,
            ta.assigned_by_authority_id,
            ta.assignment_notes,
            ta.priority AS assignment_priority,
            ta.assignment_status,
            ta.assigned_at,
            ta.due_at,
            ta.accepted_at,
            ta.started_at,
            ta.completed_at,

            wr.title AS report_title,
            wr.description AS report_description,
            wr.address_text,
            wr.latitude,
            wr.longitude,
            wr.estimated_severity,
            wr.report_status,
            wr.submitted_at,

            e.employee_code,
            u.full_name AS employee_name,

            ca.organization_name,

            r.region_id,
            r.region_name,
            r.region_type

        FROM task_assignments AS ta

        JOIN waste_reports AS wr
            ON wr.report_id = ta.report_id

        JOIN employees AS e
            ON e.employee_id = ta.employee_id

        JOIN users AS u
            ON u.user_id = e.user_id

        JOIN community_authorities AS ca
            ON ca.authority_id =
               ta.assigned_by_authority_id

        JOIN regions AS r
            ON r.region_id = wr.region_id

        WHERE ta.assignment_id = %s
          AND ta.employee_id = %s
          AND ta.assignment_status IN (
              'assigned',
              'accepted',
              'in_progress',
              'completed'
          )

        LIMIT 1
        """,
        (
            assignment_id,
            employee_id,
        ),
    )


def get_employee_assignments(
    employee_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return the employee's latest assignments."""

    safe_limit = min(
        max(int(limit), 1),
        100,
    )

    return fetch_all(
        """
        SELECT
            ta.assignment_id,
            ta.report_id,
            ta.assignment_notes,
            ta.priority AS assignment_priority,
            ta.assignment_status,
            ta.assigned_at,
            ta.due_at,
            ta.completed_at,

            wr.title AS report_title,
            wr.address_text,
            wr.latitude,
            wr.longitude,
            wr.estimated_severity,
            wr.report_status,

            r.region_id,
            r.region_name,
            r.region_type

        FROM task_assignments AS ta

        JOIN waste_reports AS wr
            ON wr.report_id = ta.report_id

        JOIN regions AS r
            ON r.region_id = wr.region_id

        WHERE ta.employee_id = %s

        ORDER BY
            FIELD(
                ta.assignment_status,
                'in_progress',
                'accepted',
                'assigned',
                'completed',
                'cancelled'
            ),

            FIELD(
                ta.priority,
                'urgent',
                'high',
                'medium',
                'low'
            ),

            ta.assigned_at DESC

        LIMIT %s
        """,
        (
            employee_id,
            safe_limit,
        ),
    )


# ============================================================
# ASSIGNMENT DETECTION SESSION
# ============================================================

def get_assignment_detection_session(
    assignment_id: int,
    employee_id: int,
) -> dict[str, Any] | None:
    """
    Return the latest completed YOLO detection connected
    to the report used by the employee assignment.
    """

    return fetch_one(
        """
        SELECT
            ds.detection_session_id,
            ds.request_uuid,
            ds.user_id,
            ds.report_id,
            ds.model_version_id,
            ds.source_module,
            ds.original_filename,
            ds.stored_image_path,
            ds.annotated_image_path,
            ds.applied_global_threshold,
            ds.processing_status,
            ds.processing_time_ms,
            ds.created_at,
            ds.completed_at,

            mv.version_name,
            mv.architecture,

            ta.assignment_id,
            ta.employee_id

        FROM task_assignments AS ta

        JOIN detection_sessions AS ds
            ON ds.report_id = ta.report_id

        JOIN model_versions AS mv
            ON mv.model_version_id =
               ds.model_version_id

        WHERE ta.assignment_id = %s
          AND ta.employee_id = %s
          AND ds.processing_status = 'completed'

        ORDER BY
            ds.completed_at DESC,
            ds.detection_session_id DESC

        LIMIT 1
        """,
        (
            assignment_id,
            employee_id,
        ),
    )


def get_detected_objects_for_employee_assignment(
    detection_session_id: int,
) -> list[dict[str, Any]]:
    """
    Return detected objects and their waste categories.
    """

    return fetch_all(
        """
        SELECT
            obj.detected_object_id,
            obj.detection_session_id,
            obj.model_class_id,
            obj.confidence,
            obj.applied_class_threshold,
            obj.bbox_x1,
            obj.bbox_y1,
            obj.bbox_x2,
            obj.bbox_y2,

            mc.class_name,
            mc.display_name,
            mc.future_merged_label,

            wc.category_id,
            wc.category_code,
            wc.category_name,
            wc.description AS category_description,
            wc.hazard_level,
            wc.requires_special_handling

        FROM detected_objects AS obj

        JOIN model_classes AS mc
            ON mc.model_class_id =
               obj.model_class_id

        JOIN waste_categories AS wc
            ON wc.category_id =
               mc.category_id

        WHERE obj.detection_session_id = %s
          AND mc.is_active = 1
          AND wc.is_active = 1

        ORDER BY
            FIELD(
                wc.hazard_level,
                'high',
                'medium',
                'low'
            ),
            obj.confidence DESC,
            obj.detected_object_id
        """,
        (detection_session_id,),
    )


# ============================================================
# VERIFIED EMPLOYEE KNOWLEDGE
# ============================================================

def retrieve_verified_employee_knowledge(
    model_class_id: int,
    category_id: int,
    region_id: int | None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """
    Retrieve verified municipal-employee knowledge.

    Search priority:

    1. Exact class and selected region.
    2. Exact class with national coverage.
    3. Category match and selected region.
    4. Category match with national coverage.
    """

    safe_limit = min(
        max(int(limit), 1),
        20,
    )

    rows = fetch_all(
        """
        SELECT
            k.*

        FROM v_verified_bd_rag_knowledge AS k

        WHERE k.audience_role =
              'municipal_employee'

          AND (
              k.model_class_id = %s
              OR k.category_id = %s
          )

          AND (
              (
                  %s IS NOT NULL
                  AND k.region_id = %s
              )
              OR k.region_id IS NULL
          )

        ORDER BY
            CASE
                WHEN k.model_class_id = %s
                THEN 0
                ELSE 1
            END,

            CASE
                WHEN %s IS NOT NULL
                     AND k.region_id = %s
                THEN 0

                WHEN k.region_id IS NULL
                THEN 1

                ELSE 2
            END,

            k.priority DESC,
            k.knowledge_id

        LIMIT %s
        """,
        (
            model_class_id,
            category_id,

            region_id,
            region_id,

            model_class_id,

            region_id,
            region_id,

            safe_limit,
        ),
    )

    ranked_rows: list[dict[str, Any]] = []
    seen_knowledge_ids: set[int] = set()

    for row_value in rows:
        row = dict(row_value)

        knowledge_id = int(
            row["knowledge_id"]
        )

        if knowledge_id in seen_knowledge_ids:
            continue

        seen_knowledge_ids.add(
            knowledge_id
        )

        row_model_class_id = int(
            row["model_class_id"]
        )

        row_region_id = row.get(
            "region_id"
        )

        exact_class = (
            row_model_class_id
            == model_class_id
        )

        exact_region = (
            region_id is not None
            and row_region_id == region_id
        )

        national_record = (
            row_region_id is None
        )

        if exact_class and exact_region:
            retrieval_method = "exact_class"
            retrieval_score = 1.0

        elif exact_class and national_record:
            retrieval_method = "exact_class"
            retrieval_score = 0.95

        elif exact_region:
            retrieval_method = (
                "category_fallback"
            )
            retrieval_score = 0.85

        else:
            retrieval_method = (
                "national_fallback"
            )
            retrieval_score = 0.75

        row["retrieval_method"] = (
            retrieval_method
        )

        row["retrieval_score"] = (
            retrieval_score
        )

        ranked_rows.append(row)

    return ranked_rows


# ============================================================
# EMPLOYEE SAFETY RULES
# ============================================================

def get_employee_safety_rules(
    model_class_id: int,
    category_id: int,
) -> list[dict[str, Any]]:
    """
    Return active municipal employee safety rules.
    """

    return fetch_all(
        """
        SELECT
            safety_rule_id,
            model_class_id,
            category_id,
            audience_role,
            rule_code,
            rule_type,
            severity,
            rule_text,
            is_mandatory

        FROM safety_rules

        WHERE is_active = 1

          AND audience_role IN (
              'all',
              'municipal_employee'
          )

          AND category_id = %s

          AND (
              model_class_id = %s
              OR model_class_id IS NULL
          )

        ORDER BY
            FIELD(
                severity,
                'critical',
                'high',
                'medium',
                'low'
            ),

            FIELD(
                rule_type,
                'prohibited',
                'required',
                'warning'
            ),

            safety_rule_id
        """,
        (
            category_id,
            model_class_id,
        ),
    )


# ============================================================
# VERIFIED EMPLOYEE FACILITIES
# ============================================================

def get_verified_employee_facilities(
    region_id: int | None,
    category_id: int,
) -> list[dict[str, Any]]:
    """
    Return verified facilities accepting the category.
    """

    if region_id is None:
        return []

    return fetch_all(
        """
        SELECT
            vf.facility_id,
            vf.region_id,
            vf.region_name,
            vf.facility_name,
            vf.facility_type,
            vf.address_text,
            vf.latitude,
            vf.longitude,
            vf.phone,
            vf.email,
            vf.opening_hours,

            fac.acceptance_notes

        FROM v_verified_disposal_facilities AS vf

        JOIN facility_accepted_categories AS fac
            ON fac.facility_id =
               vf.facility_id

        WHERE vf.region_id = %s
          AND fac.category_id = %s

        ORDER BY vf.facility_name
        """,
        (
            region_id,
            category_id,
        ),
    )


# ============================================================
# EMPLOYEE ADVICE STORAGE
# ============================================================

def create_employee_advice(
    detection_session_id: int,
    priority_level: str,
    summary: str,
    response_language: str,
    response_payload: dict[str, Any],
    prompt_version: str = (
        "offline-employee-rag-1.0"
    ),
) -> int:
    """
    Save a municipal employee RAG response.
    """

    allowed_priorities = {
        "low",
        "medium",
        "high",
        "critical",
    }

    if priority_level not in allowed_priorities:
        raise ValueError(
            "priority_level must be low, medium, "
            "high or critical."
        )

    if response_language not in {
        "en",
        "bn",
    }:
        raise ValueError(
            "response_language must be 'en' or 'bn'."
        )

    advice_id = execute(
        """
        INSERT INTO generated_advice (
            detection_session_id,
            audience_role,
            priority_level,
            summary,
            response_language,
            response_json,
            gemini_model,
            prompt_version,
            local_verification_required
        )
        VALUES (
            %s,
            'municipal_employee',
            %s,
            %s,
            %s,
            %s,
            NULL,
            %s,
            1
        )
        """,
        (
            detection_session_id,
            priority_level,
            summary,
            response_language,

            json.dumps(
                response_payload,
                ensure_ascii=False,
                default=_json_default,
            ),

            prompt_version,
        ),
    )

    if not advice_id:
        raise RuntimeError(
            "The Employee RAG advice record "
            "could not be created."
        )

    return int(advice_id)


def save_employee_advice_knowledge_links(
    advice_id: int,
    knowledge_rows: list[dict[str, Any]],
) -> None:
    """
    Save the verified knowledge records used
    by the Employee RAG response.
    """

    allowed_methods = {
        "exact_class",
        "category_fallback",
        "national_fallback",
        "manual",
    }

    for rank, row in enumerate(
        knowledge_rows,
        start=1,
    ):
        retrieval_method = row.get(
            "retrieval_method",
            "manual",
        )

        if retrieval_method not in allowed_methods:
            retrieval_method = "manual"

        execute(
            """
            INSERT INTO advice_knowledge_links (
                advice_id,
                knowledge_id,
                retrieval_rank,
                retrieval_method,
                retrieval_score
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

                retrieval_score =
                    VALUES(retrieval_score)
            """,
            (
                advice_id,
                row["knowledge_id"],
                rank,
                retrieval_method,
                row.get("retrieval_score"),
            ),
        )


# ============================================================
# EMPLOYEE ADVICE HISTORY
# ============================================================

def get_employee_advice_history(
    employee_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Return saved municipal Employee RAG responses.
    """

    safe_limit = min(
        max(int(limit), 1),
        100,
    )

    return fetch_all(
        """
        SELECT
            ga.advice_id,
            ga.detection_session_id,
            ga.priority_level,
            ga.summary,
            ga.response_language,
            ga.response_json,
            ga.gemini_model,
            ga.prompt_version,
            ga.local_verification_required,
            ga.created_at,

            ds.request_uuid,
            ds.report_id,
            ds.original_filename,
            ds.annotated_image_path,

            ta.assignment_id,
            ta.assignment_status,
            ta.priority AS assignment_priority,

            wr.title AS report_title,
            wr.address_text

        FROM generated_advice AS ga

        JOIN detection_sessions AS ds
            ON ds.detection_session_id =
               ga.detection_session_id

        JOIN task_assignments AS ta
            ON ta.report_id = ds.report_id

        JOIN waste_reports AS wr
            ON wr.report_id = ta.report_id

        WHERE ta.employee_id = %s
          AND ga.audience_role =
              'municipal_employee'

        ORDER BY ga.created_at DESC

        LIMIT %s
        """,
        (
            employee_id,
            safe_limit,
        ),
    )


def get_employee_advice_by_id(
    advice_id: int,
    employee_id: int,
) -> dict[str, Any] | None:
    """
    Return one Employee RAG response belonging
    to the employee.
    """

    return fetch_one(
        """
        SELECT
            ga.advice_id,
            ga.detection_session_id,
            ga.priority_level,
            ga.summary,
            ga.response_language,
            ga.response_json,
            ga.gemini_model,
            ga.prompt_version,
            ga.local_verification_required,
            ga.created_at,

            ds.request_uuid,
            ds.report_id,
            ds.original_filename,
            ds.annotated_image_path,

            ta.assignment_id,
            ta.assignment_status,
            ta.priority AS assignment_priority,

            wr.title AS report_title,
            wr.address_text

        FROM generated_advice AS ga

        JOIN detection_sessions AS ds
            ON ds.detection_session_id =
               ga.detection_session_id

        JOIN task_assignments AS ta
            ON ta.report_id = ds.report_id

        JOIN waste_reports AS wr
            ON wr.report_id = ta.report_id

        WHERE ga.advice_id = %s
          AND ta.employee_id = %s
          AND ga.audience_role =
              'municipal_employee'

        LIMIT 1
        """,
        (
            advice_id,
            employee_id,
        ),
    )