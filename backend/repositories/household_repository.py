import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from db import execute, fetch_all, fetch_one


# ============================================================
# JSON HELPERS
# ============================================================

def _json_default(value: Any) -> Any:
    """Convert database-specific values into JSON-safe values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


# ============================================================
# HOUSEHOLD USER
# ============================================================

def get_household_user_scope(
    user_id: int,
) -> dict[str, Any] | None:
    """Return an active household user and the user's region."""

    return fetch_one(
        """
        SELECT
            u.user_id,
            u.full_name,
            u.email,
            u.phone,
            u.address_text,
            u.region_id,
            r.region_name,
            r.region_type,
            u.role,
            u.account_status

        FROM users AS u

        LEFT JOIN regions AS r
            ON r.region_id = u.region_id

        WHERE u.user_id = %s
          AND u.role = 'household'
          AND u.account_status = 'active'
        """,
        (user_id,),
    )


# ============================================================
# DETECTION SESSION
# ============================================================

def get_household_detection_session(
    detection_session_id: int,
    user_id: int | None = None,
) -> dict[str, Any] | None:
    """Return one completed household detection session."""

    query = """
        SELECT
            ds.detection_session_id,
            ds.request_uuid,
            ds.user_id,
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
            mv.architecture

        FROM detection_sessions AS ds

        JOIN model_versions AS mv
            ON mv.model_version_id = ds.model_version_id

        WHERE ds.detection_session_id = %s
          AND ds.source_module = 'household'
          AND ds.processing_status = 'completed'
    """

    parameters: list[Any] = [
        detection_session_id
    ]

    if user_id is not None:
        query += " AND ds.user_id = %s"
        parameters.append(user_id)

    return fetch_one(
        query,
        tuple(parameters),
    )


def get_detected_objects_for_session(
    detection_session_id: int,
) -> list[dict[str, Any]]:
    """Return detected objects with their mapped waste categories."""

    return fetch_all(
        """
        SELECT
            obj.detected_object_id,
            obj.detection_session_id,
            obj.model_class_id,

            mc.class_name,
            mc.display_name,
            mc.future_merged_label,

            mc.category_id,
            wc.category_code,
            wc.category_name,
            wc.description AS category_description,
            wc.hazard_level,
            wc.requires_special_handling,

            obj.confidence,
            obj.applied_class_threshold,
            obj.bbox_x1,
            obj.bbox_y1,
            obj.bbox_x2,
            obj.bbox_y2

        FROM detected_objects AS obj

        JOIN model_classes AS mc
            ON mc.model_class_id = obj.model_class_id

        JOIN waste_categories AS wc
            ON wc.category_id = mc.category_id

        WHERE obj.detection_session_id = %s
          AND mc.is_active = 1
          AND wc.is_active = 1

        ORDER BY
            obj.confidence DESC,
            obj.detected_object_id
        """,
        (detection_session_id,),
    )


def get_model_class_by_name(
    class_name: str,
) -> dict[str, Any] | None:
    """
    Find one active YOLO class and its waste category.

    This is useful for testing before the full YOLO upload
    endpoint is connected.
    """

    return fetch_one(
        """
        SELECT
            mc.model_class_id,
            mc.class_name,
            mc.display_name,
            mc.future_merged_label,
            mc.description AS class_description,

            wc.category_id,
            wc.category_code,
            wc.category_name,
            wc.description AS category_description,
            wc.hazard_level,
            wc.requires_special_handling

        FROM model_classes AS mc

        JOIN waste_categories AS wc
            ON wc.category_id = mc.category_id

        WHERE LOWER(mc.class_name) = LOWER(%s)
          AND mc.is_active = 1
          AND wc.is_active = 1

        LIMIT 1
        """,
        (class_name.strip(),),
    )


# ============================================================
# VERIFIED HOUSEHOLD RAG RETRIEVAL
# ============================================================

def retrieve_verified_household_knowledge(
    model_class_id: int,
    category_id: int,
    region_id: int | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve verified household disposal guidance.

    Retrieval order:

    1. Exact detected class for the user's region.
    2. Exact detected class with national coverage.
    3. Same-category guidance for the user's region.
    4. Same-category national fallback.
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

        WHERE k.audience_role = 'household'

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

        exact_class = (
            int(row["model_class_id"])
            == model_class_id
        )

        exact_region = (
            region_id is not None
            and row.get("region_id") == region_id
        )

        if exact_class and exact_region:
            retrieval_method = "exact_class"
            retrieval_score = 1.0

        elif exact_class:
            retrieval_method = "national_fallback"
            retrieval_score = 0.95

        elif exact_region:
            retrieval_method = "category_fallback"
            retrieval_score = 0.85

        else:
            retrieval_method = "national_fallback"
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
# SAFETY RULES
# ============================================================

def get_household_safety_rules(
    model_class_id: int,
    category_id: int,
) -> list[dict[str, Any]]:
    """
    Return active household safety rules.

    These include required actions, warnings and prohibited
    actions such as not burning batteries or plastic.
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
              'household'
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
# VERIFIED FACILITIES
# ============================================================

def get_verified_household_facilities(
    region_id: int | None,
    category_id: int,
) -> list[dict[str, Any]]:
    """
    Return verified local facilities that accept the detected
    waste category.
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
            ON fac.facility_id = vf.facility_id

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
# HOUSEHOLD ADVICE STORAGE
# ============================================================

def create_household_advice(
    detection_session_id: int,
    priority_level: str,
    summary: str,
    response_language: str,
    response_payload: dict[str, Any],
    prompt_version: str = "offline-household-rag-1.0",
) -> int:
    """Save one generated Household RAG response."""

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
            'household',
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
            "The household advice record "
            "could not be created."
        )

    return int(advice_id)


def save_household_advice_knowledge_links(
    advice_id: int,
    knowledge_rows: list[dict[str, Any]],
) -> None:
    """
    Save which verified knowledge records supported the
    household advice.
    """

    for rank, row in enumerate(
        knowledge_rows,
        start=1,
    ):
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
                row["retrieval_method"],
                row.get("retrieval_score"),
            ),
        )


# ============================================================
# HOUSEHOLD ADVICE HISTORY
# ============================================================

def get_household_advice_history(
    user_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return saved Household RAG advice for one user."""

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
            ds.original_filename,
            ds.annotated_image_path

        FROM generated_advice AS ga

        JOIN detection_sessions AS ds
            ON ds.detection_session_id =
               ga.detection_session_id

        WHERE ds.user_id = %s
          AND ga.audience_role = 'household'

        ORDER BY ga.created_at DESC

        LIMIT %s
        """,
        (
            user_id,
            safe_limit,
        ),
    )


def get_household_advice_by_id(
    advice_id: int,
    user_id: int,
) -> dict[str, Any] | None:
    """Return one household advice record owned by the user."""

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
            ds.original_filename,
            ds.annotated_image_path

        FROM generated_advice AS ga

        JOIN detection_sessions AS ds
            ON ds.detection_session_id =
               ga.detection_session_id

        WHERE ga.advice_id = %s
          AND ds.user_id = %s
          AND ga.audience_role = 'household'
        """,
        (
            advice_id,
            user_id,
        ),
    )