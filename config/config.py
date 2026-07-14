"""
Nova 3.0 - Central configuration.

Loads all runtime configuration from environment variables (.env) so that
no secrets ever live in source code. Import `Config` anywhere in the backend.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _clean_key(value: str) -> str:
    """Strip whitespace and accidental wrapping quotes from a pasted key."""
    if not value:
        return ""
    return value.strip().strip('"').strip("'").strip()


class Config:
    # --- Flask ---
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = FLASK_ENV == "development"
    SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    PORT: int = int(os.getenv("PORT", "5000"))

    # --- Auth ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXP_MINUTES: int = 60 * 24

    # --- Groq dual-key load balancing (free, fast) ---
    GROQ_API_KEY_1: str = _clean_key(os.getenv("GROQ_API_KEY_1", ""))
    GROQ_API_KEY_2: str = _clean_key(os.getenv("GROQ_API_KEY_2", ""))
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60 per minute")

    # --- Feature flags ---
    ENABLE_SYSTEM_CONTROL: bool = _bool(os.getenv("ENABLE_SYSTEM_CONTROL"), default=False)

    @classmethod
    def validate(cls) -> list:
        """Return a list of human-readable warnings about missing/insecure config."""
        warnings = []
        if not cls.GROQ_API_KEY_1 and not cls.GROQ_API_KEY_2:
            warnings.append(
                "No Groq API keys set. Nova's brain will run in offline/echo mode. "
                "Get a free key at https://console.groq.com/keys"
            )
        if cls.SECRET_KEY == "dev-secret-change-me":
            warnings.append("FLASK_SECRET_KEY is using the insecure default value.")
        if cls.JWT_SECRET_KEY == "dev-jwt-secret-change-me":
            warnings.append("JWT_SECRET_KEY is using the insecure default value.")
        return warnings
