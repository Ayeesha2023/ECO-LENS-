import os

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Blueprint,
    jsonify,
    session,
)


load_dotenv()


authority_cleanup_verification_bp = Blueprint(
    "authority_cleanup_verification",
    __name__,
    url_prefix="/api/authority/cleanup-verification",
)


def _get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "eco-lens_db"),
        autocommit=False,
    )


def _authority_id_from_session():
    user_id = session.get(
        "user_id"
    )

    role = session.get(
        "role"
    )

    if (
        user_id is None
        or
        role != "community_authority"
    ):
        return None

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                ca.authority_id

            FROM community_authorities AS ca

            JOIN users AS u
                ON u.user_id =
                   ca.user_id

            WHERE ca.user_id = %s
              AND ca.approval_status =
                  'approved'
              AND u.account_status =
                  'active'

            LIMIT 1
            """,
            (user_id,),
        )

        row = cursor.fetchone()

        if row:
            return int(
                row[
                    "authority_id"
                ]
            )

        return None

    finally:
        cursor.close()
        connection.close()


# ============================================================
# PENDING CLEANUPS
# ============================================================

@authority_cleanup_verification_bp.get(
    "/pending"
)
def pending_cleanups():
    authority_id = (
        _authority_id_from_session()
    )

    if authority_id is None:
        return jsonify(
            {
                "success": False,
                "error":
                    "Approved Community Authority access required.",
            }
        ), 403

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                cr.cleanup_id,
                cr.assignment_id,
                cr.employee_id,
                cr.report_id,
                cr.cleaned_at,
                cr.total_waste_kg,
                cr.recycled_waste_kg,
                cr.composted_waste_kg,
                cr.properly_disposed_kg,
                cr.hazardous_waste_kg,
                cr.cleanup_notes,
                cr.verification_status,

                wr.title AS report_title,
                wr.address_text,

                u.full_name AS employee_name

            FROM cleanup_records AS cr

            JOIN task_assignments AS ta
                ON ta.assignment_id =
                   cr.assignment_id

            JOIN waste_reports AS wr
                ON wr.report_id =
                   cr.report_id

            JOIN employees AS e
                ON e.employee_id =
                   cr.employee_id

            JOIN users AS u
                ON u.user_id =
                   e.user_id

            WHERE ta.assigned_by_authority_id =
                  %s

              AND cr.verification_status =
                  'pending'

            ORDER BY cr.cleaned_at DESC
            """,
            (authority_id,),
        )

        cleanups = cursor.fetchall()

        for cleanup in cleanups:
            if cleanup.get(
                "cleaned_at"
            ):
                cleanup[
                    "cleaned_at"
                ] = (
                    cleanup[
                        "cleaned_at"
                    ].isoformat()
                )

            cursor.execute(
                """
                SELECT
                    ccb.model_class_id,
                    ccb.weight_kg,
                    ccb.handling_method,
                    ccb.notes,

                    mc.display_name
                        AS class_name,

                    wc.category_name

                FROM cleanup_class_breakdown
                    AS ccb

                JOIN model_classes AS mc
                    ON mc.model_class_id =
                       ccb.model_class_id

                JOIN waste_categories AS wc
                    ON wc.category_id =
                       ccb.category_id

                WHERE ccb.cleanup_id =
                      %s

                ORDER BY mc.model_class_id
                """,
                (
                    cleanup[
                        "cleanup_id"
                    ],
                ),
            )

            breakdown = cursor.fetchall()

            for item in breakdown:
                item[
                    "weight_kg"
                ] = float(
                    item[
                        "weight_kg"
                    ]
                )

            cleanup[
                "waste_breakdown"
            ] = breakdown

            for key in (
                "total_waste_kg",
                "recycled_waste_kg",
                "composted_waste_kg",
                "properly_disposed_kg",
                "hazardous_waste_kg",
            ):
                cleanup[key] = float(
                    cleanup[key]
                )

        return jsonify(
            {
                "success": True,
                "cleanups":
                    cleanups,
            }
        ), 200

    finally:
        cursor.close()
        connection.close()


# ============================================================
# VERIFY / REJECT
# ============================================================

@authority_cleanup_verification_bp.post(
    "/<int:cleanup_id>/<string:decision>"
)
def review_cleanup(
    cleanup_id,
    decision,
):
    authority_id = (
        _authority_id_from_session()
    )

    if authority_id is None:
        return jsonify(
            {
                "success": False,
                "error":
                    "Approved Community Authority access required.",
            }
        ), 403

    if decision not in {
        "verify",
        "reject",
    }:
        return jsonify(
            {
                "success": False,
                "error":
                    "Decision must be verify or reject.",
            }
        ), 400

    new_status = (
        "verified"
        if decision == "verify"
        else "rejected"
    )

    connection = _get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE cleanup_records AS cr

            JOIN task_assignments AS ta
                ON ta.assignment_id =
                   cr.assignment_id

            SET
                cr.verification_status = %s,
                cr.verified_by_authority_id = %s,
                cr.verified_at = NOW()

            WHERE cr.cleanup_id = %s
              AND ta.assigned_by_authority_id =
                  %s
              AND cr.verification_status =
                  'pending'
            """,
            (
                new_status,
                authority_id,
                cleanup_id,
                authority_id,
            ),
        )

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify(
                {
                    "success": False,
                    "error":
                        "Pending cleanup record was not found.",
                }
            ), 404

        return jsonify(
            {
                "success": True,

                "message":
                    f"Cleanup {new_status}.",

                "verification_status":
                    new_status,
            }
        ), 200

    finally:
        cursor.close()
        connection.close()