from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from routes.authority_routes import authority_bp
from routes.household_routes import household_bp


def create_app() -> Flask:
    """
    Create and configure the ECO-LENS Flask application.
    """

    app = Flask(__name__)

    # Load settings from config.py and .env.
    app.config.from_object(Config)

    # Allow the React frontend to call Flask APIs.
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

    # Register Community Authority routes.
    app.register_blueprint(
        authority_bp
    )

    # Register Household routes.
    app.register_blueprint(
        household_bp
    )

    # ========================================================
    # ROOT ROUTE
    # ========================================================

    @app.get("/")
    def home():
        return jsonify(
            {
                "success": True,
                "application": "ECO-LENS",
                "message": (
                    "ECO-LENS backend is running."
                ),
                "available_modules": [
                    "community_authority",
                    "household",
                ],
            }
        ), 200

    # ========================================================
    # HEALTH CHECK
    # ========================================================

    @app.get("/api/health")
    def health_check():
        return jsonify(
            {
                "success": True,
                "status": "healthy",
                "message": (
                    "ECO-LENS API is running."
                ),
                "modules": {
                    "community_authority": "available",
                    "household": "available",
                },
            }
        ), 200

    # ========================================================
    # ERROR HANDLERS
    # ========================================================

    @app.errorhandler(404)
    def route_not_found(error):
        return jsonify(
            {
                "success": False,
                "error": (
                    "The requested API route "
                    "was not found."
                ),
            }
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify(
            {
                "success": False,
                "error": (
                    "This HTTP method is not allowed "
                    "for the requested route."
                ),
            }
        ), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify(
            {
                "success": False,
                "error": (
                    "An internal server error occurred."
                ),
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