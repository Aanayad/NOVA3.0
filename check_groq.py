"""
Nova 3.0 - Groq key diagnostic tool.

Run this directly to confirm your keys actually work before starting the
full app:

    python check_groq.py
"""

from config.config import Config


def test_key(label: str, api_key: str) -> None:
    print(f"\n--- Testing {label} ---")
    if not api_key:
        print("  [SKIPPED] This key is empty in your .env file.")
        return

    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 12 else "(too short?)"
    print(f"  Key found: {masked}  (length: {len(api_key)})")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[{"role": "user", "content": "Say 'Nova is connected' and nothing else."}],
            max_tokens=20,
        )
        text = response.choices[0].message.content
        print(f"  [SUCCESS] Groq replied: {text!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAILED] {type(exc).__name__}: {exc}")
        print("  ^ Common causes:")
        print("    - Key was copied incompletely, or wrapped in quotes in .env")
        print("    - Free-tier rate limit hit (wait ~60s and retry)")
        print("    - GROQ_MODEL name is wrong/outdated - check console.groq.com for current model names")


if __name__ == "__main__":
    print("Nova 3.0 - Groq connectivity check")
    print(f"Model configured: {Config.GROQ_MODEL}")
    test_key("GROQ_API_KEY_1", Config.GROQ_API_KEY_1)
    test_key("GROQ_API_KEY_2", Config.GROQ_API_KEY_2)
    print("\nDone.")
