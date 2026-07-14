"""
Nova 3.0 - REST API routes.

No conversation history is written to disk anywhere in this file, by
design - session context lives only in GroqBrain's in-memory dict for the
lifetime of the running process (see ai/groq_brain.py).

Endpoints:
    POST /api/chat            - send a message to the AI brain, get a spoken reply
    POST /api/command         - route a recognized voice command (open site, system, etc.)
    GET  /api/system/stats    - read-only CPU/RAM/battery/disk stats
    GET  /api/brain/status    - which Groq key is active, quota state
    GET  /api/health          - liveness check
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from ai.groq_brain import GroqBrain
from automation import command_router, system_control
from utils.validators import (
    ValidationError,
    validate_chat_payload,
    validate_command_payload,
    validate_session_id,
)

logger = logging.getLogger("nova.api")
api_bp = Blueprint("api", __name__, url_prefix="/api")

brain = GroqBrain()


@api_bp.errorhandler(ValidationError)
def handle_validation_error(err: ValidationError):
    return jsonify({"error": str(err)}), 400


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Nova 3.0"})


@api_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = validate_chat_payload(data)
    session_id = validate_session_id(data)

    reply = brain.ask(session_id=session_id, user_message=message)
    return jsonify({"reply": reply, "session_id": session_id})


@api_bp.route("/command", methods=["POST"])
def command():
    data = request.get_json(silent=True) or {}
    command_text = validate_command_payload(data)
    session_id = validate_session_id(data)

    routed = command_router.route(command_text)

    if routed["type"] == "chat":
        prompt = routed.get("force_prompt", command_text)
        reply = brain.ask(session_id=session_id, user_message=prompt)
        return jsonify({"type": "chat", "reply": reply, "session_id": session_id})

    if routed["type"] == "system":
        try:
            action = routed["action"]
            if action == "volume":
                delta = 15 if routed.get("direction") == "up" else -15
                result = system_control.set_volume(50 + delta)
            else:
                result = system_control.SYSTEM_ACTIONS[action]()
            routed["result"] = result
        except system_control.SystemControlDisabled as exc:
            routed["result"] = str(exc)
            routed["spoken_reply"] = (
                "System control is turned off. Enable it in your local .env "
                "file if you're running Nova on your own machine."
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("System command failed")
            routed["result"] = f"Failed: {exc}"

    return jsonify(routed)


@api_bp.route("/system/stats", methods=["GET"])
def stats():
    return jsonify(system_control.get_system_stats())


@api_bp.route("/brain/status", methods=["GET"])
def brain_status():
    return jsonify(brain.status)
