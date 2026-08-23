import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash


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
# BASIC VALIDATION
# ============================================================

def _clean_text(
    value: Any,
    field_name: str,
    required: bool = True,
    max_length: int | None = None,
) -> str | None:

    if value is None:
        if required:
            raise ValueError(
                f"{field_name} is required."
            )

        return None

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be text."
        )

    value = value.strip()

    if not value:
        if required:
            raise ValueError(
                f"{field_name} is required."
            )

        return None

    if (
        max_length is not None
        and len(value) > max_length
    ):
        raise ValueError(
            f"{field_name} is too long."
        )

    return value


def _normalize_email(
    value: Any,
) -> str:

    email = _clean_text(
        value,
        "Email",
        max_length=190,
    )

    assert email is not None

    email = email.lower()

    if (
        "@" not in email
        or "." not in email.split("@")[-1]
    ):
        raise ValueError(
            "Please enter a valid email address."
        )

    return email


def _validate_password(
    value: Any,
) -> str:

    if not isinstance(value, str):
        raise ValueError(
            "Password is required."
        )

    if len(value) < 8:
        raise ValueError(
            "Password must contain at least "
            "8 characters."
        )

    if len(value) > 128:
        raise ValueError(
            "Password is too long."
        )

    return value


def _parse_positive_int(
    value: Any,
    field_name: str,
) -> int:

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} is invalid."
        )

    try:
        result = int(value)

    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} is invalid."
        ) from exc

    if result <= 0:
        raise ValueError(
            f"{field_name} is invalid."
        )

    return result


# ============================================================
# INVITATION CODE HASHING
# ============================================================

def _invite_digest(
    invite_code: str,
) -> str:

    normalized = (
        invite_code
        .strip()
        .upper()
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


# ============================================================
# SIGNUP LOCATION DATA
# ============================================================

def get_signup_locations() -> dict[str, Any]:
    """
    Return:
    1. Household local areas.
    2. Authority-selectable wards.

    Only real, active areas linked to an active ward are shown.
    """

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        # ----------------------------------------------------
        # HOUSEHOLD AREAS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                area.region_id
                    AS area_region_id,

                area.region_name
                    AS area_name,

                ward.region_id
                    AS ward_region_id,

                ward.region_name
                    AS ward_name,

                ward.region_code
                    AS ward_code,

                zone.region_id
                    AS zone_region_id,

                zone.region_name
                    AS zone_name,

                city.region_id
                    AS city_corporation_region_id,

                city.region_name
                    AS city_corporation_name

            FROM regions AS area

            JOIN regions AS ward
                ON ward.region_id =
                   area.parent_region_id

               AND ward.region_type =
                   'ward'

               AND ward.is_active = 1

            JOIN regions AS zone
                ON zone.region_id =
                   ward.parent_region_id

               AND zone.region_type =
                   'zone'

               AND zone.is_active = 1

            JOIN regions AS city
                ON city.region_id =
                   zone.parent_region_id

               AND city.region_type =
                   'city_corporation'

               AND city.is_active = 1

            WHERE area.region_type =
                  'area'

              AND area.is_active = 1

            ORDER BY
                area.region_name
            """
        )

        household_areas = (
            cursor.fetchall()
        )


        # ----------------------------------------------------
        # AUTHORITY WARDS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                ward.region_id
                    AS ward_region_id,

                ward.region_name
                    AS ward_name,

                ward.region_code
                    AS ward_code,

                zone.region_id
                    AS zone_region_id,

                zone.region_name
                    AS zone_name,

                city.region_id
                    AS city_corporation_region_id,

                city.region_name
                    AS city_corporation_name,

                GROUP_CONCAT(
                    DISTINCT area.region_name
                    ORDER BY area.region_name
                    SEPARATOR ', '
                ) AS area_summary

            FROM regions AS ward

            JOIN regions AS zone
                ON zone.region_id =
                   ward.parent_region_id

               AND zone.region_type =
                   'zone'

               AND zone.is_active = 1

            JOIN regions AS city
                ON city.region_id =
                   zone.parent_region_id

               AND city.region_type =
                   'city_corporation'

               AND city.is_active = 1

            LEFT JOIN regions AS area
                ON area.parent_region_id =
                   ward.region_id

               AND area.region_type =
                   'area'

               AND area.is_active = 1

            WHERE ward.region_type =
                  'ward'

              AND ward.is_active = 1

            GROUP BY
                ward.region_id,
                ward.region_name,
                ward.region_code,
                zone.region_id,
                zone.region_name,
                city.region_id,
                city.region_name

            ORDER BY
                zone.region_name,
                ward.region_name
            """
        )

        authority_wards = (
            cursor.fetchall()
        )

        return {
            "household_areas":
                household_areas,

            "authority_wards":
                authority_wards,
        }

    finally:
        cursor.close()
        connection.close()


# ============================================================
# HOUSEHOLD AREA VALIDATION
# ============================================================

def _get_household_area(
    cursor,
    area_region_id: Any,
) -> dict[str, Any]:

    area_region_id = (
        _parse_positive_int(
            area_region_id,
            "Area",
        )
    )

    cursor.execute(
        """
        SELECT
            area.region_id
                AS area_region_id,

            area.region_name
                AS area_name,

            ward.region_id
                AS ward_region_id,

            ward.region_name
                AS ward_name,

            city.region_id
                AS city_corporation_region_id,

            city.region_name
                AS city_corporation_name

        FROM regions AS area

        JOIN regions AS ward
            ON ward.region_id =
               area.parent_region_id

           AND ward.region_type =
               'ward'

           AND ward.is_active = 1

        JOIN regions AS zone
            ON zone.region_id =
               ward.parent_region_id

           AND zone.region_type =
               'zone'

           AND zone.is_active = 1

        JOIN regions AS city
            ON city.region_id =
               zone.parent_region_id

           AND city.region_type =
               'city_corporation'

           AND city.is_active = 1

        WHERE area.region_id = %s

          AND area.region_type =
              'area'

          AND area.is_active = 1

        LIMIT 1
        """,
        (
            area_region_id,
        ),
    )

    result = cursor.fetchone()

    if result is None:
        raise ValueError(
            "The selected household area "
            "is not available."
        )

    return result


# ============================================================
# AUTHORITY WARD VALIDATION
# ============================================================

def _validate_authority_wards(
    cursor,
    values: Any,
) -> list[int]:

    if not isinstance(values, list):
        raise ValueError(
            "Please select at least one "
            "authority ward."
        )

    ward_ids = []

    for value in values:

        ward_id = _parse_positive_int(
            value,
            "Ward",
        )

        if ward_id not in ward_ids:
            ward_ids.append(
                ward_id
            )

    if not ward_ids:
        raise ValueError(
            "Please select at least one "
            "authority ward."
        )

    if len(ward_ids) > 20:
        raise ValueError(
            "Too many wards were selected."
        )

    placeholders = ", ".join(
        ["%s"] * len(ward_ids)
    )

    cursor.execute(
        f"""
        SELECT
            ward.region_id
                AS ward_region_id,

            city.region_id
                AS city_corporation_region_id,

            city.region_name
                AS city_corporation_name

        FROM regions AS ward

        JOIN regions AS zone
            ON zone.region_id =
               ward.parent_region_id

           AND zone.region_type =
               'zone'

           AND zone.is_active = 1

        JOIN regions AS city
            ON city.region_id =
               zone.parent_region_id

           AND city.region_type =
               'city_corporation'

           AND city.is_active = 1

        WHERE ward.region_id IN (
            {placeholders}
        )

          AND ward.region_type =
              'ward'

          AND ward.is_active = 1
        """,
        tuple(ward_ids),
    )

    valid_rows = cursor.fetchall()

    valid_ids = {
        int(
            row[
                "ward_region_id"
            ]
        )
        for row in valid_rows
    }

    if valid_ids != set(ward_ids):
        raise ValueError(
            "One or more selected wards "
            "are not available."
        )

    city_ids = {
        int(
            row[
                "city_corporation_region_id"
            ]
        )
        for row in valid_rows
    }

    if len(city_ids) != 1:
        raise ValueError(
            "All selected wards must belong "
            "to the same City Corporation."
        )

    return ward_ids


# ============================================================
# CREATE REGISTRATION INVITATION
# ============================================================

def create_registration_invite(
    invite_role: str,
    authority_id: int | None = None,
    assigned_region_id: int | None = None,
    employee_code: str | None = None,
    job_title: str | None = None,
    valid_days: int = 30,
) -> str:

    if invite_role not in {
        "employee",
        "community_authority",
    }:
        raise ValueError(
            "Invalid invitation role."
        )

    if valid_days <= 0:
        raise ValueError(
            "valid_days must be positive."
        )

    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        if invite_role == "employee":

            if authority_id is None:
                raise ValueError(
                    "Employee invitations "
                    "require an authority_id."
                )

            employee_code = _clean_text(
                employee_code,
                "Employee code",
                max_length=50,
            )

            cursor.execute(
                """
                SELECT
                    ca.authority_id,

                    ca.assigned_region_id,

                    ca.approval_status,

                    u.account_status

                FROM community_authorities
                    AS ca

                JOIN users AS u
                    ON u.user_id =
                       ca.user_id

                WHERE ca.authority_id =
                      %s

                  AND ca.approval_status =
                      'approved'

                  AND u.account_status =
                      'active'

                LIMIT 1
                """,
                (
                    authority_id,
                ),
            )

            authority = (
                cursor.fetchone()
            )

            if authority is None:
                raise ValueError(
                    "The selected authority "
                    "is not approved and active."
                )

            assigned_region_id = int(
                authority[
                    "assigned_region_id"
                ]
            )


        prefix = (
            "EMP"
            if invite_role == "employee"
            else "AUTH"
        )

        raw_code = (
            f"{prefix}-"
            f"{secrets.token_hex(6).upper()}"
        )

        digest = _invite_digest(
            raw_code
        )

        expires_at = (
            datetime.now()
            + timedelta(
                days=valid_days
            )
        )

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
                %s,
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
                invite_role,
                digest,
                authority_id,
                assigned_region_id,
                employee_code,
                job_title,
                expires_at,
            ),
        )

        connection.commit()

        return raw_code

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# GET VALID INVITE
# ============================================================

def _get_invite_for_update(
    cursor,
    invite_code: Any,
    expected_role: str,
) -> dict[str, Any]:

    invite_code = _clean_text(
        invite_code,
        "Registration code",
        max_length=100,
    )

    assert invite_code is not None

    digest = _invite_digest(
        invite_code
    )

    cursor.execute(
        """
        SELECT
            ri.invite_id,
            ri.invite_role,
            ri.authority_id,
            ri.assigned_region_id,
            ri.organization_name,
            ri.employee_code,
            ri.job_title,
            ri.expires_at,
            ri.used_by_user_id,
            ri.is_active,

            ca.approval_status
                AS authority_approval_status,

            authority_user.account_status
                AS authority_account_status

        FROM registration_invites
            AS ri

        LEFT JOIN community_authorities
            AS ca

            ON ca.authority_id =
               ri.authority_id

        LEFT JOIN users
            AS authority_user

            ON authority_user.user_id =
               ca.user_id

        WHERE ri.code_digest = %s

          AND ri.invite_role = %s

          AND ri.is_active = 1

          AND ri.used_by_user_id
              IS NULL

          AND (
              ri.expires_at IS NULL

              OR ri.expires_at >
                 NOW()
          )

        LIMIT 1

        FOR UPDATE
        """,
        (
            digest,
            expected_role,
        ),
    )

    invite = cursor.fetchone()

    if invite is None:
        raise ValueError(
            "The registration code is "
            "invalid, expired, or already used."
        )

    if expected_role == "employee":

        if (
            invite.get(
                "authority_approval_status"
            )
            != "approved"

            or invite.get(
                "authority_account_status"
            )
            != "active"
        ):
            raise ValueError(
                "The authority connected to "
                "this employee invitation "
                "is not active."
            )

    return invite


# ============================================================
# REGISTER USER
# ============================================================

def register_user(
    payload: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(payload, dict):
        raise ValueError(
            "Invalid signup request."
        )


    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    frontend_role = _clean_text(
        payload.get("role"),
        "Role",
        max_length=40,
    )

    role_map = {
        "household":
            "household",

        "employee":
            "employee",

        "authority":
            "community_authority",

        "community_authority":
            "community_authority",
    }

    if frontend_role not in role_map:
        raise ValueError(
            "Please select a valid role."
        )

    role = role_map[
        frontend_role
    ]


    # --------------------------------------------------------
    # COMMON DATA
    # --------------------------------------------------------

    full_name = _clean_text(
        payload.get(
            "fullName"
        ),
        "Full name",
        max_length=120,
    )

    email = _normalize_email(
        payload.get(
            "email"
        )
    )

    phone = _clean_text(
        payload.get(
            "phone"
        ),
        "Phone number",
        required=False,
        max_length=30,
    )

    address_text = _clean_text(
        payload.get(
            "addressText"
        ),
        "Address",
        required=False,
        max_length=500,
    )

    password = _validate_password(
        payload.get(
            "password"
        )
    )

    password_hash = (
        generate_password_hash(
            password
        )
    )


    connection = _get_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    try:

        connection.start_transaction()


        # ----------------------------------------------------
        # DUPLICATE EMAIL
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT user_id

            FROM users

            WHERE email = %s

            LIMIT 1
            """,
            (
                email,
            ),
        )

        if cursor.fetchone():
            raise ValueError(
                "An account with this "
                "email already exists."
            )


        # ----------------------------------------------------
        # ROLE-SPECIFIC REGION DATA
        # ----------------------------------------------------

        region_id = None
        locality_region_id = None

        household_area = None
        authority_ward_ids = []
        invite = None

        organization_name = None


        # HOUSEHOLD
        if role == "household":

            household_area = (
                _get_household_area(
                    cursor,
                    payload.get(
                        "areaRegionId"
                    ),
                )
            )

            locality_region_id = int(
                household_area[
                    "area_region_id"
                ]
            )

            # Important:
            # user.region_id stores WARD.
            region_id = int(
                household_area[
                    "ward_region_id"
                ]
            )


        # EMPLOYEE
        elif role == "employee":

            invite = (
                _get_invite_for_update(
                    cursor,
                    payload.get(
                        "inviteCode"
                    ),
                    "employee",
                )
            )

            region_id = int(
                invite[
                    "assigned_region_id"
                ]
            )


        # AUTHORITY
        elif role == "community_authority":

            invite = (
                _get_invite_for_update(
                    cursor,
                    payload.get(
                        "inviteCode"
                    ),
                    "community_authority",
                )
            )

            organization_name = (
                _clean_text(
                    payload.get(
                        "organizationName"
                    ),
                    "Organization name",
                    max_length=190,
                )
            )

            invite_organization_name = (
                invite.get(
                    "organization_name"
                )
            )

            if not invite_organization_name:
                raise ValueError(
                    "This authority registration code "
                    "is not linked to an organization. "
                    "Please use a code generated by an "
                    "EcoLens administrator."
                )

            normalized_entered_org = (
                " ".join(
                    str(
                        organization_name
                    )
                    .strip()
                    .split()
                )
                .casefold()
            )

            normalized_invite_org = (
                " ".join(
                    str(
                        invite_organization_name
                    )
                    .strip()
                    .split()
                )
                .casefold()
            )

            if (
                normalized_entered_org
                != normalized_invite_org
            ):
                raise ValueError(
                    "Organization name does not match "
                    "the administrator-issued "
                    "registration code."
                )

            # Save the canonical organization name from the
            # administrator-issued invitation.
            organization_name = (
                str(
                    invite_organization_name
                )
                .strip()
            )

            authority_ward_ids = (
                _validate_authority_wards(
                    cursor,
                    payload.get(
                        "wardRegionIds"
                    ),
                )
            )

            # First selected ward is stored
            # as the primary region for
            # compatibility with existing code.
            region_id = (
                authority_ward_ids[0]
            )


        # ----------------------------------------------------
        # ACCOUNT STATUS
        # ----------------------------------------------------

        # An authority that reaches this point has already
        # passed the administrator-issued registration-code
        # and organization-name checks, so it is active
        # immediately. Other existing roles also remain active.
        account_status = "active"


        # ----------------------------------------------------
        # INSERT USER
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO users (
                role,
                full_name,
                email,
                password_hash,
                phone,
                address_text,
                region_id,
                locality_region_id,
                account_status,
                email_verified
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                0
            )
            """,
            (
                role,
                full_name,
                email,
                password_hash,
                phone,
                address_text,
                region_id,
                locality_region_id,
                account_status,
            ),
        )

        user_id = int(
            cursor.lastrowid
        )


        # ----------------------------------------------------
        # EMPLOYEE PROFILE
        # ----------------------------------------------------

        if role == "employee":

            employee_code = (
                invite.get(
                    "employee_code"
                )
            )

            if not employee_code:
                raise ValueError(
                    "This employee invitation "
                    "has no employee code."
                )

            cursor.execute(
                """
                INSERT INTO employees (
                    user_id,
                    authority_id,
                    employee_code,
                    job_title,
                    employment_status,
                    joined_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'active',
                    CURDATE()
                )
                """,
                (
                    user_id,
                    invite[
                        "authority_id"
                    ],
                    employee_code,
                    invite.get(
                        "job_title"
                    ),
                ),
            )


        # ----------------------------------------------------
        # AUTHORITY PROFILE
        # ----------------------------------------------------

        elif role == "community_authority":

            primary_ward_id = (
                authority_ward_ids[0]
            )

            cursor.execute(
                """
                INSERT INTO community_authorities (
                    user_id,
                    assigned_region_id,
                    organization_name,
                    approval_status
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    'approved'
                )
                """,
                (
                    user_id,
                    primary_ward_id,
                    organization_name,
                ),
            )

            authority_id = int(
                cursor.lastrowid
            )


            # ------------------------------------------------
            # SAVE EVERY COVERED WARD
            # ------------------------------------------------

            for index, ward_id in enumerate(
                authority_ward_ids
            ):

                cursor.execute(
                    """
                    INSERT INTO authority_regions (
                        authority_id,
                        region_id,
                        is_primary
                    )
                    VALUES (
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        authority_id,
                        ward_id,
                        1
                        if index == 0
                        else 0,
                    ),
                )


        # ----------------------------------------------------
        # MARK INVITATION AS USED
        # ----------------------------------------------------

        if invite is not None:

            cursor.execute(
                """
                UPDATE registration_invites

                SET
                    used_by_user_id = %s,
                    used_at = NOW(),
                    is_active = 0

                WHERE invite_id = %s
                """,
                (
                    user_id,
                    invite[
                        "invite_id"
                    ],
                ),
            )


        connection.commit()


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        result = {
            "user_id":
                user_id,

            "role":
                role,

            "account_status":
                account_status,

            "email":
                email,
        }


        if household_area:

            result[
                "area"
            ] = {
                "area_region_id":
                    locality_region_id,

                "area_name":
                    household_area[
                        "area_name"
                    ],

                "ward_region_id":
                    region_id,

                "ward_name":
                    household_area[
                        "ward_name"
                    ],
            }


        if role == "community_authority":

            result[
                "coverage_ward_ids"
            ] = authority_ward_ids


        if role == "community_authority":

            result["message"] = (
                "Community Authority registration "
                "was approved successfully. "
                "You can now log in using your "
                "EcoLens account."
            )

        else:

            result["message"] = (
                "Your EcoLens account was "
                "created successfully."
            )


        return result


    except IntegrityError as exc:

        connection.rollback()

        if exc.errno == 1062:
            raise ValueError(
                "This email, employee code, "
                "or registration information "
                "already exists."
            ) from exc

        raise RuntimeError(
            "The account could not be "
            "saved to the database."
        ) from exc


    except ValueError:

        connection.rollback()
        raise


    except Exception as exc:

        connection.rollback()

        raise RuntimeError(
            "The signup process could not "
            "be completed."
        ) from exc


    finally:

        cursor.close()
        connection.close()