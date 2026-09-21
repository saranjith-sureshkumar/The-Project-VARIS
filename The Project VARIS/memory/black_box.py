"""
VARIS Black Box — tamper-evident audit log.
Every voice command, agent decision, and error is recorded here.
Rotate at 5MB. SHA-256 hash per entry for integrity.
"""
import json, os, hashlib
from datetime import datetime
from pathlib import Path

LOG = Path("logs/black_box.jsonl")

class BlackBox:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)

    def record(self, event_type: str, input_text: str,
               output_text: str, agent: str, reasoning: str = ""):
        """Record one event. Hash ensures tamper-evidence."""
        ts    = datetime.now().isoformat()
        entry = {
            "timestamp":  ts,
            "event_type": event_type,
            "agent":      agent,
            "input":      input_text[:500],    # Truncate very long inputs
            "output":     output_text[:500],
            "reasoning":  reasoning[:200],
        }
        # Hash for integrity check
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Rotate at 5MB
        try:
            if LOG.exists() and LOG.stat().st_size > 5_000_000:
                import shutil
                archive = f"logs/black_box_{datetime.now().strftime('%Y%m')}.jsonl"
                shutil.move(str(LOG), archive)
                print(f"[BLACK BOX] Rotated to {archive}")
        except Exception:
            pass

        try:
            with open(LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[BLACK BOX] Write error: {e}")

    def replay(self, n: int = 10) -> list:
        """Return last N entries for audit."""
        if not LOG.exists():
            return []
        entries = []
        try:
            with open(LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            return []
        return entries[-n:]

    def verify(self) -> dict:
        """Check log integrity — returns count and any tampered entries."""
        entries  = self.replay(n=9999)
        tampered = []
        for entry in entries:
            stored_hash = entry.pop("hash", None)
            computed    = hashlib.sha256(
                json.dumps(entry, sort_keys=True).encode()
            ).hexdigest()[:16]
            if stored_hash and stored_hash != computed:
                tampered.append(entry.get("timestamp", "unknown"))
            entry["hash"] = stored_hash  # Restore
        return {
            "total":    len(entries),
            "tampered": len(tampered),
            "clean":    len(entries) - len(tampered)
        }
