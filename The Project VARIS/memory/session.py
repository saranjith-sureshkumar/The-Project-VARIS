"""
VARIS Session — crash recovery and resume.
Fix from V2: command_history captured correctly even on early SIGINT.
"""
import json
from pathlib import Path
from datetime import datetime

FILE = Path("data/session.json")

def save_session(history: list):
    """Save last 10 commands for crash recovery."""
    FILE.parent.mkdir(exist_ok=True)
    try:
        FILE.write_text(json.dumps({
            "saved_at":      datetime.now().isoformat(),
            "last_commands": list(history[-10:]) if history else []
        }, indent=2))
    except Exception as e:
        print(f"[SESSION] Save error: {e}")

def load_session() -> dict | None:
    if not FILE.exists():
        return None
    try:
        return json.loads(FILE.read_text())
    except Exception:
        return None

def get_resume_message() -> str | None:
    """Returns a spoken resume message if there's a previous session."""
    s = load_session()
    if not s or not s.get("last_commands"):
        return None
    saved  = s.get("saved_at", "")[:16].replace("T", " ")
    last   = s["last_commands"][-1]
    count  = len(s["last_commands"])
    return (f"Welcome back. Last session ended at {saved}. "
            f"You had {count} command(s). Last one: '{last}'.")
