# Nova 3.0 —  Voice Assistant

A dark/purple, premium voice-first assistant: say "Nova" and it searches
Google, plays the actual top YouTube result automatically, opens websites,
and talks back to you — powered by Groq (free, fast AI). Nothing is saved
to disk — no chat history, no database. Each session lives in memory only.

---


## 1. Installation

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
