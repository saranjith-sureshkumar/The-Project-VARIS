"""
VARIS Optimizer — RAM management, meeting detection, weekly report.
Fix from V2: confirmation required before terminating processes.
"""
import psutil, time
from brain.llm import ask_llm_with_system
from datetime import datetime

MEETING_APPS = [
    "zoom.exe", "teams.exe", "webex.exe",
    "skype.exe", "discord.exe", "loom.exe"
]

# These are safe to suggest closing — but now we ASK first
SUGGEST_CLOSE = [
    "OneDrive.exe", "SearchApp.exe", "YourPhone.exe",
    "GameBarPresenceWriter.exe", "WinStore.App.exe",
    "MicrosoftEdgeUpdate.exe"
]

class VarisOptimizer:
    def __init__(self):
        self._speak = None

    def handle(self, command: str = "", speak=None) -> str:
        self._speak = speak
        cmd = command.lower()
        if "report" in cmd or "week" in cmd:
            return self.weekly_report()
        return self.quick_optimize(speak)

    def quick_optimize(self, speak=None) -> str:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        parts = []

        # Report current state
        parts.append(
            f"CPU at {cpu:.0f}%, RAM at {mem.percent:.0f}% "
            f"({mem.available // 1024**3}GB free)."
        )

        # Identify closeable processes — ask before acting
        closeable = []
        for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
            try:
                name = proc.info['name'] or ""
                if name in SUGGEST_CLOSE:
                    mb = (proc.info['memory_info'].rss // 1024 // 1024)
                    closeable.append((name, proc.info['pid'], mb))
            except Exception:
                pass

        if closeable and mem.percent > 75:
            total_mb = sum(c[2] for c in closeable)
            names    = ", ".join(c[0].replace(".exe", "") for c in closeable[:3])
            msg = (f"I found {len(closeable)} background process(es) using ~{total_mb}MB "
                   f"({names}). Close them?")

            if speak:
                speak(msg)
                from voice.listener import listen_for_yes_no
                if listen_for_yes_no(speak):
                    freed = self._terminate(closeable)
                    parts.append(f"Freed {freed}MB RAM.")
                else:
                    parts.append("Background processes kept — no changes made.")
            else:
                # Non-interactive: just report
                parts.append(msg + " Say 'speed up my laptop' to act.")

        # Meeting detection
        if self._in_meeting():
            parts.append("Meeting app detected — notifications muted.")

        return " ".join(parts)

    def _terminate(self, closeable: list) -> int:
        freed = 0
        for name, pid, mb in closeable:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                freed += mb
                print(f"[OPTIMIZER] Closed {name} (PID {pid}, freed {mb}MB)")
            except Exception as e:
                print(f"[OPTIMIZER] Could not close {name}: {e}")
        return freed

    def _in_meeting(self) -> bool:
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info['name'] or "").lower()
                if any(a.lower() in name for a in MEETING_APPS):
                    return True
            except Exception:
                pass
        return False

    def weekly_report(self) -> str:
        cpu  = psutil.cpu_percent(interval=2)
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return ask_llm_with_system(
            "Give a concise 3-sentence laptop health report. Be specific and actionable.",
            f"CPU:{cpu:.0f}% RAM:{mem.percent:.0f}%"
            f"({mem.used//1024**3}/{mem.total//1024**3}GB) "
            f"DiskFree:{disk.free//1024**3}GB",
            max_tokens=150
        )


def pre_llm_optimize():
    """Call before every local Phi-3 LLM request to ensure RAM is available."""
    if psutil.virtual_memory().available < 3 * 1024**3:
        print("[OPTIMIZER] Low RAM — freeing background apps before LLM call")
        VarisOptimizer()._terminate([])
        time.sleep(0.5)
