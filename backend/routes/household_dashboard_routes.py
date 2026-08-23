import uuid
from pathlib import Path

from flask import (
    Blueprint,
    jsonify,
    request,
    send_from_directory,
    session,
)
from werkzeug.utils import secure_filename

from repositories.household_dashboard_repository import (
    build_household_dashboard,
    create_public_report,
    get_household_for_user,
    get_household_location_options,
    get_household_report,
    get_household_reports,
)
from services.household_detection_service import (
    run_household_detection,
)


household_dashboard_bp = Blueprint(
    "household_dashboard",
    __name__,
    url_prefix="/api/household/dashboard",
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOAD_ROOT = BACKEND_DIR / "uploads"
DETECTION_UPLOAD_DIR = UPLOAD_ROOT / "detections" / "household"
REPORT_UPLOAD_DIR = UPLOAD_ROOT / "report_images" / "household"

DETECTION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def _require_household():
    user_id = session.get("user_id")
    role = session.get("role")

    if user_id is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "You must log in first.",
                }
            ),
            401,
        )

    if role != "household":
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Household access required.",
                }
            ),
            403,
        )

    household = get_household_for_user(int(user_id))

    if household is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Household profile was not found.",
                }
            ),
            403,
        )

    if household["account_status"] != "active":
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "This household account is not active.",
                }
            ),
            403,
        )

    return household, None


def _validate_image(file_storage):
    if file_storage is None:
        raise ValueError("An image is required.")

    original_name = secure_filename(file_storage.filename or "")

    if not original_name:
        raise ValueError("Please choose an image.")

    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    return original_name, suffix


def _save_image(file_storage, directory: Path, prefix: str):
    original_name, suffix = _validate_image(file_storage)
    filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    path = directory / filename
    file_storage.save(str(path))
    relative_path = path.relative_to(BACKEND_DIR).as_posix()
    return original_name, path, relative_path


def _parse_coordinate(value, field_name: str, minimum: float, maximum: float):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")

    if number < minimum or number > maximum:
        raise ValueError(f"{field_name} is outside the valid range.")

    return number


# ============================================================
# DASHBOARD BOOTSTRAP
# ============================================================

@household_dashboard_bp.get("/bootstrap")
def bootstrap():
    household, error = _require_household()
    if error:
        return error

    try:
        data = build_household_dashboard(int(household["user_id"]))
        return jsonify({"success": True, **data}), 200
    except Exception as exc:
        print("Household dashboard error:", exc)
        return jsonify(
            {
                "success": False,
                "error": "Household dashboard could not be loaded.",
            }
        ), 500


# ============================================================
# PERSONAL WASTE DETECTION
# Image -> YOLO only. RAG is called through the existing
# /api/household/<user_id>/advice endpoint after this succeeds.
# ============================================================

@household_dashboard_bp.post("/detect")
def detect_my_waste():
    household, error = _require_household()
    if error:
        return error

    saved_path = None

    try:
        image = request.files.get("image")
        original_name, saved_path, _ = _save_image(
            image,
            DETECTION_UPLOAD_DIR,
            f"household_{household['user_id']}",
        )

        result = run_household_detection(
            user_id=int(household["user_id"]),
            original_filename=original_name,
            stored_image_path=saved_path,
        )

        return jsonify(
            {
                "success": True,
                "message": "Waste detection completed.",
                "detection": result,
            }
        ), 201

    except ValueError as exc:
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        return jsonify({"success": False, "error": str(exc)}), 400

    except FileNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    except Exception as exc:
        print("Household detection error:", exc)
        return jsonify(
            {
                "success": False,
                "error": "Waste detection could not be completed.",
            }
        ), 500


# ============================================================
# PUBLIC WASTE REPORTING
# IMPORTANT: This does NOT run YOLO.
# ============================================================

@household_dashboard_bp.post("/reports")
def create_report():
    household, error = _require_household()
    if error:
        return error

    saved_path = None

    try:
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        address_text = (request.form.get("address_text") or "").strip() or None
        location_region_id = request.form.get("location_region_id")

        if len(title) < 4:
            raise ValueError("Please enter a short report title.")

        if len(title) > 200:
            raise ValueError("Report title is too long.")

        if len(description) < 8:
            raise ValueError("Please describe the public waste problem.")

        if location_region_id in (None, ""):
            raise ValueError("Please select the local area or ward.")

        try:
            location_region_id = int(location_region_id)
        except (TypeError, ValueError):
            raise ValueError("Selected location is invalid.")

        latitude = _parse_coordinate(
            request.form.get("latitude"),
            "Latitude",
            -90,
            90,
        )
        longitude = _parse_coordinate(
            request.form.get("longitude"),
            "Longitude",
            -180,
            180,
        )

        image = request.files.get("image")
        _, saved_path, relative_path = _save_image(
            image,
            REPORT_UPLOAD_DIR,
            f"public_report_{household['user_id']}",
        )

        result = create_public_report(
            user_id=int(household["user_id"]),
            location_region_id=location_region_id,
            title=title,
            description=description,
            address_text=address_text,
            latitude=latitude,
            longitude=longitude,
            image_path=relative_path,
        )

        if result["authority_found"]:
            message = (
                "Public waste report submitted to the responsible "
                "Community Authority."
            )
        else:
            message = (
                "Report saved successfully. No approved authority is currently "
                "mapped to this ward, so assignment will wait until coverage "
                "is configured."
            )

        return jsonify(
            {
                "success": True,
                "message": message,
                "report": result,
            }
        ), 201

    except ValueError as exc:
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        return jsonify({"success": False, "error": str(exc)}), 400

    except Exception as exc:
        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        print("Household public-report error:", exc)
        return jsonify(
            {
                "success": False,
                "error": "Public waste report could not be submitted.",
            }
        ), 500


@household_dashboard_bp.get("/reports")
def reports():
    household, error = _require_household()
    if error:
        return error

    return jsonify(
        {
            "success": True,
            "reports": get_household_reports(int(household["user_id"])),
        }
    ), 200


@household_dashboard_bp.get("/reports/<int:report_id>")
def report_detail(report_id):
    household, error = _require_household()
    if error:
        return error

    report = get_household_report(
        user_id=int(household["user_id"]),
        report_id=report_id,
    )

    if report is None:
        return jsonify(
            {
                "success": False,
                "error": "Report was not found.",
            }
        ), 404

    return jsonify({"success": True, "report": report}), 200


@household_dashboard_bp.get("/locations")
def locations():
    household, error = _require_household()
    if error:
        return error

    return jsonify(
        {
            "success": True,
            "locations": get_household_location_options(),
        }
    ), 200


# ============================================================
# UPLOADED MEDIA
# The database stores paths beginning with uploads/...
# Frontend should remove that first prefix before calling here.
# ============================================================

@household_dashboard_bp.get("/media/<path:filename>")
def media(filename):
    return send_from_directory(str(UPLOAD_ROOT), filename)