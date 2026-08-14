import os

from datetime import timedelta

from dotenv import load_dotenv

from flask import (
    Flask,
    jsonify,
)

from flask_cors import CORS


from config import Config

from routes.auth_routes import auth_bp
from routes.authority_routes import authority_bp
from routes.employee_routes import employee_bp
from routes.household_routes import household_bp


load_dotenv()


def create_app() -> Flask:

    app = Flask(
        __name__
    )


    app.config.from_object(
        Config
    )


    # ========================================================
    # SESSION SECURITY
    # ========================================================

    flask_secret_key = (
        os.getenv(
            "FLASK_SECRET_KEY"
        )
    )


    if not flask_secret_key:

        raise RuntimeError(
            "FLASK_SECRET_KEY is missing "
            "from backend/.env"
        )


    app.config.update(

        SECRET_KEY=
            flask_secret_key,

        SESSION_COOKIE_NAME=
            "ecolens_session",

        SESSION_COOKIE_HTTPONLY=
            True,

        SESSION_COOKIE_SAMESITE=
            "Lax",

        # False because local development
        # is using HTTP rather than HTTPS.
        SESSION_COOKIE_SECURE=
            False,

        PERMANENT_SESSION_LIFETIME=
            timedelta(
                hours=8
            ),
    )


    # ========================================================
    # CORS
    # ========================================================

    CORS(
        app,

        resources={
            r"/api/*": {

                "origins": [

                    "http://localhost:5173",

                    "http://127.0.0.1:5173",
                ]
            }
        },

        supports_credentials=True,
    )


    # ========================================================
    # BLUEPRINTS
    # ========================================================

    app.register_blueprint(
        auth_bp
    )


    app.register_blueprint(
        authority_bp
    )


    app.register_blueprint(
        household_bp
    )


    app.register_blueprint(
        employee_bp
    )


    # ========================================================
    # HOME
    # ========================================================

    @app.get("/")
    def home():

        return jsonify(
            {
                "success": True,

                "application":
                    "ECO-LENS",

                "message":
                    "ECO-LENS backend is running.",

                "available_modules": [
                    "authentication",
                    "community_authority",
                    "household",
                    "employee",
                ],
            }
        ), 200


    # ========================================================
    # HEALTH
    # ========================================================

    @app.get(
        "/api/health"
    )
    def health_check():

        return jsonify(
            {
                "success": True,

                "status":
                    "healthy",

                "modules": {

                    "authentication":
                        "available",

                    "community_authority":
                        "available",

                    "household":
                        "available",

                    "employee":
                        "available",
                },
            }
        ), 200


    # ========================================================
    # ERRORS
    # ========================================================

    @app.errorhandler(
        404
    )
    def route_not_found(
        error
    ):

        return jsonify(
            {
                "success": False,

                "error":
                    "The requested API route was not found.",
            }
        ), 404


    @app.errorhandler(
        405
    )
    def method_not_allowed(
        error
    ):

        return jsonify(
            {
                "success": False,

                "error":
                    "This HTTP method is not allowed for this route.",
            }
        ), 405


    @app.errorhandler(
        500
    )
    def internal_server_error(
        error
    ):

        return jsonify(
            {
                "success": False,

                "error":
                    "An internal server error occurred.",
            }
        ), 500


    return app


app = create_app()


if __name__ == "__main__":

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )