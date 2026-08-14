import os
from typing import Any

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import check_password_hash


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
    )


# ============================================================
# ROLE HELPERS
# ============================================================

ROLE_MAP = {
    "household": "household",
    "employee": "employee",
    "authority": "community_authority",
    "community_authority": "community_authority",
}


ROLE_DISPLAY = {
    "household": "Household",
    "employee": "Municipal Employee",
    "community_authority": "Community Authority",
}


ROLE_REDIRECT = {
    "household": "/household",
    "employee": "/employee",
    "community_authority": "/authority",
}


def _normalize_role(
    value: Any,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Please select an account type."
        )

    role = (
        value
        .strip()
        .lower()
    )

    if role not in ROLE_MAP:
        raise ValueError(
            "Please select a valid account type."
        )

    return ROLE_MAP[role]


# ============================================================
# EMAIL
# ============================================================

def _normalize_email(
    value: Any,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Email is required."
        )

    email = (
        value
        .strip()
        .lower()
    )

    if not email:
        raise ValueError(
            "Email is required."
        )

    if len(email) > 190:
        raise ValueError(
            "Email is too long."
        )

    if (
        "@" not in email
        or "." not in email.split("@")[-1]
    ):
        raise ValueError(
            "Please enter a valid email address."
        )

    return email


# ============================================================
# PASSWORD
# ============================================================

def _validate_password_input(
    value: Any,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            "Password is required."
        )

    if not value:
        raise ValueError(
            "Password is required."
        )

    if len(value) > 128:
        raise ValueError(
            "Password is too long."
        )

    return value


def _password_matches(
    password_hash: str,
    password: str,
) -> bool:

    try:

        return check_password_hash(
            password_hash,
            password,
        )

    except Exception:

        # Old seed/demo rows may contain
        # placeholder hashes.
        return False


# ============================================================
# DATABASE USER QUERY
# ============================================================

def _find_user_by_email(
    cursor,
    email: str,
):

    cursor.execute(
        """
        SELECT
            u.user_id,
            u.role,
            u.full_name,
            u.email,
            u.password_hash,
            u.phone,
            u.region_id,
            u.account_status,
            u.email_verified,

            e.employee_id,
            e.authority_id
                AS employee_authority_id,
            e.employee_code,
            e.job_title,
            e.employment_status,

            ca.authority_id
                AS community_authority_id,
            ca.organization_name,
            ca.approval_status,

            r.region_name

        FROM users AS u

        LEFT JOIN employees AS e
            ON e.user_id =
               u.user_id

        LEFT JOIN community_authorities
            AS ca
            ON ca.user_id =
               u.user_id

        LEFT JOIN regions AS r
            ON r.region_id =
               u.region_id

        WHERE LOWER(u.email) =
              LOWER(%s)

        LIMIT 1
        """,
        (
            email,
        ),
    )

    return cursor.fetchone()


# ============================================================
# ACCESS CHECKS
# ============================================================

def _validate_account_access(
    user: dict[str, Any],
):

    role = user["role"]

    account_status = (
        user["account_status"]
    )


    # --------------------------------------------------------
    # USER ACCOUNT STATUS
    # --------------------------------------------------------

    if account_status == "pending":

        raise PermissionError(
            "Your account is awaiting approval."
        )


    if account_status == "suspended":

        raise PermissionError(
            "Your EcoLens account is suspended."
        )


    if account_status == "rejected":

        raise PermissionError(
            "Your EcoLens registration was rejected."
        )


    if account_status != "active":

        raise PermissionError(
            "Your account is not active."
        )


    # --------------------------------------------------------
    # EMPLOYEE STATUS
    # --------------------------------------------------------

    if role == "employee":

        if not user.get(
            "employee_id"
        ):

            raise PermissionError(
                "Employee profile was not found."
            )


        employment_status = (
            user.get(
                "employment_status"
            )
        )


        if employment_status == "inactive":

            raise PermissionError(
                "This employee account is inactive."
            )


        if employment_status == "on_leave":

            raise PermissionError(
                "This employee account is currently marked as on leave."
            )


        if employment_status != "active":

            raise PermissionError(
                "This employee account cannot currently log in."
            )


    # --------------------------------------------------------
    # AUTHORITY STATUS
    # --------------------------------------------------------

    if role == "community_authority":

        if not user.get(
            "community_authority_id"
        ):

            raise PermissionError(
                "Community Authority profile was not found."
            )


        approval_status = (
            user.get(
                "approval_status"
            )
        )


        if approval_status == "pending":

            raise PermissionError(
                "Your Community Authority registration is awaiting approval."
            )


        if approval_status == "rejected":

            raise PermissionError(
                "Your Community Authority registration was rejected."
            )


        if approval_status != "approved":

            raise PermissionError(
                "Your Community Authority account is not approved."
            )


# ============================================================
# SAFE USER RESPONSE
# ============================================================

def _build_safe_user(
    user: dict[str, Any],
) -> dict[str, Any]:

    role = user["role"]


    result = {

        "user_id":
            int(
                user["user_id"]
            ),

        "role":
            role,

        "role_display":
            ROLE_DISPLAY.get(
                role,
                role,
            ),

        "full_name":
            user["full_name"],

        "email":
            user["email"],

        "phone":
            user.get(
                "phone"
            ),

        "region_id":
            user.get(
                "region_id"
            ),

        "region_name":
            user.get(
                "region_name"
            ),

        "account_status":
            user[
                "account_status"
            ],

        "redirect_path":
            ROLE_REDIRECT[
                role
            ],
    }


    if role == "employee":

        result[
            "employee"
        ] = {

            "employee_id":
                user.get(
                    "employee_id"
                ),

            "authority_id":
                user.get(
                    "employee_authority_id"
                ),

            "employee_code":
                user.get(
                    "employee_code"
                ),

            "job_title":
                user.get(
                    "job_title"
                ),

            "employment_status":
                user.get(
                    "employment_status"
                ),
        }


    if role == "community_authority":

        result[
            "authority"
        ] = {

            "authority_id":
                user.get(
                    "community_authority_id"
                ),

            "organization_name":
                user.get(
                    "organization_name"
                ),

            "approval_status":
                user.get(
                    "approval_status"
                ),
        }


    return result


# ============================================================
# LOGIN
# ============================================================

def authenticate_user(
    email: Any,
    password: Any,
    requested_role: Any,
) -> dict[str, Any]:

    email = _normalize_email(
        email
    )

    password = (
        _validate_password_input(
            password
        )
    )

    requested_role = (
        _normalize_role(
            requested_role
        )
    )


    connection = (
        _get_connection()
    )

    cursor = connection.cursor(
        dictionary=True
    )


    try:

        user = _find_user_by_email(
            cursor,
            email,
        )


        # ----------------------------------------------------
        # DO NOT REVEAL WHETHER EMAIL EXISTS
        # ----------------------------------------------------

        if user is None:

            raise ValueError(
                "Email or password is incorrect."
            )


        # ----------------------------------------------------
        # PASSWORD
        # ----------------------------------------------------

        if not _password_matches(
            user["password_hash"],
            password,
        ):

            raise ValueError(
                "Email or password is incorrect."
            )


        # ----------------------------------------------------
        # SELECTED ROLE MUST MATCH DATABASE ROLE
        # ----------------------------------------------------

        if (
            user["role"]
            != requested_role
        ):

            raise ValueError(
                "The selected account type does not match this account."
            )


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        _validate_account_access(
            user
        )


        return _build_safe_user(
            user
        )


    finally:

        cursor.close()

        connection.close()


# ============================================================
# CURRENT LOGGED-IN USER
# ============================================================

def get_login_user_by_id(
    user_id: int,
) -> dict[str, Any] | None:

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
                u.user_id,
                u.role,
                u.full_name,
                u.email,
                u.phone,
                u.region_id,
                u.account_status,
                u.email_verified,

                e.employee_id,
                e.authority_id
                    AS employee_authority_id,
                e.employee_code,
                e.job_title,
                e.employment_status,

                ca.authority_id
                    AS community_authority_id,
                ca.organization_name,
                ca.approval_status,

                r.region_name

            FROM users AS u

            LEFT JOIN employees AS e
                ON e.user_id =
                   u.user_id

            LEFT JOIN community_authorities
                AS ca
                ON ca.user_id =
                   u.user_id

            LEFT JOIN regions AS r
                ON r.region_id =
                   u.region_id

            WHERE u.user_id = %s

            LIMIT 1
            """,
            (
                user_id,
            ),
        )


        user = cursor.fetchone()


        if user is None:

            return None


        _validate_account_access(
            user
        )


        return _build_safe_user(
            user
        )


    finally:

        cursor.close()

        connection.close()