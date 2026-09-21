"""
VARIS Speaker — neural voice output.
Priority: edge-tts (Indian English, neural) → Windows SAPI → print fallback.
Improvements over V2:
  - Asyncio event loop conflict fix (works in threads)
  - Long text chunking (edge-tts fails on very long strings)
  - Internet check cached at startup, re-checked every 5 minutes
  - Linux/macOS: espeak-ng fallback instead of SAPI
  - Speaking indicator for terminal
"""
import os, asyncio, tempfile, threading, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

VOICE      = os.getenv("VARIS_VOICE", "en-IN-NeerjaNeural")
MAX_CHARS  = 800   # edge-tts max per chunk
_speak_lock    = threading.Lock()
_internet_ok   = False
_last_net_check = 0.0
_net_check_lock = threading.Lock()

# ── Internet check (cached 5 minutes) ────────────────────────────────────────
def _check_internet() -> bool:
    global _internet_ok, _last_net_check
    with _net_check_lock:
        now = time.time()
        if now - _last_net_check < 300:   # 5-minute cache
            return _internet_ok
        try:
            import socket
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                ("8.8.8.8", 53)
            )
            _internet_ok   = True
        except Exception:
            _internet_ok   = False
        _last_net_check = now
        return _internet_ok

# Run initial check at import (non-blocking)
threading.Thread(target=_check_internet, daemon=True).start()

# ── Text chunking (split on sentence boundaries) ──────────────────────────────
def _chunk_text(text: str, max_len: int = MAX_CHARS) -> list[str]:
    """Split long text into chunks at sentence boundaries."""
    if len(text) <= max_len:
        return [text]
    chunks  = []
    current = ""
    for sentence in text.replace("! ", ". ").replace("? ", ". ").split(". "):
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = (current + ". " + sentence).strip() if current else sentence
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current + ".")
            current = sentence
    if current:
        chunks.append(current if current.endswith(".") else current + ".")
    return chunks if chunks else [text[:max_len]]

# ── edge-tts (neural, Indian English) ─────────────────────────────────────────
async def _edge_tts_chunk(text: str, voice: str):
    """Speak one chunk via edge-tts."""
    import edge_tts
    Path("data").mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".mp3", dir="data"
    ) as f:
        tmp = f.name

    await edge_tts.Communicate(text, voice).save(tmp)

    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except Exception:
        # pygame not available — try playsound
        try:
            import playsound
            playsound.playsound(tmp)
        except Exception:
            pass
    finally:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass

def _run_edge_tts(text: str, voice: str):
    """Run edge-tts in a clean event loop (avoids thread conflicts)."""
    try:
        # Python 3.10+ preferred method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        chunks = _chunk_text(text)
        for chunk in chunks:
            if chunk.strip():
                loop.run_until_complete(_edge_tts_chunk(chunk, voice))
        loop.close()
    except Exception as e:
        print(f"[SPEAKER] edge-tts error: {e} — switching to offline voice")
        _offline_speak(text)

# ── Offline fallback (SAPI / espeak) ─────────────────────────────────────────
def _offline_speak(text: str):
    """Platform-appropriate offline TTS."""
    import sys
    if sys.platform == "win32":
        _sapi_speak(text)
    elif sys.platform == "darwin":
        _macos_speak(text)
    else:
        _espeak_speak(text)

def _sapi_speak(text: str):
    """Windows SAPI voice (no internet needed)."""
    try:
        import win32com.client
        sapi = win32com.client.Dispatch("SAPI.SpVoice")
        sapi.Rate   = 1
        sapi.Volume = 100
        sapi.Speak(text)
    except Exception as e:
        print(f"[SPEAKER] SAPI error: {e}")
        print(f"[VARIS] {text}")

def _macos_speak(text: str):
    """macOS 'say' command."""
    import subprocess
    try:
        subprocess.run(["say", "-r", "185", text], timeout=30)
    except Exception:
        print(f"[VARIS] {text}")

def _espeak_speak(text: str):
    """Linux espeak-ng."""
    import subprocess
    try:
        subprocess.run(
            ["espeak-ng", "-v", "en-in", "-s", "160", text],
            timeout=30, capture_output=True
        )
    except FileNotFoundError:
        try:
            subprocess.run(
                ["espeak", "-v", "en", "-s", "160", text],
                timeout=30, capture_output=True
            )
        except FileNotFoundError:
            print(f"[VARIS] {text}")
    except Exception:
        print(f"[VARIS] {text}")

# ── Public API ─────────────────────────────────────────────────────────────────
def speak(text: str):
    """
    Speak text aloud. Thread-safe.
    Uses edge-tts (online) → SAPI/espeak (offline) → print fallback.
    """
    if not text or not text.strip():
        return

    # Print always (terminal feedback)
    print(f"[VARIS] {text}")

    with _speak_lock:
        if _check_internet():
            try:
                _run_edge_tts(text, VOICE)
                return
            except Exception:
                pass
        _offline_speak(text)


def speak_async(text: str):
    """Speak without blocking the caller."""
    threading.Thread(target=speak, args=(text,), daemon=True).start()
