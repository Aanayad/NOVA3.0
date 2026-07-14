"""Nova 3.0 - request input validation helpers."""

from __future__ import annotations

MAX_MESSAGE_LENGTH = 4000


class ValidationError(Exception):
    pass


def validate_chat_payload(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValidationError("Field 'message' is required and must be a non-empty string.")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message too long (max {MAX_MESSAGE_LENGTH} characters).")

    return message.strip()


def validate_session_id(data: dict) -> str:
    session_id = data.get("session_id") or "default"
    if not isinstance(session_id, str) or len(session_id) > 128:
        raise ValidationError("Invalid session_id.")
    return session_id


def validate_command_payload(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    command = data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValidationError("Field 'command' is required and must be a non-empty string.")
    return command.strip()
