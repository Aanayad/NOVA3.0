"""
Nova 3.0 - AI Brain (Groq)
==========================
Groq is a free, extremely fast LLM inference API (their custom LPU hardware
typically responds far faster than most hosted APIs) and is fully
OpenAI-SDK compatible, so we talk to it via the standard `openai` package
pointed at Groq's base URL.

Get free keys at https://console.groq.com/keys (no credit card required).

Features:
  * Automatic load balancing across two API keys
  * Quota/rate-limit failover (Key 1 -> Key 2 -> back to Key 1)
  * Retry logic with exponential backoff
  * In-memory conversation context ONLY - nothing is written to disk.
    Restarting the server or refreshing the page clears it, by design.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List

from openai import OpenAI

from config.config import Config

logger = logging.getLogger("nova.ai")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

NOVA_SYSTEM_PROMPT = """You are Nova, a premium voice assistant (like a modern Alexa).
Personality: friendly, professional, concise, occasionally funny when appropriate.
Keep spoken replies short (1-3 sentences) unless the user asks for detail, since
your responses are read aloud by text-to-speech. Never use markdown syntax in
replies that will be spoken. If asked to perform a device/browser action, briefly
confirm it in natural language (the actual action is executed separately)."""


@dataclass
class _KeyState:
    api_key: str
    label: str
    quota_exhausted_until: float = 0.0
    failure_count: int = 0

    def is_available(self) -> bool:
        return bool(self.api_key) and time.time() >= self.quota_exhausted_until

    def mark_exhausted(self, cooldown_seconds: int = 60) -> None:
        self.quota_exhausted_until = time.time() + cooldown_seconds
        self.failure_count += 1
        logger.warning("%s marked exhausted for %ss", self.label, cooldown_seconds)


class _QuotaExceeded(Exception):
    pass


class GroqBrain:
    """Dual-key load-balanced Groq client. Memory lives in RAM only."""

    MAX_RETRIES_PER_KEY = 2
    MAX_HISTORY_TURNS = 12

    def __init__(self) -> None:
        self._keys: List[_KeyState] = [
            _KeyState(api_key=Config.GROQ_API_KEY_1, label="GROQ_KEY_1"),
            _KeyState(api_key=Config.GROQ_API_KEY_2, label="GROQ_KEY_2"),
        ]
        self._active_index = 0
        self._sessions: Dict[str, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=self.MAX_HISTORY_TURNS)
        )
        self._offline = not any(k.api_key for k in self._keys)
        if self._offline:
            logger.warning("No Groq keys configured - running in offline echo mode.")

    def ask(self, session_id: str, user_message: str) -> str:
        history = self._sessions[session_id]

        if self._offline:
            reply = self._offline_reply()
        else:
            reply = self._ask_with_failover(history, user_message)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        return reply

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _ask_with_failover(self, history: Deque[dict], user_message: str) -> str:
        order = [self._active_index, 1 - self._active_index]

        for key_index in order:
            key_state = self._keys[key_index]
            if not key_state.is_available():
                continue

            for attempt in range(1, self.MAX_RETRIES_PER_KEY + 1):
                try:
                    reply = self._call_groq(key_state, history, user_message)
                    self._active_index = key_index
                    return reply
                except _QuotaExceeded:
                    key_state.mark_exhausted(cooldown_seconds=60)
                    break
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "%s attempt %s/%s failed: %s",
                        key_state.label, attempt, self.MAX_RETRIES_PER_KEY, exc,
                    )
                    time.sleep(min(2 ** attempt, 5))

        logger.error("Both Groq keys unavailable - falling back to offline mode.")
        return self._offline_reply()

    def _call_groq(self, key_state: _KeyState, history: Deque[dict], user_message: str) -> str:
        client = OpenAI(api_key=key_state.api_key, base_url=GROQ_BASE_URL)

        messages = [{"role": "system", "content": NOVA_SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = client.chat.completions.create(
                model=Config.GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=400,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "429" in message or "rate" in message or "quota" in message:
                raise _QuotaExceeded(str(exc)) from exc
            raise

        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise RuntimeError("Empty response from Groq")
        return text.strip()

    @staticmethod
    def _offline_reply() -> str:
        return (
            "I'm running without a connected AI brain right now. Add a free "
            "Groq API key (console.groq.com) in your .env file to unlock "
            "full conversation."
        )

    @property
    def status(self) -> dict:
        return {
            "offline": self._offline,
            "active_key": self._keys[self._active_index].label if not self._offline else None,
            "keys": [
                {
                    "label": k.label,
                    "configured": bool(k.api_key),
                    "available": k.is_available(),
                    "failures": k.failure_count,
                }
                for k in self._keys
            ],
        }
