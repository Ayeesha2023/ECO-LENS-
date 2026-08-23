import hashlib
import os
import secrets
from datetime import (
    datetime,
    timedelta,
)

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)


load_dotenv()


authority_employee_invite_bp = Blueprint(
    "authority_employee_invite",
    __name__,
    url_prefix="/api/authority/employee-invites",
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


def _digest(
    code: str,
):
    return hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()


def _require_authority():
    user_id = session.get(
        "user_id"
    )

    role = session.get(
        "role"
    )

    if user_id is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "You must log in first.",
                }
            ),
            401,
        )

    if role != "community_authority":
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "Community Authority access required.",
                }
            ),
            403,
        )

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                ca.authority_id,
                ca.user_id,
                ca.assigned_region_id,
                ca.organization_name,
                ca.approval_status,

                u.account_status,
                u.full_name

            FROM community_authorities AS ca

            JOIN users AS u
                ON u.user_id =
                   ca.user_id

            WHERE ca.user_id = %s

            LIMIT 1
            """,
            (user_id,),
        )

        authority = cursor.fetchone()

    finally:
        cursor.close()
        connection.close()

    if authority is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "Community Authority profile was not found.",
                }
            ),
            403,
        )

    if (
        authority[
            "approval_status"
        ] != "approved"

        or

        authority[
            "account_status"
        ] != "active"
    ):
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "This Community Authority is not active and approved.",
                }
            ),
            403,
        )

    return authority, None


# ============================================================
# LIST INVITES
# ============================================================

@authority_employee_invite_bp.get(
    ""
)
def list_employee_invites():
    authority, error = (
        _require_authority()
    )

    if error:
        return error

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:
        cursor.execute(
            """
            SELECT
                invite_id,
                employee_code,
                job_title,
                expires_at,
                used_by_user_id,
                used_at,
                is_active,
                created_at,

                CASE
                    WHEN used_at IS NOT NULL
                        THEN 'used'

                    WHEN is_active = 0
                        THEN 'revoked'

                    WHEN expires_at < NOW()
                        THEN 'expired'

                    ELSE 'active'
                END AS invite_status

            FROM registration_invites

            WHERE invite_role = 'employee'
              AND authority_id = %s

            ORDER BY created_at DESC
            """,
            (
                authority[
                    "authority_id"
                ],
            ),
        )

        rows = cursor.fetchall()

        for row in rows:
            for key in (
                "expires_at",
                "used_at",
                "created_at",
            ):
                if row.get(key):
                    row[key] = (
                        row[key]
                        .isoformat()
                    )

        return jsonify(
            {
                "success": True,
                "invites": rows,
            }
        ), 200

    finally:
        cursor.close()
        connection.close()


# ============================================================
# CREATE EMPLOYEE INVITE
# ============================================================

@authority_employee_invite_bp.post(
    ""
)
def create_employee_invite():
    authority, error = (
        _require_authority()
    )

    if error:
        return error

    payload = request.get_json(
        silent=True
    ) or {}

    job_title = str(
        payload.get(
            "job_title",
            "Municipal Employee",
        )
    ).strip()

    employee_code = str(
        payload.get(
            "employee_code",
            "",
        )
    ).strip()

    try:
        expires_days = int(
            payload.get(
                "expires_days",
                7,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        expires_days = 7

    expires_days = max(
        1,
        min(
            expires_days,
            30,
        ),
    )

    if not employee_code:
        employee_code = (
            f"EMP-"
            f"{authority['authority_id']}-"
            f"{secrets.token_hex(3).upper()}"
        )

    raw_invite_code = (
        "ECO-EMP-"
        + secrets.token_hex(5).upper()
    )

    code_digest = _digest(
        raw_invite_code
    )

    expires_at = (
        datetime.now()
        + timedelta(
            days=expires_days
        )
    )

    connection = _get_connection()
    cursor = connection.cursor()

    try:
        connection.start_transaction()

        cursor.execute(
            """
            INSERT INTO registration_invites (
                invite_role,
                code_digest,
                authority_id,
                assigned_region_id,
                employee_code,
                job_title,
                expires_at,
                is_active
            )
            VALUES (
                'employee',
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                1
            )
            """,
            (
                code_digest,
                authority[
                    "authority_id"
                ],
                authority[
                    "assigned_region_id"
                ],
                employee_code,
                job_title,
                expires_at,
            ),
        )

        invite_id = int(
            cursor.lastrowid
        )

        connection.commit()

        return jsonify(
            {
                "success": True,

                "message":
                    "Employee invitation created. "
                    "Copy the code now; only its "
                    "secure digest is stored.",

                "invite": {
                    "invite_id":
                        invite_id,

                    "invite_code":
                        raw_invite_code,

                    "employee_code":
                        employee_code,

                    "job_title":
                        job_title,

                    "expires_at":
                        expires_at.isoformat(),
                },
            }
        ), 201

    except mysql.connector.IntegrityError:
        connection.rollback()

        return jsonify(
            {
                "success": False,
                "error":
                    "Employee code already exists. "
                    "Try another employee code.",
            }
        ), 400

    except Exception as exc:
        connection.rollback()

        print(
            "Employee invite creation error:",
            exc,
        )

        return jsonify(
            {
                "success": False,
                "error":
                    "Employee invitation could not be created.",
            }
        ), 500

    finally:
        cursor.close()
        connection.close()


# ============================================================
# REVOKE UNUSED INVITE
# ============================================================

@authority_employee_invite_bp.post(
    "/<int:invite_id>/revoke"
)
def revoke_employee_invite(
    invite_id,
):
    authority, error = (
        _require_authority()
    )

    if error:
        return error

    connection = _get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE registration_invites

            SET is_active = 0

            WHERE invite_id = %s
              AND invite_role = 'employee'
              AND authority_id = %s
              AND used_at IS NULL
            """,
            (
                invite_id,
                authority[
                    "authority_id"
                ],
            ),
        )

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify(
                {
                    "success": False,
                    "error":
                        "Active invitation was not found.",
                }
            ), 404

        return jsonify(
            {
                "success": True,
                "message":
                    "Invitation revoked.",
            }
        ), 200

    finally:
        cursor.close()
        connection.close()