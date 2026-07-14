# Nova 3.0 — Alexa-style Voice Assistant

A dark/purple, premium voice-first assistant: say "Nova" and it searches
Google, plays the actual top YouTube result automatically, opens websites,
and talks back to you — powered by Groq (free, fast AI). Nothing is saved
to disk — no chat history, no database. Each session lives in memory only.

---

## 1. What this build does (and deliberately doesn't)

| Feature | Status |
|---|---|
| "Nova search X" → opens a real Google search | ✅ Works |
| "Nova play X" → finds and auto-plays the actual top YouTube result inline | ✅ Works (live lookup, no API key needed) |
| "Nova open X" → opens any website in a new tab | ✅ Works |
| Speaks every reply back to you (TTS) | ✅ Works |
| Understands your voice, wake word "Nova" (STT) | ✅ Works (Chrome/Edge) |
| Chat history / saved conversations | ❌ Intentionally removed — nothing is written to disk |
| Native app control (shutdown, open VS Code, volume, etc.) | ✅ Works, but **only locally** with `ENABLE_SYSTEM_CONTROL=true` — a hosted server cannot control your OS, for the same reason no web app can |

---

## 2. Installation

```bash
git clone <your-fork-url> NOVA3.0
cd NOVA3.0

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
```

### Get free Groq API keys (no credit card)
1. Go to https://console.groq.com/keys
2. Sign in, click "Create API Key"
3. Copy it straight into `.env` as `GROQ_API_KEY_1` — **no quotes, no extra spaces**
4. Repeat with a second Groq account/project for `GROQ_API_KEY_2`, so load balancing gives you a real second quota pool

### Verify your keys work BEFORE starting the app
```bash
python check_groq.py
```
You should see `[SUCCESS] Groq replied: 'Nova is connected'` for at least one key. If it fails, the script prints the exact error from Groq — fix that first.

### Run it
```bash
python app.py
# -> open http://localhost:5000 in Chrome or Edge (needed for the wake-word mic)
```

Say **"Nova"**, then try:
- *"search python tutorial"* → opens a real Google search tab
- *"play Diljit Dosanjh"* → looks up the real top YouTube result and **auto-plays it inline**
- *"open github"* → opens github.com in a new tab

---

## 3. Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY_1` / `_2` | Recommended | Free keys from console.groq.com. Nova automatically fails over between them and never crashes even with none set (falls back to a safe offline reply). |
| `GROQ_MODEL` | No | Defaults to `llama-3.3-70b-versatile`. For higher free daily request limits, try `llama-3.1-8b-instant`. |
| `FLASK_SECRET_KEY` / `JWT_SECRET_KEY` | Yes for production | Long random strings — generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ENABLE_SYSTEM_CONTROL` | No | `true` only when running locally and you want Nova to control this machine (shutdown, open native apps, volume, etc). Keep `false` on any hosted deployment. |
| `RATE_LIMIT_DEFAULT` | No | Flask-Limiter default, e.g. `60 per minute`. |

**Important:** never wrap values in quotes in `.env` — write `GROQ_API_KEY_1=abc123`, not `GROQ_API_KEY_1="abc123"`.

---

## 4. How the auto-play YouTube feature works

`automation/browser_automation.py` sends a real HTTP request to YouTube's
search page, parses the embedded `ytInitialData` JSON for the first actual
video result, and returns its direct `/watch?v=...` URL. The frontend then
embeds that specific video with `autoplay=1` in an inline player — so "Nova
play Diljit Dosanjh" plays an actual song, not just a list of search
results. If the lookup ever fails (network hiccup, YouTube changing their
page structure), it gracefully falls back to opening a normal search tab
instead of breaking.

---

## 5. Architecture

```
Browser (voice + chat UI, no history stored)
        │ REST (fetch)
        ▼
Flask app.py → api/routes.py
        │                    │
        ▼                    ▼
ai/groq_brain.py      automation/
(Groq, dual-key,        command_router.py
 in-memory only)         browser_automation.py (incl. YouTube lookup)
                          system_control.py (local only)
                          file_manager.py (local only)
```

No `database/` folder in this build — that's intentional, not missing.

---

## 6. Deployment

Same as before — Render, Railway, or Docker all work for the Flask backend:
```bash
docker build -t nova3 .
docker run -p 5000:5000 --env-file .env nova3
```
Keep `ENABLE_SYSTEM_CONTROL=false` on any hosted deployment.

---

## 7. Troubleshooting

- **Wake word doesn't trigger** — use Chrome/Edge over `localhost` or HTTPS (mic access needs a secure context).
- **Groq errors** — run `python check_groq.py` first; it shows Groq's exact error message (rate limit, bad key, wrong model name) instead of a generic fallback.
- **YouTube doesn't auto-play** — check your terminal for a "YouTube lookup failed" warning; this means the live scrape failed (network issue or YouTube changed their page) and Nova fell back to a normal search tab instead — try again, or open the tab manually.
- **System commands do nothing** — confirm `ENABLE_SYSTEM_CONTROL=true` in `.env` and that you're running locally.

---

## 8. License
MIT.
