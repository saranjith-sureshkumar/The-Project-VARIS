"""
VARIS Brain — Hybrid Intelligence Engine
Priority: Groq cloud (fast, GPT-4 class, free tier) → Phi-3 local (offline fallback)

Why hybrid:
  - Groq (llama-3.3-70B): responds in ~0.5s, far smarter than Phi-3
  - Phi-3 local: works when internet is down, zero cost, your data stays local
  - Personal data (memory, files, screen) NEVER sent to any cloud
  - Only the text of your command goes to Groq — nothing else

Free tier limits (Groq):
  - 14,400 requests/day on free plan — you will never hit this
  - Sign up at console.groq.com → API Keys → Create key → paste in .env
"""

import os, time, threading, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
load_dotenv()

# ── Model config ──────────────────────────────────────────────────────────────
GROQ_KEY        = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = "llama-3.3-70b-versatile"          # Best free Groq model
GROQ_URL        = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_URL      = "http://localhost:11434/api/generate"

# ── Shared HTTP session (connection reuse, retry) ─────────────────────────────
_session = requests.Session()
_session.mount("http://",  HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.3)))
_session.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.3)))

# ── Internet + Groq availability (cached, re-checked every 60s) ───────────────
_groq_available   = False
_groq_last_check  = 0.0
_groq_lock        = threading.Lock()

def _check_groq() -> bool:
    """Returns True if Groq API key is set and reachable."""
    global _groq_available, _groq_last_check
    with _groq_lock:
        now = time.time()
        if now - _groq_last_check < 60:
            return _groq_available
        if not GROQ_KEY or len(GROQ_KEY) < 20:
            _groq_available = False
            _groq_last_check = now
            return False
        try:
            # Lightweight ping — tiny prompt, 1 token
            r = _session.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": GROQ_MODEL,
                      "messages": [{"role": "user", "content": "hi"}],
                      "max_tokens": 1},
                timeout=4)
            _groq_available = r.status_code in (200, 400)  # 400 = reached, wrong input
            _groq_last_check = now
        except Exception:
            _groq_available = False
            _groq_last_check = now
        return _groq_available

def groq_ready() -> bool:
    return _check_groq()

# ── Groq call ─────────────────────────────────────────────────────────────────
def _ask_groq(system: str, user: str, max_tokens: int = 512,
              temperature: float = 0.7) -> str | None:
    """
    Send to Groq. Returns response string or None on failure.
    Only task text is sent. Memory/files/screen content never leaves device.
    """
    if not GROQ_KEY:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    try:
        r = _session.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}",
                     "Content-Type": "application/json"},
            json={"model": GROQ_MODEL,
                  "messages": messages,
                  "max_tokens": max_tokens,
                  "temperature": temperature},
            timeout=15)
        if r.status_code == 429:
            # Rate limit — fall through to local
            print("[LLM] Groq rate limit hit, using local model")
            return None
        if r.status_code == 401:
            print("[LLM] Groq API key invalid — check .env GROQ_API_KEY")
            return None
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.Timeout:
        print("[LLM] Groq timeout, falling back to local")
        return None
    except Exception as e:
        print(f"[LLM] Groq error: {type(e).__name__} — falling back to local")
        return None

# ── Ollama / Phi-3 call ───────────────────────────────────────────────────────
def _friendly_ollama_error(e) -> str:
    s = str(e)
    if "11434" in s or "Connection" in type(e).__name__:
        return "AI brain offline. Start Ollama or check your internet for cloud AI."
    if "Timeout" in type(e).__name__ or "timed out" in s.lower():
        return "AI is taking too long. Try a shorter question."
    if "not found" in s.lower():
        return f"Model {OLLAMA_MODEL} not downloaded. Run: ollama pull {OLLAMA_MODEL}"
    return "AI error. Please try again."

def _ask_ollama(system: str, user: str, max_tokens: int = 512,
                temperature: float = 0.7) -> str:
    """Send to local Ollama/Phi-3. Always works offline."""
    full_prompt = (f"{system}\n\nUser: {user}\nVARIS:" if system
                   else f"User: {user}\nVARIS:")
    try:
        r = _session.post(OLLAMA_URL,
            json={"model": OLLAMA_MODEL,
                  "system": system if system else "",
                  "prompt": user,
                  "stream": False,
                  "options": {"temperature": temperature,
                               "num_predict": max_tokens}},
            timeout=60)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        return _friendly_ollama_error(e)

# ── Public API — these are the functions all agents call ─────────────────────

def ask_llm(prompt: str, context: str = "", max_tokens: int = 512) -> str:
    """
    General ask. Tries Groq first, falls back to local Phi-3.
    Usage: ask_llm("classify this command", max_tokens=10)
    """
    system = "You are VARIS, a concise AI assistant. Keep answers under 4 sentences."
    user   = f"{context}\n\n{prompt}" if context else prompt

    if _check_groq():
        result = _ask_groq(system, user, max_tokens, temperature=0.7)
        if result:
            return result

    return _ask_ollama(system, user, max_tokens, temperature=0.7)


def ask_llm_with_system(system: str, user: str, max_tokens: int = 512) -> str:
    """
    Ask with a custom system prompt. Used by all agents for structured tasks.
    Usage: ask_llm_with_system("Write a formal email", "Topic: leave request")
    """
    if _check_groq():
        result = _ask_groq(system, user, max_tokens, temperature=0.5)
        if result:
            return result

    return _ask_ollama(system, user, max_tokens, temperature=0.5)


def ask_llm_fast(prompt: str, max_tokens: int = 20) -> str:
    """
    Ultra-fast classification call (intent routing, yes/no decisions).
    Groq only — if offline, falls back gracefully.
    Usage: ask_llm_fast("Classify: FILE BROWSER EMAIL SYSTEM", max_tokens=5)
    """
    system = "Reply with ONLY the requested label or word. No explanation."
    if _check_groq():
        result = _ask_groq(system, prompt, max_tokens, temperature=0.1)
        if result:
            return result.strip().upper()

    return _ask_ollama(system, prompt, max_tokens, temperature=0.1)


# ── Health checks ─────────────────────────────────────────────────────────────

def check_ollama_health() -> bool:
    try:
        r = _session.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            models = r.json().get("models", [])
            return any(OLLAMA_MODEL in m.get("name", "") for m in models)
        return False
    except Exception:
        return False


def get_brain_status() -> dict:
    """Returns current AI backend status for startup display."""
    groq_ok   = _check_groq()
    ollama_ok = check_ollama_health()
    return {
        "groq_available":  groq_ok,
        "ollama_available": ollama_ok,
        "active_backend":  "Groq (cloud)" if groq_ok else
                           ("Phi-3 (local)" if ollama_ok else "OFFLINE"),
        "model": GROQ_MODEL if groq_ok else OLLAMA_MODEL,
    }


# ── Startup probe (non-blocking) ──────────────────────────────────────────────
def probe_backends_async():
    """Call once at startup in a background thread to warm the cache."""
    threading.Thread(target=_check_groq, daemon=True).start()
