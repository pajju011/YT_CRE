import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent

def load_env():
    env_file = ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

ENV = load_env()
API_KEY = ENV.get("MAITOKEN_API_KEY", "")
BASE_URL = ENV.get("MAITOKEN_BASE_URL", "https://api.maitoken.net/v1").rstrip("/")

def check_balance():
    """Checks if the key is valid and has positive balance."""
    if not API_KEY:
        return {"ok": False, "error": "No API key configured in .env"}
    
    url = f"{BASE_URL}/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "Mozilla/5.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "models_count": len(data.get("data", []))}
    except urllib.error.HTTPError as e:
        return {"ok": False, "code": e.code, "error": e.read().decode()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def generate_script(prompt, category="math"):
    """
    Attempts to generate a structured 6-beat script using MaiToken.
    Falls back gracefully if credits are 0 or API fails.
    """
    if not API_KEY:
        return None

    system_prompt = (
        "You are an expert YouTube Shorts director. Convert the user prompt into a high-retention 6-beat short script.\n"
        "Return ONLY a JSON object with this exact schema:\n"
        "{\n"
        '  "title": "Short title",\n'
        '  "vo": [\n'
        '    {"beat": "hook", "text": "Thumb-stopping opening question or payoff (max 10 words).", "start": 0.4, "end": 3.5},\n'
        '    {"beat": "setup", "text": "Establish the context or conventional way.", "start": 3.8, "end": 7.5},\n'
        '    {"beat": "quiz", "text": "Challenge the viewer or build curiosity.", "start": 7.8, "end": 12.0},\n'
        '    {"beat": "reveal", "text": "Deliver the core insight or trick step-by-step.", "start": 12.5, "end": 22.0},\n'
        '    {"beat": "twist", "text": "Unexpected counter-intuitive application or edge case.", "start": 22.5, "end": 31.0},\n'
        '    {"beat": "loop", "text": "Closing line that grammatically loops back into the hook without any like/subscribe outro.", "start": 31.5, "end": 40.0}\n'
        "  ]\n"
        "}"
    )

    payload = json.dumps({
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Topic: {prompt}\nCategory: {category}"}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[MaiToken Warning] HTTP {e.code}: {err_body}")
        return None
    except Exception as e:
        print(f"[MaiToken Warning] {e}")
        return None

if __name__ == "__main__":
    print("Testing MaiToken configuration...")
    bal = check_balance()
    print("Status:", bal)
