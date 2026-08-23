from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)

from repositories.auth_repository import (
    get_signup_locations,
    register_user,
)

from repositories.login_repository import (
    authenticate_user,
    get_login_user_by_id,
)

from repositories.admin_repository import (
    authenticate_admin,
    get_admin_by_id,
)


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth",
)


# ============================================================
# SIGNUP LOCATIONS
# ============================================================

@auth_bp.get(
    "/signup-locations"
)
def signup_locations():

    try:

        locations = (
            get_signup_locations()
        )

        return jsonify(
            {
                "success": True,
                **locations,
            }
        ), 200


    except Exception:

        return jsonify(
            {
                "success": False,

                "error": (
                    "Signup locations "
                    "could not be loaded."
                ),
            }
        ), 500


# ============================================================
# OLD REGIONS ENDPOINT
# ============================================================

@auth_bp.get(
    "/regions"
)
def regions():

    try:

        locations = (
            get_signup_locations()
        )

        return jsonify(
            {
                "success": True,

                "regions":
                    locations[
                        "household_areas"
                    ],
            }
        ), 200


    except Exception:

        return jsonify(
            {
                "success": False,

                "error": (
                    "Regions could not "
                    "be loaded."
                ),
            }
        ), 500


# ============================================================
# SIGNUP
# ============================================================

@auth_bp.post(
    "/signup"
)
def signup():

    payload = request.get_json(
        silent=True
    )


    if payload is None:

        return jsonify(
            {
                "success": False,

                "error": (
                    "A JSON request "
                    "body is required."
                ),
            }
        ), 400


    try:

        result = register_user(
            payload
        )

        return jsonify(
            {
                "success": True,
                **result,
            }
        ), 201


    except ValueError as exc:

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400


    except Exception:

        return jsonify(
            {
                "success": False,

                "error": (
                    "The account could "
                    "not be created."
                ),
            }
        ), 500


# ============================================================
# LOGIN
# ============================================================

@auth_bp.post(
    "/login"
)
def login():

    payload = request.get_json(
        silent=True
    )


    if payload is None:

        return jsonify(
            {
                "success": False,

                "error": (
                    "A JSON request body "
                    "is required."
                ),
            }
        ), 400


    try:

        requested_role = (
            str(
                payload.get(
                    "role",
                    ""
                )
            )
            .strip()
            .lower()
        )


        if requested_role == "admin":

            user = authenticate_admin(
                email=payload.get(
                    "email"
                ),

                password=payload.get(
                    "password"
                ),
            )

        else:

            user = authenticate_user(
                email=payload.get(
                    "email"
                ),

                password=payload.get(
                    "password"
                ),

                requested_role=payload.get(
                    "role"
                ),
            )


        # Remove any old login session.
        session.clear()


        session.permanent = True


        session[
            "user_id"
        ] = user[
            "user_id"
        ]


        session[
            "role"
        ] = user[
            "role"
        ]


        return jsonify(
            {
                "success": True,

                "message": (
                    "Login successful."
                ),

                "user": user,

                "redirect_path":
                    user[
                        "redirect_path"
                    ],
            }
        ), 200


    except PermissionError as exc:

        return jsonify(
            {
                "success": False,

                "error": str(exc),
            }
        ), 403


    except ValueError as exc:

        return jsonify(
            {
                "success": False,

                "error": str(exc),
            }
        ), 401


    except Exception:

        return jsonify(
            {
                "success": False,

                "error": (
                    "Login could not "
                    "be completed."
                ),
            }
        ), 500


# ============================================================
# CURRENT SESSION
# ============================================================

@auth_bp.get(
    "/me"
)
def current_user():

    user_id = session.get(
        "user_id"
    )


    if user_id is None:

        return jsonify(
            {
                "success": False,

                "error": (
                    "You are not logged in."
                ),
            }
        ), 401


    try:

        session_role = session.get(
            "role"
        )


        if session_role == "admin":

            user = (
                get_admin_by_id(
                    int(user_id)
                )
            )

        else:

            user = (
                get_login_user_by_id(
                    int(user_id)
                )
            )


        if user is None:

            session.clear()

            return jsonify(
                {
                    "success": False,

                    "error": (
                        "The logged-in "
                        "account no longer exists."
                    ),
                }
            ), 401


        return jsonify(
            {
                "success": True,

                "user": user,
            }
        ), 200


    except PermissionError as exc:

        session.clear()

        return jsonify(
            {
                "success": False,

                "error": str(exc),
            }
        ), 403


    except Exception:

        return jsonify(
            {
                "success": False,

                "error": (
                    "The current account "
                    "could not be loaded."
                ),
            }
        ), 500


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.post(
    "/logout"
)
def logout():

    session.clear()


    return jsonify(
        {
            "success": True,

            "message": (
                "You have been logged out."
            ),
        }
    ), 200