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

    return {
        key: _safe_value(value)
        for key, value in row.items()
    }


def _safe_rows(rows: list[dict]):
    return [_safe_row(row) for row in rows]


# ============================================================
# EMPLOYEE PROFILE
# ============================================================

def get_employee_for_user(user_id: int):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                e.employee_id,
                e.user_id,
                e.authority_id,
                e.employee_code,
                e.job_title,
                e.employment_status,
                e.joined_at,

                u.full_name,
                u.email,
                u.phone,
                u.account_status,

                ca.organization_name,
                ca.assigned_region_id,

                r.region_name AS primary_region_name,
                r.region_type AS primary_region_type

            FROM employees AS e

            JOIN users AS u
                ON u.user_id = e.user_id

            JOIN community_authorities AS ca
                ON ca.authority_id = e.authority_id

            JOIN regions AS r
                ON r.region_id = ca.assigned_region_id

            WHERE e.user_id = %s

            LIMIT 1
            """,
            (user_id,),
        )

        return _safe_row(cursor.fetchone())

    finally:
        cursor.close()
        connection.close()


# ============================================================
# MODEL CLASSES
# ============================================================

def get_model_classes():
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                mc.model_class_id,
                mc.category_id,
                mc.class_name,
                mc.display_name,

                wc.category_code,
                wc.category_name,
                wc.hazard_level,
                wc.requires_special_handling

            FROM model_classes AS mc

            JOIN waste_categories AS wc
                ON wc.category_id = mc.category_id

            WHERE mc.is_active = 1
              AND wc.is_active = 1

            ORDER BY mc.model_class_id
            """
        )

        return _safe_rows(cursor.fetchall())

    finally:
        cursor.close()
        connection.close()


# ============================================================
# ASSIGNMENTS
# ============================================================

def get_employee_assignments(
    employee_id: int,
    limit: int = 100,
):
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                ta.assignment_id,
                ta.report_id,
                ta.employee_id,
                ta.assigned_by_authority_id,
                ta.assignment_notes,
                ta.priority,
                ta.assignment_status,
                ta.assigned_at,
                ta.accepted_at,
                ta.started_at,
                ta.completed_at,

                wr.title AS report_title,
                wr.description AS report_description,
                wr.address_text,
                wr.latitude,
                wr.longitude,
                wr.report_status,
                wr.submitted_at,

                r.region_id,
                r.region_name,
                r.region_type,

                ca.organization_name,

                (
                    SELECT ri.image_path
                    FROM report_images AS ri
                    WHERE ri.report_id = wr.report_id
                      AND ri.image_type = 'before'
                    ORDER BY ri.created_at ASC
                    LIMIT 1
                ) AS before_image_path,

                cr.cleanup_id,
                cr.total_waste_kg,
                cr.recycled_waste_kg,
                cr.composted_waste_kg,
                cr.properly_disposed_kg,
                cr.hazardous_waste_kg,
                cr.cleanup_notes,
                cr.verification_status AS cleanup_verification_status

            FROM task_assignments AS ta

            JOIN waste_reports AS wr
                ON wr.report_id = ta.report_id

            JOIN regions AS r
                ON r.region_id = wr.region_id

            JOIN community_authorities AS ca
                ON ca.authority_id = ta.assigned_by_authority_id

            LEFT JOIN cleanup_records AS cr
                ON cr.assignment_id = ta.assignment_id

            WHERE ta.employee_id = %s

            ORDER BY
                CASE ta.assignment_status
                    WHEN 'assigned' THEN 1
                    WHEN 'accepted' THEN 2
                    WHEN 'in_progress' THEN 3
                    WHEN 'completed' THEN 4
                    ELSE 5
                END,
                ta.assigned_at DESC

            LIMIT %s
            """,
            (employee_id, int(limit)),
        )

        return _safe_rows(cursor.fetchall())

    finally:
        cursor.close()
        connection.close()


def get_assignment_detail(
    employee_id: int,
    assignment_id: int,
):
    assignments = get_employee_assignments(
        employee_id=employee_id,
        limit=500,
    )

    assignment = next(
        (
            item
            for item in assignments
            if int(item["assignment_id"]) == int(assignment_id)
        ),
        None,
    )

    if assignment is None:
        return None

    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                ri.report_image_id,
                ri.image_path,
                ri.image_type,
                ri.created_at

            FROM report_images AS ri

            WHERE ri.report_id = %s

            ORDER BY ri.created_at ASC
            """,
            (assignment["report_id"],),
        )

        assignment["images"] = _safe_rows(
            cursor.fetchall()
        )

        if assignment.get("cleanup_id"):
            cursor.execute(
                """
                SELECT
                    ccb.cleanup_class_breakdown_id,
                    ccb.model_class_id,
                    ccb.category_id,
                    ccb.weight_kg,
                    ccb.handling_method,
                    ccb.notes,

                    mc.class_name,
                    mc.display_name,

                    wc.category_code,
                    wc.category_name

                FROM cleanup_class_breakdown AS ccb

                JOIN model_classes AS mc
                    ON mc.model_class_id = ccb.model_class_id

                JOIN waste_categories AS wc
                    ON wc.category_id = ccb.category_id

                WHERE ccb.cleanup_id = %s

                ORDER BY mc.model_class_id
                """,
                (assignment["cleanup_id"],),
            )

            assignment["waste_breakdown"] = _safe_rows(
                cursor.fetchall()
            )
        else:
            assignment["waste_breakdown"] = []

        cursor.execute(
            """
            SELECT
                ds.detection_session_id,
                ds.original_filename,
                ds.stored_image_path,
                ds.annotated_image_path,
                ds.processing_status,
                ds.created_at,
                ds.completed_at

            FROM detection_sessions AS ds

            WHERE ds.report_id = %s
              AND ds.user_id = (
                    SELECT e.user_id
                    FROM employees AS e
                    WHERE e.employee_id = %s
                    LIMIT 1
              )
              AND ds.source_module = 'employee'

            ORDER BY ds.created_at DESC

            LIMIT 1
            """,
            (
                assignment["report_id"],
                employee_id,
            ),
        )

        assignment["latest_detection"] = _safe_row(
            cursor.fetchone()
        )

        return assignment

    finally:
        cursor.close()
        connection.close()


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def build_employee_dashboard(user_id: int):
    employee = get_employee_for_user(user_id)

    if employee is None:
        raise ValueError("Employee account was not found.")

    employee_id = int(employee["employee_id"])

    assignments = get_employee_assignments(employee_id)
    model_classes = get_model_classes()

    active_statuses = {
        "assigned",
        "accepted",
        "in_progress",
    }

    summary = {
        "total_assignments": len(assignments),

        "new_assignments": sum(
            1
            for assignment in assignments
            if assignment["assignment_status"] == "assigned"
        ),

        "active_assignments": sum(
            1
            for assignment in assignments
            if assignment["assignment_status"] in active_statuses
        ),

        "in_progress": sum(
            1
            for assignment in assignments
            if assignment["assignment_status"] == "in_progress"
        ),

        "completed_assignments": sum(
            1
            for assignment in assignments
            if assignment["assignment_status"] == "completed"
        ),
    }

    return {
        "employee": employee,
        "summary": summary,
        "assignments": assignments,
        "model_classes": model_classes,
    }


# ============================================================
# ACCEPT / START
# ============================================================

def transition_assignment(
    employee_id: int,
    assignment_id: int,
    action: str,
):
    transitions = {
        "accept": {
            "from": "assigned",
            "to": "accepted",
            "timestamp_column": "accepted_at",
            "report_status": "assigned",
        },

        "start": {
            "from": "accepted",
            "to": "in_progress",
            "timestamp_column": "started_at",
            "report_status": "in_progress",
        },
    }

    if action not in transitions:
        raise ValueError("Invalid assignment action.")

    transition = transitions[action]

    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT
                assignment_id,
                report_id,
                employee_id,
                assignment_status

            FROM task_assignments

            WHERE assignment_id = %s
              AND employee_id = %s

            LIMIT 1
            FOR UPDATE
            """,
            (
                assignment_id,
                employee_id,
            ),
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise ValueError(
                "Assignment was not found for this employee."
            )

        if assignment["assignment_status"] != transition["from"]:
            raise ValueError(
                f"Assignment must be {transition['from']} "
                f"before it can become {transition['to']}."
            )

        sql = f"""
            UPDATE task_assignments
            SET
                assignment_status = %s,
                {transition["timestamp_column"]} = NOW()
            WHERE assignment_id = %s
              AND employee_id = %s
        """

        cursor.execute(
            sql,
            (
                transition["to"],
                assignment_id,
                employee_id,
            ),
        )

        cursor.execute(
            """
            UPDATE waste_reports
            SET report_status = %s
            WHERE report_id = %s
            """,
            (
                transition["report_status"],
                assignment["report_id"],
            ),
        )

        connection.commit()

        return {
            "assignment_id": assignment_id,
            "assignment_status": transition["to"],
            "report_status": transition["report_status"],
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# COMPLETE CLEANUP
# ============================================================

def complete_assignment(
    employee_id: int,
    user_id: int,
    assignment_id: int,
    waste_breakdown: list[dict],
    cleanup_notes: str | None,
    after_image_path: str,
):
    if (
        not isinstance(waste_breakdown, list)
        or not waste_breakdown
    ):
        raise ValueError(
            "At least one waste class and weight is required."
        )

    allowed_methods = {
        "recycled",
        "composted",
        "special_collection",
        "controlled_disposal",
        "other",
    }

    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute(
            """
            SELECT
                ta.assignment_id,
                ta.report_id,
                ta.assignment_status,
                ta.assigned_by_authority_id

            FROM task_assignments AS ta

            WHERE ta.assignment_id = %s
              AND ta.employee_id = %s

            LIMIT 1
            FOR UPDATE
            """,
            (
                assignment_id,
                employee_id,
            ),
        )

        assignment = cursor.fetchone()

        if assignment is None:
            raise ValueError(
                "Assignment was not found for this employee."
            )

        if assignment["assignment_status"] != "in_progress":
            raise ValueError(
                "Start the assignment before completing it."
            )

        cursor.execute(
            """
            SELECT cleanup_id

            FROM cleanup_records

            WHERE assignment_id = %s

            LIMIT 1
            """,
            (assignment_id,),
        )

        if cursor.fetchone():
            raise ValueError(
                "A cleanup record already exists for this assignment."
            )

        class_ids = []
        normalized_rows = []

        for item in waste_breakdown:
            try:
                model_class_id = int(
                    item.get("model_class_id")
                )

                weight_kg = float(
                    item.get("weight_kg", 0)
                )

            except (TypeError, ValueError):
                raise ValueError(
                    "Each waste row must have a valid class and weight."
                )

            handling_method = str(
                item.get("handling_method", "")
            ).strip()

            notes = str(
                item.get("notes", "")
            ).strip() or None

            if weight_kg <= 0:
                raise ValueError(
                    "Waste weight must be greater than zero."
                )

            if handling_method not in allowed_methods:
                raise ValueError(
                    "Invalid waste handling method."
                )

            class_ids.append(model_class_id)

            normalized_rows.append(
                {
                    "model_class_id": model_class_id,
                    "weight_kg": round(weight_kg, 2),
                    "handling_method": handling_method,
                    "notes": notes,
                }
            )

        if len(set(class_ids)) != len(class_ids):
            raise ValueError(
                "Each waste class can only be reported once."
            )

        placeholders = ", ".join(
            ["%s"] * len(class_ids)
        )

        cursor.execute(
            f"""
            SELECT
                mc.model_class_id,
                mc.category_id,
                mc.class_name,
                mc.display_name,

                wc.category_code,
                wc.category_name

            FROM model_classes AS mc

            JOIN waste_categories AS wc
                ON wc.category_id = mc.category_id

            WHERE mc.model_class_id IN ({placeholders})
              AND mc.is_active = 1
              AND wc.is_active = 1
            """,
            tuple(class_ids),
        )

        class_rows = cursor.fetchall()

        class_map = {
            int(row["model_class_id"]): row
            for row in class_rows
        }

        if len(class_map) != len(class_ids):
            raise ValueError(
                "One or more selected waste classes are invalid."
            )

        total_waste_kg = 0.0
        recycled_waste_kg = 0.0
        composted_waste_kg = 0.0
        properly_disposed_kg = 0.0
        hazardous_waste_kg = 0.0

        for item in normalized_rows:
            metadata = class_map[
                item["model_class_id"]
            ]

            weight = item["weight_kg"]
            method = item["handling_method"]

            total_waste_kg += weight

            if method == "recycled":
                recycled_waste_kg += weight

            if method == "composted":
                composted_waste_kg += weight

            if method in {
                "special_collection",
                "controlled_disposal",
            }:
                properly_disposed_kg += weight

            if metadata["category_code"] == "HAZARDOUS":
                hazardous_waste_kg += weight

        cursor.execute(
            """
            INSERT INTO cleanup_records (
                assignment_id,
                employee_id,
                report_id,
                cleaned_at,
                total_waste_kg,
                recycled_waste_kg,
                composted_waste_kg,
                properly_disposed_kg,
                hazardous_waste_kg,
                estimated_co2_reduction_kg,
                cleanup_notes,
                verification_status
            )
            VALUES (
                %s,
                %s,
                %s,
                NOW(),
                %s,
                %s,
                %s,
                %s,
                %s,
                0.00,
                %s,
                'pending'
            )
            """,
            (
                assignment_id,
                employee_id,
                assignment["report_id"],
                round(total_waste_kg, 2),
                round(recycled_waste_kg, 2),
                round(composted_waste_kg, 2),
                round(properly_disposed_kg, 2),
                round(hazardous_waste_kg, 2),
                cleanup_notes,
            ),
        )

        cleanup_id = int(cursor.lastrowid)

        for item in normalized_rows:
            metadata = class_map[
                item["model_class_id"]
            ]

            cursor.execute(
                """
                INSERT INTO cleanup_class_breakdown (
                    cleanup_id,
                    model_class_id,
                    category_id,
                    weight_kg,
                    handling_method,
                    notes
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    cleanup_id,
                    item["model_class_id"],
                    metadata["category_id"],
                    item["weight_kg"],
                    item["handling_method"],
                    item["notes"],
                ),
            )

        cursor.execute(
            """
            INSERT INTO report_images (
                report_id,
                image_path,
                image_type,
                uploaded_by_user_id
            )
            VALUES (
                %s,
                %s,
                'after',
                %s
            )
            """,
            (
                assignment["report_id"],
                after_image_path,
                user_id,
            ),
        )

        cursor.execute(
            """
            UPDATE task_assignments
            SET
                assignment_status = 'completed',
                completed_at = NOW()
            WHERE assignment_id = %s
              AND employee_id = %s
            """,
            (
                assignment_id,
                employee_id,
            ),
        )

        cursor.execute(
            """
            UPDATE waste_reports
            SET
                report_status = 'completed',
                completed_at = NOW()
            WHERE report_id = %s
            """,
            (assignment["report_id"],),
        )

        connection.commit()

        return {
            "cleanup_id": cleanup_id,
            "assignment_id": assignment_id,
            "report_id": assignment["report_id"],
            "verification_status": "pending",
            "total_waste_kg": round(total_waste_kg, 2),
            "recycled_waste_kg": round(recycled_waste_kg, 2),
            "composted_waste_kg": round(composted_waste_kg, 2),
            "properly_disposed_kg": round(
                properly_disposed_kg,
                2,
            ),
            "hazardous_waste_kg": round(
                hazardous_waste_kg,
                2,
            ),
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()