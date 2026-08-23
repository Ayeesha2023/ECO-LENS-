import os

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# DATABASE
# ============================================================

def _get_connection():

    return mysql.connector.connect(
        host=os.getenv(
            "DB_HOST",
            "127.0.0.1",
        ),
        port=int(
            os.getenv(
                "DB_PORT",
                "3306",
            )
        ),
        user=os.getenv(
            "DB_USER",
            "root",
        ),
        password=os.getenv(
            "DB_PASSWORD",
            "",
        ),
        database=os.getenv(
            "DB_NAME",
            "eco-lens_db",
        ),
        autocommit=False,
    )


# ============================================================
# JSON SAFE VALUES
# ============================================================

def _safe_value(
    value: Any,
):

    if isinstance(
        value,
        Decimal,
    ):
        return float(value)

    if isinstance(
        value,
        (datetime, date),
    ):
        return value.isoformat()

    return value


def _safe_row(
    row: dict | None,
):

    if row is None:
        return None

    return {
        key: _safe_value(value)
        for key, value
        in row.items()
    }


def _safe_rows(
    rows: list[dict],
):

    return [
        _safe_row(row)
        for row in rows
    ]


# ============================================================
# AUTHORITY FROM LOGGED-IN USER
# ============================================================

def get_authority_for_user(
    user_id: int,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT
                ca.authority_id,
                ca.user_id,
                ca.organization_name,
                ca.assigned_region_id,
                ca.approval_status,

                u.full_name,
                u.email,
                u.phone,
                u.account_status,

                r.region_name
                    AS primary_region_name,
                r.region_type
                    AS primary_region_type

            FROM community_authorities AS ca

            JOIN users AS u
                ON u.user_id =
                   ca.user_id

            JOIN regions AS r
                ON r.region_id =
                   ca.assigned_region_id

            WHERE ca.user_id = %s

            LIMIT 1
            """,
            (
                user_id,
            ),
        )

        return _safe_row(
            cursor.fetchone()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# COVERAGE WARDS
# ============================================================

def get_authority_coverage(
    authority_id: int,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT DISTINCT
                r.region_id,
                r.region_code,
                r.region_name,
                r.region_type,

                CASE
                    WHEN r.region_id =
                         ca.assigned_region_id
                    THEN 1
                    ELSE 0
                END AS is_primary

            FROM community_authorities AS ca

            JOIN regions AS r
                ON (
                    r.region_id =
                    ca.assigned_region_id

                    OR r.region_id IN (
                        SELECT ar.region_id

                        FROM authority_regions AS ar

                        WHERE ar.authority_id =
                              ca.authority_id
                    )
                )

            WHERE ca.authority_id = %s

              AND r.is_active = 1

            ORDER BY
                is_primary DESC,
                r.region_name
            """,
            (
                authority_id,
            ),
        )

        return _safe_rows(
            cursor.fetchall()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# REPORTS
# ============================================================

def get_authority_reports(
    authority_id: int,
    status: str | None = None,
    limit: int = 100,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        sql = """
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

                wr.estimated_severity,
                wr.report_status,

                wr.submitted_at,
                wr.updated_at,
                wr.completed_at,

                reporter.full_name
                    AS reporter_name,

                reporter.email
                    AS reporter_email,

                r.region_name,
                r.region_type,

                (
                    SELECT ri.image_path

                    FROM report_images AS ri

                    WHERE ri.report_id =
                          wr.report_id

                      AND ri.image_type =
                          'before'

                    ORDER BY
                        ri.created_at ASC

                    LIMIT 1
                ) AS before_image_path,

                (
                    SELECT COUNT(*)

                    FROM task_assignments AS ta

                    WHERE ta.report_id =
                          wr.report_id

                      AND ta.assignment_status
                          NOT IN (
                              'completed',
                              'cancelled'
                          )
                ) AS active_assignment_count

            FROM waste_reports AS wr

            JOIN users AS reporter
                ON reporter.user_id =
                   wr.reporter_user_id

            JOIN regions AS r
                ON r.region_id =
                   wr.region_id

            WHERE (
                wr.authority_id = %s

                OR wr.region_id = (
                    SELECT
                        ca.assigned_region_id

                    FROM community_authorities
                        AS ca

                    WHERE ca.authority_id = %s

                    LIMIT 1
                )

                OR wr.region_id IN (
                    SELECT ar.region_id

                    FROM authority_regions
                        AS ar

                    WHERE ar.authority_id = %s
                )
            )
        """

        params: list[Any] = [
            authority_id,
            authority_id,
            authority_id,
        ]


        if status:

            allowed_statuses = {
                "submitted",
                "under_review",
                "assigned",
                "in_progress",
                "completed",
                "rejected",
                "cancelled",
            }

            if status not in allowed_statuses:

                raise ValueError(
                    "Invalid report status."
                )

            sql += """
                AND wr.report_status = %s
            """

            params.append(
                status
            )


        sql += """
            ORDER BY
                wr.submitted_at DESC

            LIMIT %s
        """

        params.append(
            int(limit)
        )


        cursor.execute(
            sql,
            tuple(params),
        )

        return _safe_rows(
            cursor.fetchall()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# SINGLE REPORT
# ============================================================

def get_authority_report(
    authority_id: int,
    report_id: int,
):

    reports = get_authority_reports(
        authority_id=authority_id,
        limit=500,
    )

    report = next(
        (
            item
            for item in reports
            if int(
                item["report_id"]
            ) == int(report_id)
        ),
        None,
    )

    if report is None:

        return None


    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

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

            ORDER BY
                ri.created_at ASC
            """,
            (
                report_id,
            ),
        )

        images = _safe_rows(
            cursor.fetchall()
        )


        cursor.execute(
            """
            SELECT
                ta.assignment_id,
                ta.employee_id,
                ta.assignment_notes,
                ta.priority,
                ta.assignment_status,
                ta.assigned_at,
                ta.accepted_at,
                ta.started_at,
                ta.completed_at,

                u.full_name
                    AS employee_name,

                e.employee_code,
                e.job_title

            FROM task_assignments AS ta

            JOIN employees AS e
                ON e.employee_id =
                   ta.employee_id

            JOIN users AS u
                ON u.user_id =
                   e.user_id

            WHERE ta.report_id = %s

              AND ta.assigned_by_authority_id =
                  %s

            ORDER BY
                ta.assigned_at DESC
            """,
            (
                report_id,
                authority_id,
            ),
        )

        assignments = _safe_rows(
            cursor.fetchall()
        )


        report["images"] = images
        report["assignments"] = assignments

        return report

    finally:

        cursor.close()
        connection.close()


# ============================================================
# EMPLOYEES
# ============================================================

def get_authority_employees(
    authority_id: int,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT
                e.employee_id,
                e.employee_code,
                e.job_title,
                e.employment_status,
                e.joined_at,

                u.user_id,
                u.full_name,
                u.email,
                u.phone,

                COUNT(
                    DISTINCT CASE

                        WHEN ta.assignment_status
                             IN (
                                'assigned',
                                'accepted',
                                'in_progress'
                             )

                        THEN ta.assignment_id

                    END
                ) AS active_assignments,

                COUNT(
                    DISTINCT CASE

                        WHEN ta.assignment_status =
                             'completed'

                        THEN ta.assignment_id

                    END
                ) AS completed_assignments

            FROM employees AS e

            JOIN users AS u
                ON u.user_id =
                   e.user_id

            LEFT JOIN task_assignments AS ta
                ON ta.employee_id =
                   e.employee_id

            WHERE e.authority_id = %s

            GROUP BY
                e.employee_id,
                e.employee_code,
                e.job_title,
                e.employment_status,
                e.joined_at,

                u.user_id,
                u.full_name,
                u.email,
                u.phone

            ORDER BY
                e.employment_status,
                u.full_name
            """,
            (
                authority_id,
            ),
        )

        return _safe_rows(
            cursor.fetchall()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ASSIGNMENTS
# ============================================================

def get_authority_assignments(
    authority_id: int,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT
                ta.assignment_id,
                ta.report_id,
                ta.employee_id,

                ta.assignment_notes,
                ta.priority,
                ta.assignment_status,

                ta.assigned_at,
                ta.accepted_at,
                ta.started_at,
                ta.completed_at,

                wr.title
                    AS report_title,

                wr.address_text,
                wr.latitude,
                wr.longitude,

                wr.region_id,
                r.region_name,

                u.full_name
                    AS employee_name,

                e.employee_code,
                e.job_title

            FROM task_assignments AS ta

            JOIN waste_reports AS wr
                ON wr.report_id =
                   ta.report_id

            JOIN regions AS r
                ON r.region_id =
                   wr.region_id

            JOIN employees AS e
                ON e.employee_id =
                   ta.employee_id

            JOIN users AS u
                ON u.user_id =
                   e.user_id

            WHERE ta.assigned_by_authority_id =
                  %s

            ORDER BY
                ta.assigned_at DESC
            """,
            (
                authority_id,
            ),
        )

        return _safe_rows(
            cursor.fetchall()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# ANALYTICS
# ============================================================

def get_authority_analytics_summary(
    authority_id: int,
):

    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        cursor.execute(
            """
            SELECT *

            FROM v_authority_community_analytics

            WHERE authority_id = %s

            LIMIT 1
            """,
            (
                authority_id,
            ),
        )

        return _safe_row(
            cursor.fetchone()
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def build_dashboard_summary(
    authority_id: int,
):

    reports = get_authority_reports(
        authority_id
    )

    employees = get_authority_employees(
        authority_id
    )

    assignments = get_authority_assignments(
        authority_id
    )


    open_reports = sum(
        1
        for report in reports
        if report["report_status"]
        in {
            "submitted",
            "under_review",
            "assigned",
            "in_progress",
        }
    )


    new_reports = sum(
        1
        for report in reports
        if report["report_status"]
        == "submitted"
    )


    completed_reports = sum(
        1
        for report in reports
        if report["report_status"]
        == "completed"
    )


    active_assignments = sum(
        1
        for assignment in assignments
        if assignment[
            "assignment_status"
        ]
        in {
            "assigned",
            "accepted",
            "in_progress",
        }
    )


    active_employees = sum(
        1
        for employee in employees
        if employee[
            "employment_status"
        ] == "active"
    )


    return {
        "total_reports":
            len(reports),

        "new_reports":
            new_reports,

        "open_reports":
            open_reports,

        "completed_reports":
            completed_reports,

        "active_assignments":
            active_assignments,

        "active_employees":
            active_employees,
    }


# ============================================================
# CREATE ASSIGNMENT
# ============================================================

def assign_employee_to_report(
    authority_id: int,
    report_id: int,
    employee_id: int,
    priority: str,
    assignment_notes: str | None,
):

    allowed_priorities = {
        "low",
        "medium",
        "high",
        "urgent",
    }


    if priority not in allowed_priorities:

        raise ValueError(
            "Invalid assignment priority."
        )


    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )


    try:

        connection.start_transaction()


        # ----------------------------------------------------
        # CHECK REPORT BELONGS TO AUTHORITY COVERAGE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                wr.report_id,
                wr.report_status

            FROM waste_reports AS wr

            WHERE wr.report_id = %s

              AND (
                    wr.authority_id = %s

                    OR wr.region_id = (
                        SELECT
                            ca.assigned_region_id

                        FROM community_authorities
                            AS ca

                        WHERE ca.authority_id =
                              %s

                        LIMIT 1
                    )

                    OR wr.region_id IN (
                        SELECT
                            ar.region_id

                        FROM authority_regions
                            AS ar

                        WHERE ar.authority_id =
                              %s
                    )
              )

            LIMIT 1

            FOR UPDATE
            """,
            (
                report_id,
                authority_id,
                authority_id,
                authority_id,
            ),
        )


        report = (
            cursor.fetchone()
        )


        if report is None:

            raise ValueError(
                "Report was not found in "
                "this authority's coverage."
            )


        if report[
            "report_status"
        ] in {
            "completed",
            "rejected",
            "cancelled",
        }:

            raise ValueError(
                "This report can no longer "
                "be assigned."
            )


        # ----------------------------------------------------
        # CHECK EMPLOYEE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                employee_id,
                employment_status

            FROM employees

            WHERE employee_id = %s

              AND authority_id = %s

            LIMIT 1
            """,
            (
                employee_id,
                authority_id,
            ),
        )


        employee = (
            cursor.fetchone()
        )


        if employee is None:

            raise ValueError(
                "The selected employee does "
                "not belong to this authority."
            )


        if employee[
            "employment_status"
        ] != "active":

            raise ValueError(
                "The selected employee is "
                "not currently active."
            )


        # ----------------------------------------------------
        # PREVENT DOUBLE ACTIVE ASSIGNMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                assignment_id

            FROM task_assignments

            WHERE report_id = %s

              AND assignment_status IN (
                    'assigned',
                    'accepted',
                    'in_progress'
              )

            LIMIT 1
            """,
            (
                report_id,
            ),
        )


        if cursor.fetchone():

            raise ValueError(
                "This report already has "
                "an active assignment."
            )


        # ----------------------------------------------------
        # CREATE ASSIGNMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO task_assignments (
                report_id,
                employee_id,
                assigned_by_authority_id,
                assignment_notes,
                priority,
                assignment_status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                'assigned'
            )
            """,
            (
                report_id,
                employee_id,
                authority_id,
                assignment_notes,
                priority,
            ),
        )


        assignment_id = int(
            cursor.lastrowid
        )


        # ----------------------------------------------------
        # UPDATE REPORT
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE waste_reports

            SET
                authority_id = %s,
                report_status = 'assigned'

            WHERE report_id = %s
            """,
            (
                authority_id,
                report_id,
            ),
        )


        connection.commit()


        return {
            "assignment_id":
                assignment_id,

            "report_id":
                report_id,

            "employee_id":
                employee_id,

            "priority":
                priority,

            "assignment_status":
                "assigned",
        }


    except Exception:

        connection.rollback()
        raise


    finally:

        cursor.close()
        connection.close()


# ============================================================
# BOOTSTRAP EVERYTHING NEEDED BY REACT
# ============================================================

def build_authority_dashboard(
    user_id: int,
):

    authority = get_authority_for_user(
        user_id
    )


    if authority is None:

        raise ValueError(
            "Community Authority account "
            "was not found."
        )


    authority_id = int(
        authority[
            "authority_id"
        ]
    )


    return {
        "authority":
            authority,

        "summary":
            build_dashboard_summary(
                authority_id
            ),

        "reports":
            get_authority_reports(
                authority_id,
                limit=50,
            ),

        "employees":
            get_authority_employees(
                authority_id
            ),

        "assignments":
            get_authority_assignments(
                authority_id
            ),

        "coverage":
            get_authority_coverage(
                authority_id
            ),

        "analytics":
            get_authority_analytics_summary(
                authority_id
            ),
    }