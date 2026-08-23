from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)

from repositories.authority_dashboard_repository import (
    assign_employee_to_report,
    build_authority_dashboard,
    get_authority_assignments,
    get_authority_employees,
    get_authority_for_user,
    get_authority_report,
    get_authority_reports,
    get_authority_coverage,
)


authority_dashboard_bp = Blueprint(
    "authority_dashboard",
    __name__,
    url_prefix="/api/authority/dashboard",
)


# ============================================================
# AUTH CHECK
# ============================================================

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


    authority = (
        get_authority_for_user(
            int(user_id)
        )
    )


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

        or authority[
            "account_status"
        ] != "active"
    ):

        return None, (
            jsonify(
                {
                    "success": False,

                    "error":
                        "This Community Authority account is not active and approved.",
                }
            ),
            403,
        )


    return authority, None


# ============================================================
# BOOTSTRAP
# ============================================================

@authority_dashboard_bp.get(
    "/bootstrap"
)
def bootstrap():

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    try:

        data = (
            build_authority_dashboard(
                int(
                    authority[
                        "user_id"
                    ]
                )
            )
        )


        return jsonify(
            {
                "success": True,
                **data,
            }
        ), 200


    except Exception as exc:

        print(
            "Authority dashboard error:",
            exc,
        )

        return jsonify(
            {
                "success": False,

                "error":
                    "Authority dashboard could not be loaded.",
            }
        ), 500


# ============================================================
# REPORTS
# ============================================================

@authority_dashboard_bp.get(
    "/reports"
)
def reports():

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    try:

        status = request.args.get(
            "status"
        )


        result = (
            get_authority_reports(
                authority_id=int(
                    authority[
                        "authority_id"
                    ]
                ),
                status=status,
            )
        )


        return jsonify(
            {
                "success": True,
                "reports": result,
            }
        ), 200


    except ValueError as exc:

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400


# ============================================================
# SINGLE REPORT
# ============================================================

@authority_dashboard_bp.get(
    "/reports/<int:report_id>"
)
def report_detail(
    report_id,
):

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    report = get_authority_report(
        authority_id=int(
            authority[
                "authority_id"
            ]
        ),
        report_id=report_id,
    )


    if report is None:

        return jsonify(
            {
                "success": False,

                "error":
                    "Report was not found.",
            }
        ), 404


    return jsonify(
        {
            "success": True,
            "report": report,
        }
    ), 200


# ============================================================
# EMPLOYEES
# ============================================================

@authority_dashboard_bp.get(
    "/employees"
)
def employees():

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    result = get_authority_employees(
        int(
            authority[
                "authority_id"
            ]
        )
    )


    return jsonify(
        {
            "success": True,
            "employees": result,
        }
    ), 200


# ============================================================
# ASSIGNMENTS
# ============================================================

@authority_dashboard_bp.get(
    "/assignments"
)
def assignments():

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    result = get_authority_assignments(
        int(
            authority[
                "authority_id"
            ]
        )
    )


    return jsonify(
        {
            "success": True,
            "assignments": result,
        }
    ), 200


# ============================================================
# ASSIGN EMPLOYEE
# ============================================================

@authority_dashboard_bp.post(
    "/reports/<int:report_id>/assign"
)
def assign_report(
    report_id,
):

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    payload = request.get_json(
        silent=True
    ) or {}


    try:

        employee_id = int(
            payload.get(
                "employee_id"
            )
        )


        priority = (
            payload.get(
                "priority",
                "medium",
            )
        )


        notes = payload.get(
            "assignment_notes"
        )


        if isinstance(
            notes,
            str,
        ):

            notes = (
                notes.strip()
                or None
            )


        result = (
            assign_employee_to_report(
                authority_id=int(
                    authority[
                        "authority_id"
                    ]
                ),
                report_id=report_id,
                employee_id=employee_id,
                priority=priority,
                assignment_notes=notes,
            )
        )


        return jsonify(
            {
                "success": True,

                "message":
                    "Employee assigned successfully.",

                "assignment":
                    result,
            }
        ), 201


    except (
        TypeError,
        ValueError,
    ) as exc:

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400


    except Exception as exc:

        print(
            "Assignment error:",
            exc,
        )

        return jsonify(
            {
                "success": False,

                "error":
                    "Employee could not be assigned.",
            }
        ), 500


# ============================================================
# COVERAGE
# ============================================================

@authority_dashboard_bp.get(
    "/coverage"
)
def coverage():

    authority, error = (
        _require_authority()
    )

    if error:
        return error


    result = get_authority_coverage(
        int(
            authority[
                "authority_id"
            ]
        )
    )


    return jsonify(
        {
            "success": True,
            "coverage": result,
        }
    ), 200