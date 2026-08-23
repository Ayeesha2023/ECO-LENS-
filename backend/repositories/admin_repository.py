import hashlib
import os
import secrets
from datetime import datetime, timedelta
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


def _normalize_email(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Email is required.")
    email = value.strip().lower()
    if not email:
        raise ValueError("Email is required.")
    if len(email) > 190:
        raise ValueError("Email is too long.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Please enter a valid email address.")
    return email


def _validate_plaintext_password(value: Any) -> str:
    """Demo-only admin password validation. Other roles remain hashed."""
    if not isinstance(value, str):
        raise ValueError("Password is required.")
    if not value:
        raise ValueError("Password is required.")
    if len(value) > 255:
        raise ValueError("Password is too long.")
    return value


def _clean_organization_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Organization name is required.")
    organization_name = " ".join(value.strip().split())
    if len(organization_name) < 2:
        raise ValueError("Organization name is required.")
    if len(organization_name) > 190:
        raise ValueError("Organization name is too long.")
    return organization_name


def _digest_invite_code(raw_code: str) -> str:
    return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()


def _safe_admin(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": int(row["admin_id"]),
        "admin_id": int(row["admin_id"]),
        "role": "admin",
        "role_display": "Administrator",
        "full_name": row["admin_name"],
        "email": row["email"],
        "account_status": "active" if int(row["is_active"]) else "inactive",
        "redirect_path": "/admin",
    }


def authenticate_admin(email: Any, password: Any) -> dict[str, Any]:
    email = _normalize_email(email)
    password = _validate_plaintext_password(password)

    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT admin_id, admin_name, email, password, is_active, created_at
            FROM admins
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
            """,
            (email,),
        )
        admin = cursor.fetchone()
        if admin is None or str(admin["password"]) != password:
            raise ValueError("Email or password is incorrect.")
        if not int(admin["is_active"]):
            raise PermissionError("This administrator account is inactive.")
        return _safe_admin(admin)
    finally:
        cursor.close()
        connection.close()


def get_admin_by_id(admin_id: int) -> dict[str, Any] | None:
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT admin_id, admin_name, email, password, is_active, created_at
            FROM admins
            WHERE admin_id = %s
            LIMIT 1
            """,
            (admin_id,),
        )
        admin = cursor.fetchone()
        if admin is None:
            return None
        if not int(admin["is_active"]):
            raise PermissionError("This administrator account is inactive.")
        return _safe_admin(admin)
    finally:
        cursor.close()
        connection.close()


def create_authority_invite(*, organization_name: Any, valid_days: int = 30) -> dict[str, Any]:
    organization_name = _clean_organization_name(organization_name)
    try:
        valid_days = int(valid_days)
    except (TypeError, ValueError) as exc:
        raise ValueError("valid_days must be an integer.") from exc
    if valid_days < 1:
        raise ValueError("valid_days must be at least 1.")
    if valid_days > 90:
        raise ValueError("valid_days cannot exceed 90.")

    raw_invite_code = "ECO-AUTH-" + secrets.token_hex(6).upper()
    code_digest = _digest_invite_code(raw_invite_code)
    expires_at = datetime.now() + timedelta(days=valid_days)

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
                organization_name,
                employee_code,
                job_title,
                expires_at,
                is_active
            )
            VALUES (
                'community_authority',
                %s,
                NULL,
                NULL,
                %s,
                NULL,
                NULL,
                %s,
                1
            )
            """,
            (code_digest, organization_name, expires_at),
        )
        invite_id = int(cursor.lastrowid)
        connection.commit()
        return {
            "invite_id": invite_id,
            "invite_code": raw_invite_code,
            "organization_name": organization_name,
            "expires_at": expires_at.isoformat(),
            "invite_role": "community_authority",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def list_authority_invites():
    connection = _get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                invite_id,
                organization_name,
                expires_at,
                used_by_user_id,
                used_at,
                is_active,
                created_at,
                CASE
                    WHEN used_at IS NOT NULL THEN 'used'
                    WHEN is_active = 0 THEN 'revoked'
                    WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 'expired'
                    ELSE 'active'
                END AS invite_status
            FROM registration_invites
            WHERE invite_role = 'community_authority'
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            for key in ("expires_at", "used_at", "created_at"):
                if row.get(key):
                    row[key] = row[key].isoformat()
        return rows
    finally:
        cursor.close()
        connection.close()