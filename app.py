"""
Nova 3.0 - Application entry point.

Run locally:
    python app.py

Run in production:
    gunicorn -w 2 -b 0.0.0.0:5000 app:app
"""

from __future__ import annotations

import logging

from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from api.routes import api_bp
from config.config import Config
from utils.logger import setup_logging

setup_logging("DEBUG" if Config.DEBUG else "INFO")
logger = logging.getLogger("nova.app")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["JSON_SORT_KEYS"] = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    Limiter(
        get_remote_address,
        app=app,
        default_limits=[Config.RATE_LIMIT_DEFAULT],
        storage_uri="memory://",
    )

    app.register_blueprint(api_bp)

    for warning in Config.validate():
        logger.warning("Config warning: %s", warning)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/manifest.json")
    def manifest():
        return app.send_static_file("manifest.json")

    @app.route("/sw.js")
    def service_worker():
        return app.send_static_file("sw.js")

    @app.errorhandler(404)
    def not_found(_err):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(err):
        logger.exception("Unhandled server error: %s", err)
        return {"error": "Internal server error"}, 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
