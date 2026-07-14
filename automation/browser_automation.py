"""
Nova 3.0 - Browser automation resolver.

IMPORTANT ARCHITECTURE NOTE:
A Flask server cannot open a tab inside *your* browser - it can only open one
on whatever machine the server process runs on. Since Nova is a web app, the
correct (and only real) way to "open a website" for the person talking to it
is to resolve the command into a target URL/action on the backend, then send
that instruction to the frontend, which opens it with window.open() in the
user's own browser. This module does the resolving; static/js/commands.js
does the opening/embedding.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger("nova.browser")


# Curated map of common sites so Nova doesn't have to guess via search.
SITE_MAP = {
    "youtube": "https://www.youtube.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "gmail": "https://mail.google.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "canva": "https://www.canva.com",
    "leetcode": "https://leetcode.com",
    "geeksforgeeks": "https://www.geeksforgeeks.org",
    "gfg": "https://www.geeksforgeeks.org",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "amazon": "https://www.amazon.com",
    "flipkart": "https://www.flipkart.com",
    "blinkit": "https://blinkit.com",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "gemini": "https://gemini.google.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
    "translate": "https://translate.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitch": "https://www.twitch.tv",
    "discord": "https://discord.com/app",
    "telegram": "https://web.telegram.org",
}


def resolve_open_site(command_text: str) -> dict:
    """
    Turn "open instagram" / "open this website: example.com" into a browser action.
    Returns a dict the frontend understands, e.g.:
        {"action": "open_url", "url": "https://www.instagram.com", "label": "Instagram"}
    """
    text = command_text.lower().strip()
    text = re.sub(r"^(nova[,]?\s*)?open\s+", "", text).strip()

    # Direct URL already given ("open example.com" / "open https://...")
    url_match = re.search(r"((https?://)?[\w-]+\.[a-z]{2,}(/\S*)?)", text)
    if url_match and "." in url_match.group(1):
        raw = url_match.group(1)
        url = raw if raw.startswith("http") else f"https://{raw}"
        return {"action": "open_url", "url": url, "label": raw}

    if text in SITE_MAP:
        return {"action": "open_url", "url": SITE_MAP[text], "label": text.title()}

    # Fuzzy: check if any known site name is contained in the phrase
    for key, url in SITE_MAP.items():
        if key in text:
            return {"action": "open_url", "url": url, "label": key.title()}

    # Fallback: not a known site -> search Google for it instead
    return resolve_google_search(text)


def resolve_google_search(query: str) -> dict:
    query = query.strip() or "google"
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    return {"action": "open_url", "url": url, "label": f'Google search: "{query}"'}


def _find_first_youtube_video_id(query: str) -> Optional[str]:
    """
    Look up YouTube's search results page and pull out the first real
    video ID, so Nova can play the actual top result automatically instead
    of just opening a list of search results. This is a lightweight HTML
    scrape (no API key required) - YouTube embeds a JSON blob called
    ytInitialData in the page that lists videoRenderer entries in order.

    Falls back to None (caller should fall back to opening a search tab)
    if the lookup fails for any reason - network issues, YouTube changing
    their page structure, etc. Never raises.
    """
    try:
        resp = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=5,
        )
        resp.raise_for_status()

        match = re.search(r"var ytInitialData = ({.*?});</script>", resp.text)
        if not match:
            # Try the alternate assignment style YouTube sometimes uses
            match = re.search(r"ytInitialData\"\]\s*=\s*({.*?});", resp.text)
        if not match:
            return None

        data = json.loads(match.group(1))
        video_id = _extract_first_video_id(data)
        return video_id
    except Exception as exc:  # noqa: BLE001 - never let a scrape failure crash Nova
        logger.warning("YouTube lookup failed for %r: %s", query, exc)
        return None


def _extract_first_video_id(node) -> Optional[str]:
    """Recursively walk YouTube's ytInitialData structure for the first videoRenderer."""
    if isinstance(node, dict):
        if "videoRenderer" in node and isinstance(node["videoRenderer"], dict):
            vid = node["videoRenderer"].get("videoId")
            if vid:
                return vid
        for value in node.values():
            found = _extract_first_video_id(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _extract_first_video_id(item)
            if found:
                return found
    return None


def resolve_youtube_command(command_text: str) -> dict:
    """
    Handles: "play <song/topic>", "search <query> on youtube",
    "play this video on youtube".

    Actually looks up the real top result and returns a direct /watch URL
    so the frontend can auto-play it inline - not just a search-results page.
    """
    text = command_text.lower().strip()
    text = re.sub(r"^(nova[,]?\s*)?", "", text)

    play_match = re.match(r"play\s+(.*)", text)
    search_match = re.match(r"search\s+(.*?)\s+on\s+youtube", text)

    query: Optional[str] = None
    if play_match:
        query = play_match.group(1)
    elif search_match:
        query = search_match.group(1)
    else:
        query = text.replace("youtube", "").strip()

    query = query.strip() or "music"

    video_id = _find_first_youtube_video_id(query)
    if video_id:
        return {
            "action": "open_url",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "label": f'"{query}"',
        }

    # Lookup failed for some reason - graceful fallback to a normal search tab
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return {"action": "open_url", "url": url, "label": f'YouTube search: "{query}"'}


# In-page player controls (play/pause/next/mute/fullscreen) are executed
# entirely client-side against the embedded <iframe>/<video> element -
# see static/js/commands.js -> handlePlayerControl().
PLAYER_CONTROL_COMMANDS = {
    "pause", "resume", "play", "next video", "previous video",
    "mute", "unmute", "fullscreen", "exit fullscreen",
    "increase volume", "decrease volume",
}
