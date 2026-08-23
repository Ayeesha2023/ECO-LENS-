import json
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    jsonify,
    request,
    send_from_directory,
    session,
)

from werkzeug.utils import (
    secure_filename,
)

from repositories.employee_dashboard_repository import (
    build_employee_dashboard,
    complete_assignment,
    get_assignment_detail,
    get_employee_for_user,
    transition_assignment,
)

from services.employee_detection_service import (
    run_employee_detection,
)


employee_dashboard_bp = Blueprint(
    "employee_dashboard",
    __name__,
    url_prefix="/api/employee/dashboard",
)


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

UPLOAD_ROOT = (
    BACKEND_DIR /
    "uploads"
)

DETECTION_UPLOAD_DIR = (
    UPLOAD_ROOT /
    "detections" /
    "employee"
)

AFTER_UPLOAD_DIR = (
    UPLOAD_ROOT /
    "report_images"
)

DETECTION_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AFTER_UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def _require_employee():
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

    if role != "employee":
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "Municipal Employee access required.",
                }
            ),
            403,
        )

    employee = get_employee_for_user(
        int(user_id)
    )

    if employee is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "Employee profile was not found.",
                }
            ),
            403,
        )

    if (
        employee[
            "account_status"
        ] != "active"
        or
        employee[
            "employment_status"
        ] != "active"
    ):
        return None, (
            jsonify(
                {
                    "success": False,
                    "error":
                        "This employee account is not active.",
                }
            ),
            403,
        )

    return employee, None


def _validate_image(
    file_storage,
):
    if file_storage is None:
        raise ValueError(
            "An image is required."
        )

    original_name = (
        secure_filename(
            file_storage.filename
            or ""
        )
    )

    if not original_name:
        raise ValueError(
            "Please choose an image."
        )

    suffix = Path(
        original_name
    ).suffix.lower()

    if (
        suffix
        not in
        ALLOWED_IMAGE_EXTENSIONS
    ):
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP "
            "images are allowed."
        )

    return (
        original_name,
        suffix,
    )


def _save_image(
    file_storage,
    directory: Path,
    prefix: str,
):
    (
        original_name,
        suffix,
    ) = _validate_image(
        file_storage
    )

    filename = (
        f"{prefix}_"
        f"{uuid.uuid4().hex}"
        f"{suffix}"
    )

    path = (
        directory /
        filename
    )

    file_storage.save(
        str(path)
    )

    relative_path = (
        path
        .relative_to(
            BACKEND_DIR
        )
        .as_posix()
    )

    return (
        original_name,
        path,
        relative_path,
    )


# ============================================================
# BOOTSTRAP
# ============================================================

@employee_dashboard_bp.get(
    "/bootstrap"
)
def bootstrap():
    employee, error = (
        _require_employee()
    )

    if error:
        return error

    try:
        data = (
            build_employee_dashboard(
                int(
                    employee[
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
            "Employee dashboard error:",
            exc,
        )

        return jsonify(
            {
                "success": False,
                "error":
                    "Employee dashboard could not be loaded.",
            }
        ), 500


# ============================================================
# ASSIGNMENT DETAIL
# ============================================================

@employee_dashboard_bp.get(
    "/assignments/<int:assignment_id>"
)
def assignment_detail(
    assignment_id,
):
    employee, error = (
        _require_employee()
    )

    if error:
        return error

    assignment = (
        get_assignment_detail(
            employee_id=int(
                employee[
                    "employee_id"
                ]
            ),
            assignment_id=assignment_id,
        )
    )

    if assignment is None:
        return jsonify(
            {
                "success": False,
                "error":
                    "Assignment was not found.",
            }
        ), 404

    return jsonify(
        {
            "success": True,
            "assignment":
                assignment,
        }
    ), 200


# ============================================================
# ACCEPT / START
# ============================================================

@employee_dashboard_bp.post(
    "/assignments/<int:assignment_id>/<string:action>"
)
def assignment_action(
    assignment_id,
    action,
):
    employee, error = (
        _require_employee()
    )

    if error:
        return error

    if action not in {
        "accept",
        "start",
    }:
        return jsonify(
            {
                "success": False,
                "error":
                    "Invalid assignment action.",
            }
        ), 400

    try:
        result = (
            transition_assignment(
                employee_id=int(
                    employee[
                        "employee_id"
                    ]
                ),
                assignment_id=
                    assignment_id,
                action=action,
            )
        )

        return jsonify(
            {
                "success": True,

                "message":
                    "Assignment updated successfully.",

                "assignment":
                    result,
            }
        ), 200

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400

    except Exception as exc:
        print(
            "Employee assignment action error:",
            exc,
        )

        return jsonify(
            {
                "success": False,
                "error":
                    "Assignment could not be updated.",
            }
        ), 500


# ============================================================
# OPTIONAL YOLO SCAN AT THE CLEANUP SITE
# ============================================================

@employee_dashboard_bp.post(
    "/assignments/<int:assignment_id>/scan"
)
def scan_waste(
    assignment_id,
):
    employee, error = (
        _require_employee()
    )

    if error:
        return error

    assignment = (
        get_assignment_detail(
            employee_id=int(
                employee[
                    "employee_id"
                ]
            ),
            assignment_id=
                assignment_id,
        )
    )

    if assignment is None:
        return jsonify(
            {
                "success": False,
                "error":
                    "Assignment was not found.",
            }
        ), 404

    if (
        assignment[
            "assignment_status"
        ]
        not in {
            "accepted",
            "in_progress",
        }
    ):
        return jsonify(
            {
                "success": False,
                "error":
                    "Accept the assignment before scanning waste.",
            }
        ), 400

    try:
        image = request.files.get(
            "image"
        )

        (
            original_name,
            stored_path,
            _,
        ) = _save_image(
            image,
            DETECTION_UPLOAD_DIR,
            f"assignment_{assignment_id}",
        )

        result = (
            run_employee_detection(
                user_id=int(
                    employee[
                        "user_id"
                    ]
                ),

                report_id=int(
                    assignment[
                        "report_id"
                    ]
                ),

                original_filename=
                    original_name,

                stored_image_path=
                    stored_path,
            )
        )

        return jsonify(
            {
                "success": True,

                "message":
                    "Waste scan completed.",

                "detection":
                    result,
            }
        ), 201

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400

    except FileNotFoundError as exc:
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500

    except Exception as exc:
        print(
            "Employee detection error:",
            exc,
        )

        return jsonify(
            {
                "success": False,
                "error":
                    "Waste detection could not be completed.",
            }
        ), 500


# ============================================================
# COMPLETE CLEANUP
# ============================================================

@employee_dashboard_bp.post(
    "/assignments/<int:assignment_id>/complete"
)
def complete_cleanup(
    assignment_id,
):
    employee, error = (
        _require_employee()
    )

    if error:
        return error

    try:
        raw_breakdown = (
            request.form.get(
                "waste_breakdown"
            )
            or "[]"
        )

        waste_breakdown = (
            json.loads(
                raw_breakdown
            )
        )

        cleanup_notes = (
            request.form.get(
                "cleanup_notes"
            )
            or ""
        ).strip() or None

        after_image = (
            request.files.get(
                "after_image"
            )
        )

        (
            _,
            _,
            after_relative_path,
        ) = _save_image(
            after_image,
            AFTER_UPLOAD_DIR,
            f"cleanup_{assignment_id}",
        )

        result = (
            complete_assignment(
                employee_id=int(
                    employee[
                        "employee_id"
                    ]
                ),

                user_id=int(
                    employee[
                        "user_id"
                    ]
                ),

                assignment_id=
                    assignment_id,

                waste_breakdown=
                    waste_breakdown,

                cleanup_notes=
                    cleanup_notes,

                after_image_path=
                    after_relative_path,
            )
        )

        return jsonify(
            {
                "success": True,

                "message":
                    "Cleanup completed and sent "
                    "to the authority for verification.",

                "cleanup":
                    result,
            }
        ), 201

    except json.JSONDecodeError:
        return jsonify(
            {
                "success": False,
                "error":
                    "Waste breakdown format is invalid.",
            }
        ), 400

    except ValueError as exc:
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400

    except Exception as exc:
        print(
            "Cleanup completion error:",
            exc,
        )

        return jsonify(
            {
                "success": False,
                "error":
                    "Cleanup could not be submitted.",
            }
        ), 500


# ============================================================
# UPLOADED MEDIA
# ============================================================

@employee_dashboard_bp.get(
    "/media/<path:filename>"
)
def media(
    filename,
):
    return send_from_directory(
        str(UPLOAD_ROOT),
        filename,
    )