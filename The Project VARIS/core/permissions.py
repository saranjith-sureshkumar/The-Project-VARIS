"""
VARIS Permission Manager — first-launch consent system.
VARIS asks for permission before accessing ANYTHING.
This is what makes VARIS fundamentally different from every other AI.
Permissions stored in data/permissions.json — edit anytime to change.
"""
import json
from pathlib import Path

FILE = Path("data/permissions.json")

DEFAULTS = {
    "microphone": {"enabled": False, "where": "100% Local — never leaves device"},
    "screen":     {"enabled": False, "where": "100% Local — OCR runs on-device"},
    "files":      {"enabled": False, "where": "100% Local — no upload ever"},
    "email":      {"enabled": False, "where": "Local + task text sent to AI only"},
    "browser":    {"enabled": False, "where": "100% Local — opens your browser"},
    "system":     {"enabled": False, "where": "100% Local — reads your stats"},
    "memory":     {"enabled": False, "where": "100% Local — stored in data/"},
    "cloud_ai":   {"enabled": False, "where": "Task text ONLY — no personal data sent"},
    "tasks":      {"enabled": False, "where": "100% Local — stored in data/tasks.json"},
}

DESCRIPTIONS = {
    "microphone": "Voice commands — required for voice control features",
    "screen":     "Screen capture — powers visual memory and Recall feature",
    "files":      "File access — organise, sort and find your files by voice",
    "email":      "Email agent — AI drafts emails, you confirm before sending",
    "browser":    "Browser control — open websites and search by voice",
    "system":     "System monitoring — explains what your computer is doing",
    "memory":     "Persistent memory — VARIS remembers your history across sessions",
    "cloud_ai":   "Cloud AI boost — faster, smarter responses (task text only, no personal data)",
    "tasks":      "Task manager — reminders, Pomodoro timers, exam countdowns",
}

def load_permissions() -> dict | None:
    """Returns saved permissions or None if first launch."""
    if FILE.exists():
        try:
            return json.loads(FILE.read_text())
        except Exception:
            return None
    return None

def save_permissions(perms: dict):
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(perms, indent=2))

def run_first_launch() -> dict:
    """Interactive first-launch permission setup."""
    print("\n" + "=" * 58)
    print("  VARIS — FIRST LAUNCH PERMISSION SETUP")
    print("=" * 58)
    print("\n  VARIS never accesses anything without your explicit")
    print("  permission. You control exactly what it can do.\n")

    perms = {k: dict(v) for k, v in DEFAULTS.items()}

    for name, details in perms.items():
        print(f"\n  [{name.upper()}]")
        print(f"  What: {DESCRIPTIONS.get(name, '')}")
        print(f"  Data: {details['where']}")
        try:
            ans = input("  Allow? (yes/no, default no): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "no"
        perms[name]["enabled"] = ans in ("yes", "y")
        status = "✓ Allowed" if perms[name]["enabled"] else "✗ Denied"
        print(f"  → {status}")

    save_permissions(perms)
    print("\n" + "=" * 58)
    print("  Permissions saved to data/permissions.json")
    print("  Edit that file anytime to change your choices.")
    print("=" * 58 + "\n")
    return perms

def check_permission(name: str) -> bool:
    """Check if a specific permission is granted. Used by agents."""
    p = load_permissions()
    if p is None:
        return False
    return p.get(name, {}).get("enabled", False)

def get_all_permissions() -> dict:
    """Return all permissions with their current state."""
    return load_permissions() or {k: dict(v) for k, v in DEFAULTS.items()}
