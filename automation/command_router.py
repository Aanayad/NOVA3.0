"""
Nova 3.0 - Command router.

Takes raw recognized speech (already stripped of the "Nova" wake word by the
frontend) and decides whether it's:
  1. A browser/website action        -> automation.browser_automation
  2. A YouTube action                -> automation.browser_automation
  3. A local system action           -> automation.system_control (local only)
  4. A file action                   -> automation.file_manager (local only)
  5. General conversation            -> falls through to the AI brain

Returns a structured dict the frontend can act on directly, e.g.:
    {"type": "browser", "action": "open_url", "url": "...", "spoken_reply": "Opening YouTube."}
    {"type": "system", "spoken_reply": "Shutting down in 5 seconds."}
    {"type": "chat"}   # meaning: no automation matched, send to the AI brain
"""

from __future__ import annotations

import re
from typing import Optional

from automation import browser_automation, system_control, file_manager

# Ordered list of (regex, handler_name) - first match wins.
_PATTERNS = [
    (r"^open\s+(youtube|instagram|linkedin|github|chatgpt|gmail|netflix|spotify|canva|"
     r"leetcode|geeksforgeeks|gfg|stackoverflow|reddit|amazon|flipkart|blinkit|whatsapp( web)?|"
     r"twitter|x|facebook|gemini|maps|google maps|drive|google drive|calendar|translate|"
     r"wikipedia|twitch|discord|telegram)\b", "open_site"),
    (r"^open\s+this\s+website", "open_site"),
    (r"^search\s+.+\s+on\s+youtube$", "youtube"),
    (r"^play\s+", "youtube"),
    (r"^play\s+this\s+video\s+on\s+youtube", "youtube"),
    (r"^(pause|resume|next video|previous video|mute video|fullscreen|exit fullscreen|"
     r"increase volume|decrease volume)$", "player_control"),
    (r"^search\s+this\s+on\s+google$", "google_this"),
    (r"^search\s+", "google"),
    (r"^open\s+", "open_site"),  # fallback for any other "open X"
    (r"^(shutdown|shut down)( (the|my) (pc|computer))?$", "shutdown"),
    (r"^restart( (the|my) (pc|computer))?$", "restart"),
    (r"^(sleep|go to sleep)$", "sleep"),
    (r"^lock( (the|my) (pc|computer))?$", "lock"),
    (r"^mute$", "mute"),
    (r"^(increase|decrease|set)\s+volume", "volume"),
    (r"^take\s+(a\s+)?screenshot$", "screenshot"),
    (r"^(what'?s the weather|weather)", "weather"),
    (r"^(tell me|what'?s)?\s*(today'?s\s+)?news$", "news"),
    (r"^remind me", "reminder"),
    (r"^tell me a joke$", "joke"),
]


def route(command_text: str) -> dict:
    text = command_text.strip().lower()
    # Strip a leading wake word if it slipped through
    text = re.sub(r"^nova[,]?\s*", "", text)

    for pattern, handler in _PATTERNS:
        if re.match(pattern, text):
            return _dispatch(handler, text)

    return {"type": "chat"}  # no automation matched -> let the AI brain answer


def _dispatch(handler: str, text: str) -> dict:
    if handler == "open_site":
        result = browser_automation.resolve_open_site(text)
        return {"type": "browser", **result, "spoken_reply": f"Opening {result['label']}."}

    if handler == "youtube":
        result = browser_automation.resolve_youtube_command(text)
        return {"type": "browser", **result, "spoken_reply": f"Playing {result['label']} on YouTube."}

    if handler == "player_control":
        return {"type": "player_control", "action": text, "spoken_reply": ""}

    if handler in ("google", "google_this"):
        query = re.sub(r"^search\s+", "", text)
        query = re.sub(r"\s+on\s+google$", "", query)
        query = re.sub(r"^this\s+on\s+google$", "", query)
        result = browser_automation.resolve_google_search(query)
        return {"type": "browser", **result, "spoken_reply": f'Searching Google for "{query}".'}

    if handler in ("shutdown", "restart", "sleep", "lock", "mute"):
        return {
            "type": "system",
            "action": handler,
            "spoken_reply": f"Confirmed. Executing {handler}.",
        }

    if handler == "volume":
        direction = "up" if "increase" in text else "down"
        return {"type": "system", "action": "volume", "direction": direction,
                 "spoken_reply": f"Turning volume {direction}."}

    if handler == "screenshot":
        return {"type": "client_action", "action": "screenshot",
                 "spoken_reply": "Taking a screenshot."}

    if handler == "weather":
        return {"type": "info_lookup", "action": "weather",
                 "spoken_reply": "Let me check the weather for you."}

    if handler == "news":
        return {"type": "info_lookup", "action": "news",
                 "spoken_reply": "Here's today's top news."}

    if handler == "reminder":
        return {"type": "reminder", "spoken_reply": "Got it, I'll remind you."}

    if handler == "joke":
        return {"type": "chat", "force_prompt": "Tell me a short, friendly joke."}

    return {"type": "chat"}
