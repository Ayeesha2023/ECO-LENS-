import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def _get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "eco-lens_db"),
        autocommit=False,
    )


def _safe_value(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _safe_row(row: dict | None):
    if row is None:
        return None
    return {key: _safe_value(value) for key, value in row.items()}


def _safe_rows(rows: list[dict]):
    return [_safe_row(row) for row in rows]


def _json_load(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return bool(row and int(row["table_count"]) > 0)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) AS column_count
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    row = cursor.fetchone()
    return bool(row and int(row["column_count"]) > 0)


def _region_type_supports_area(cursor) -> bool:
    cursor.execute(
        """
        SELECT COLUMN_TYPE
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'regions'
          AND column_name = 'region_type'
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return False
    return "'area'" in str(row["COLUMN_TYPE"])


def get_household_for_user(user_id: int):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        has_locality = _column_exists(cursor, "users", "locality_region_id")
        if has_locality:
            cursor.execute(
                """
                SELECT
                    u.user_id, u.role, u.full_name, u.email, u.phone,
                    u.address_text, u.region_id, u.locality_region_id,
                    u.account_status, u.email_verified, u.created_at,
                    ward.region_name AS ward_name,
                    ward.region_type AS ward_region_type,
                    locality.region_name AS locality_name,
                    locality.region_type AS locality_region_type
                FROM users AS u
                LEFT JOIN regions AS ward
                    ON ward.region_id = u.region_id
                LEFT JOIN regions AS locality
                    ON locality.region_id = u.locality_region_id
                WHERE u.user_id = %s
                  AND u.role = 'household'
                LIMIT 1
                """,
                (user_id,),
            )
        else:
            cursor.execute(
                """
                SELECT
                    u.user_id, u.role, u.full_name, u.email, u.phone,
                    u.address_text, u.region_id, u.account_status,
                    u.email_verified, u.created_at,
                    r.region_name AS ward_name,
                    r.region_type AS ward_region_type
                FROM users AS u
                LEFT JOIN regions AS r
                    ON r.region_id = u.region_id
                WHERE u.user_id = %s
                  AND u.role = 'household'
                LIMIT 1
                """,
                (user_id,),
            )
        return _safe_row(cursor.fetchone())
    finally:
        cursor.close()
        connection.close()


def get_household_location_options():
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if _region_type_supports_area(cursor):
            cursor.execute(
                """
                SELECT
                    area.region_id AS location_region_id,
                    area.region_name AS location_name,
                    area.region_type AS location_type,
                    ward.region_id AS ward_region_id,
                    ward.region_name AS ward_name,
                    ward.region_code AS ward_code,
                    area.latitude, area.longitude
                FROM regions AS area
                JOIN regions AS ward
                    ON ward.region_id = area.parent_region_id
                WHERE area.is_active = 1
                  AND ward.is_active = 1
                  AND area.region_type = 'area'
                  AND ward.region_type = 'ward'
                ORDER BY ward.region_name, area.region_name
                """
            )
            rows = cursor.fetchall()
            if rows:
                return _safe_rows(rows)

        cursor.execute(
            """
            SELECT
                ward.region_id AS location_region_id,
                ward.region_name AS location_name,
                ward.region_type AS location_type,
                ward.region_id AS ward_region_id,
                ward.region_name AS ward_name,
                ward.region_code AS ward_code,
                ward.latitude, ward.longitude
            FROM regions AS ward
            WHERE ward.is_active = 1
              AND ward.region_type = 'ward'
            ORDER BY ward.region_name
            """
        )
        return _safe_rows(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()


def resolve_report_ward(cursor, location_region_id: int):
    cursor.execute(
        """
        SELECT region_id, parent_region_id, region_name, region_type, is_active
        FROM regions
        WHERE region_id = %s
        LIMIT 1
        """,
        (location_region_id,),
    )
    region = cursor.fetchone()
    if region is None:
        raise ValueError("The selected location was not found.")
    if not int(region["is_active"]):
        raise ValueError("The selected location is inactive.")

    if region["region_type"] == "ward":
        return {
            "location_region_id": int(region["region_id"]),
            "location_name": region["region_name"],
            "ward_region_id": int(region["region_id"]),
            "ward_name": region["region_name"],
        }

    if region["region_type"] == "area":
        cursor.execute(
            """
            SELECT region_id, region_name, region_type, is_active
            FROM regions
            WHERE region_id = %s
            LIMIT 1
            """,
            (region["parent_region_id"],),
        )
        ward = cursor.fetchone()
        if (
            ward is None
            or ward["region_type"] != "ward"
            or not int(ward["is_active"])
        ):
            raise ValueError(
                "The selected area is not connected to an active ward."
            )
        return {
            "location_region_id": int(region["region_id"]),
            "location_name": region["region_name"],
            "ward_region_id": int(ward["region_id"]),
            "ward_name": ward["region_name"],
        }

    raise ValueError("Please choose a ward or local area.")


def _find_responsible_authority(cursor, ward_region_id: int):
    has_authority_regions = _table_exists(cursor, "authority_regions")

    if has_authority_regions:
        # Later EcoLens patches use authority_regions for multi-ward coverage.
        cursor.execute(
            """
            SELECT DISTINCT ca.authority_id, ca.organization_name
            FROM community_authorities AS ca
            JOIN users AS u ON u.user_id = ca.user_id
            LEFT JOIN authority_regions AS ar
                ON ar.authority_id = ca.authority_id
            WHERE ca.approval_status = 'approved'
              AND u.account_status = 'active'
              AND (
                    ca.assigned_region_id = %s
                    OR ar.region_id = %s
              )
            ORDER BY ca.authority_id
            LIMIT 1
            """,
            (ward_region_id, ward_region_id),
        )
    else:
        cursor.execute(
            """
            SELECT ca.authority_id, ca.organization_name
            FROM community_authorities AS ca
            JOIN users AS u ON u.user_id = ca.user_id
            WHERE ca.approval_status = 'approved'
              AND u.account_status = 'active'
              AND ca.assigned_region_id = %s
            ORDER BY ca.authority_id
            LIMIT 1
            """,
            (ward_region_id,),
        )

    return cursor.fetchone()


def create_public_report(
    *,
    user_id: int,
    location_region_id: int,
    title: str,
    description: str,
    address_text: str | None,
    latitude: float,
    longitude: float,
    image_path: str,
):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT user_id, account_status
            FROM users
            WHERE user_id = %s
              AND role = 'household'
            LIMIT 1
            FOR UPDATE
            """,
            (user_id,),
        )
        household = cursor.fetchone()
        if household is None or household["account_status"] != "active":
            raise ValueError("An active household account is required.")

        location = resolve_report_ward(cursor, location_region_id)
        authority = _find_responsible_authority(
            cursor,
            location["ward_region_id"],
        )
        authority_id = int(authority["authority_id"]) if authority else None

        # Household users do not set municipal priority. Operational priority
        # is chosen later by the Community Authority during assignment.
        cursor.execute(
            """
            INSERT INTO waste_reports (
                reporter_user_id,
                region_id,
                authority_id,
                title,
                description,
                address_text,
                latitude,
                longitude,
                report_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'submitted')
            """,
            (
                user_id,
                location["ward_region_id"],
                authority_id,
                title,
                description,
                address_text,
                latitude,
                longitude,
            ),
        )
        report_id = int(cursor.lastrowid)

        cursor.execute(
            """
            INSERT INTO report_images (
                report_id,
                image_path,
                image_type,
                uploaded_by_user_id
            )
            VALUES (%s, %s, 'before', %s)
            """,
            (report_id, image_path, user_id),
        )

        connection.commit()
        return {
            "report_id": report_id,
            "report_status": "submitted",
            "location_name": location["location_name"],
            "ward_region_id": location["ward_region_id"],
            "ward_name": location["ward_name"],
            "authority_id": authority_id,
            "authority_name": authority["organization_name"] if authority else None,
            "authority_found": bool(authority),
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_household_reports(user_id: int, limit: int = 200):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                wr.report_id,
                wr.reporter_user_id,
                wr.region_id,
                wr.authority_id,
                wr.title,
                wr.description,
                wr.address_text,
                wr.latitude,
                wr.longitude,
                wr.report_status,
                wr.submitted_at,
                wr.updated_at,
                wr.completed_at,
                r.region_name,
                r.region_code,
                ca.organization_name AS authority_name,
                (
                    SELECT ri.image_path
                    FROM report_images AS ri
                    WHERE ri.report_id = wr.report_id
                      AND ri.image_type = 'before'
                    ORDER BY ri.created_at ASC
                    LIMIT 1
                ) AS before_image_path,
                (
                    SELECT ri.image_path
                    FROM report_images AS ri
                    WHERE ri.report_id = wr.report_id
                      AND ri.image_type = 'after'
                    ORDER BY ri.created_at DESC
                    LIMIT 1
                ) AS after_image_path,
                (
                    SELECT ta.assignment_status
                    FROM task_assignments AS ta
                    WHERE ta.report_id = wr.report_id
                      AND ta.assignment_status <> 'cancelled'
                    ORDER BY ta.assigned_at DESC
                    LIMIT 1
                ) AS assignment_status,
                (
                    SELECT u.full_name
                    FROM task_assignments AS ta
                    JOIN employees AS e ON e.employee_id = ta.employee_id
                    JOIN users AS u ON u.user_id = e.user_id
                    WHERE ta.report_id = wr.report_id
                      AND ta.assignment_status <> 'cancelled'
                    ORDER BY ta.assigned_at DESC
                    LIMIT 1
                ) AS employee_name
            FROM waste_reports AS wr
            JOIN regions AS r ON r.region_id = wr.region_id
            LEFT JOIN community_authorities AS ca
                ON ca.authority_id = wr.authority_id
            WHERE wr.reporter_user_id = %s
            ORDER BY wr.submitted_at DESC
            LIMIT %s
            """,
            (user_id, int(limit)),
        )
        return _safe_rows(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()


def get_household_report(user_id: int, report_id: int):
    reports = get_household_reports(user_id=user_id, limit=500)
    report = next(
        (
            item
            for item in reports
            if int(item["report_id"]) == int(report_id)
        ),
        None,
    )
    if report is None:
        return None

    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT report_image_id, image_path, image_type, created_at
            FROM report_images
            WHERE report_id = %s
            ORDER BY created_at ASC
            """,
            (report_id,),
        )
        report["images"] = _safe_rows(cursor.fetchall())
        return report
    finally:
        cursor.close()
        connection.close()


def get_household_detection_history(user_id: int, limit: int = 100):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                ds.detection_session_id,
                ds.request_uuid,
                ds.original_filename,
                ds.stored_image_path,
                ds.annotated_image_path,
                ds.applied_global_threshold,
                ds.processing_status,
                ds.processing_time_ms,
                ds.created_at,
                ds.completed_at,
                mv.version_name AS model_version,
                mv.architecture,
                ga.advice_id,
                ga.priority_level,
                ga.summary,
                ga.response_language,
                ga.response_json,
                ga.gemini_model,
                ga.prompt_version,
                ga.local_verification_required,
                ga.created_at AS advice_created_at
            FROM detection_sessions AS ds
            JOIN model_versions AS mv
                ON mv.model_version_id = ds.model_version_id
            LEFT JOIN generated_advice AS ga
                ON ga.advice_id = (
                    SELECT ga2.advice_id
                    FROM generated_advice AS ga2
                    WHERE ga2.detection_session_id = ds.detection_session_id
                      AND ga2.audience_role = 'household'
                    ORDER BY ga2.created_at DESC
                    LIMIT 1
                )
            WHERE ds.user_id = %s
              AND ds.source_module = 'household'
            ORDER BY ds.created_at DESC
            LIMIT %s
            """,
            (user_id, int(limit)),
        )
        rows = _safe_rows(cursor.fetchall())

        for row in rows:
            row["advice_result"] = _json_load(row.get("response_json"))
            row.pop("response_json", None)
            cursor.execute(
                """
                SELECT
                    do.detected_object_id,
                    do.model_class_id,
                    do.confidence,
                    do.applied_class_threshold,
                    mc.class_name,
                    mc.display_name,
                    wc.category_name,
                    wc.category_code,
                    wc.hazard_level
                FROM detected_objects AS do
                JOIN model_classes AS mc
                    ON mc.model_class_id = do.model_class_id
                JOIN waste_categories AS wc
                    ON wc.category_id = mc.category_id
                WHERE do.detection_session_id = %s
                ORDER BY do.confidence DESC
                """,
                (row["detection_session_id"],),
            )
            row["detected_objects"] = _safe_rows(cursor.fetchall())

        return rows
    finally:
        cursor.close()
        connection.close()


def build_household_dashboard(user_id: int):
    household = get_household_for_user(user_id)
    if household is None:
        raise ValueError("Household account was not found.")

    reports = get_household_reports(user_id)
    detections = get_household_detection_history(user_id)
    active_report_statuses = {
        "submitted",
        "under_review",
        "assigned",
        "in_progress",
    }

    summary = {
        "total_reports": len(reports),
        "active_reports": sum(
            1
            for report in reports
            if report["report_status"] in active_report_statuses
        ),
        "completed_reports": sum(
            1
            for report in reports
            if report["report_status"] == "completed"
        ),
        "previous_detections": len(detections),
    }

    return {
        "household": household,
        "summary": summary,
        "reports": reports,
        "detections": detections,
        "location_options": get_household_location_options(),
    }