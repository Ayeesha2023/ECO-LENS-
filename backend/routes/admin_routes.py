from flask import Blueprint, jsonify, request, session

from repositories.admin_repository import (
    create_authority_invite,
    get_admin_by_id,
    list_authority_invites,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)


def _require_admin():
    admin_id = session.get("user_id")
    role = session.get("role")

    if admin_id is None:
        return None, (
            jsonify({"success": False, "error": "You must log in first."}),
            401,
        )

    if role != "admin":
        return None, (
            jsonify({"success": False, "error": "Administrator access required."}),
            403,
        )

    try:
        admin = get_admin_by_id(int(admin_id))
    except PermissionError as exc:
        session.clear()
        return None, (jsonify({"success": False, "error": str(exc)}), 403)

    if admin is None:
        session.clear()
        return None, (
            jsonify({"success": False, "error": "Administrator account was not found."}),
            401,
        )

    return admin, None


@admin_bp.get("/bootstrap")
def bootstrap():
    admin, error = _require_admin()
    if error:
        return error

    try:
        return jsonify(
            {
                "success": True,
                "admin": admin,
                "authority_invites": list_authority_invites(),
            }
        ), 200
    except Exception as exc:
        print("Admin bootstrap error:", exc)
        return jsonify(
            {"success": False, "error": "Admin dashboard could not be loaded."}
        ), 500


@admin_bp.get("/authority-invites")
def authority_invites():
    _, error = _require_admin()
    if error:
        return error

    try:
        return jsonify(
            {"success": True, "invites": list_authority_invites()}
        ), 200
    except Exception as exc:
        print("Admin authority invite list error:", exc)
        return jsonify(
            {"success": False, "error": "Authority invitations could not be loaded."}
        ), 500


@admin_bp.post("/authority-invites")
def generate_authority_invite():
    _, error = _require_admin()
    if error:
        return error

    payload = request.get_json(silent=True) or {}

    try:
        invite = create_authority_invite(
            organization_name=payload.get("organization_name"),
            valid_days=payload.get("valid_days", 30),
        )
        return jsonify(
            {
                "success": True,
                "message": (
                    "Authority registration code created. Copy the code now; "
                    "only its digest is stored in the database."
                ),
                "invite": invite,
            }
        ), 201
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        print("Admin authority invite error:", exc)
        return jsonify(
            {"success": False, "error": "Authority registration code could not be created."}
        ), 500