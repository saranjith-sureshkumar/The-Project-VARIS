"""
VARIS — Virtual Agent for Reasoning, Intelligence & Sovereignty
Main entry point — fully wired: permissions, system detector,
black box, screen recall, intent compiler, hybrid LLM, alert queue.
"""
import os, sys, time, threading, signal
from pathlib import Path

print("""
╔══════════════════════════════════════════════════════════╗
║        V . A . R . I . S                                ║
║   Virtual Agent for Reasoning, Intelligence & Sovereignty║
║   Your AI OS — Loyal only to you                        ║
╚══════════════════════════════════════════════════════════╝
""")

from dotenv import load_dotenv
load_dotenv()

# ── PID lock — prevent double launch ─────────────────────────────────────────
def _acquire_pid_lock():
    lock = Path("data/varis.lock")
    lock.parent.mkdir(exist_ok=True)
    if lock.exists():
        try:
            import psutil
            pid = int(lock.read_text().strip())
            if psutil.pid_exists(pid):
                print("[ERROR] VARIS already running. Close the other instance first.")
                sys.exit(1)
        except Exception:
            pass
    lock.write_text(str(os.getpid()))

def _release_pid_lock():
    p = Path("data/varis.lock")
    if p.exists():
        p.unlink()

# ── Step 1: Detect hardware, set optimal models ───────────────────────────────
def _setup_hardware():
    from core.system_detector import detect, print_report
    spec = print_report()
    # Apply detected models to env if not already overridden by user
    if not os.getenv("WHISPER_MODEL"):
        os.environ["WHISPER_MODEL"] = spec["whisper_model"]
    if not os.getenv("OLLAMA_MODEL"):
        os.environ["OLLAMA_MODEL"] = spec["ollama_model"]
    return spec

# ── Step 2: First-launch permission consent ───────────────────────────────────
def _setup_permissions():
    from core.permissions import load_permissions, run_first_launch
    perms = load_permissions()
    if perms is None:
        print("\n[FIRST LAUNCH] Setting up permissions...\n")
        perms = run_first_launch()
    return perms

# ── Step 3: Check and start Ollama (local fallback) ───────────────────────────
def _ensure_ollama():
    model = os.getenv("OLLAMA_MODEL", "phi3")
    print(f"[STARTUP] Checking Ollama ({model})...")
    for attempt in range(3):
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if not any(model in m for m in models):
                    print(f"[STARTUP] Downloading {model} (~2.4GB, first time only)...")
                    import subprocess
                    subprocess.run(["ollama", "pull", model], check=True)
                print(f"[STARTUP] Local AI ({model}) ready")
                return True
        except Exception:
            if attempt == 0:
                print("[STARTUP] Starting Ollama service...")
                import subprocess
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(5)
    print("[STARTUP] Ollama not reachable — cloud AI will be used if configured")
    return False

# ── Step 4: Show AI backend status ────────────────────────────────────────────
def _show_brain_status():
    from brain.llm import get_brain_status, probe_backends_async
    probe_backends_async()
    time.sleep(1)  # Brief wait for async probe
    status = get_brain_status()
    backend = status["active_backend"]
    model   = status["model"]
    if status["groq_available"]:
        print(f"[BRAIN] ⚡ Groq cloud active — {model} (fast mode)")
        print(f"[BRAIN]    Local Phi-3 standing by as offline fallback")
    elif status["ollama_available"]:
        print(f"[BRAIN] 🧠 Local Phi-3 active — offline mode")
        print(f"[BRAIN]    Add GROQ_API_KEY to .env for 10x faster responses")
    else:
        print("[BRAIN] ⚠️  No AI backend ready — check Ollama or GROQ_API_KEY")

# ── Step 5: Warm up model (background) ───────────────────────────────────────
def _warmup():
    try:
        import requests
        requests.post("http://localhost:11434/api/generate",
            json={"model": os.getenv("OLLAMA_MODEL","phi3"),
                  "prompt": "hi", "stream": False},
            timeout=30)
        print("[STARTUP] Local model warmed up")
    except Exception:
        pass

# ── Security check: credentials not hardcoded ─────────────────────────────────
def _check_credentials():
    f = Path("agents/email_agent.py")
    if f.exists() and "your_email@gmail.com" in f.read_text():
        print("[SECURITY WARNING] Move Gmail credentials to .env file!\n")

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    _acquire_pid_lock()
    command_history = []   # Defined before signal handler captures it

    def _shutdown(sig=None, frame=None):
        print("\n[VARIS] Shutting down...")
        from memory.session import save_session
        save_session(command_history)
        _release_pid_lock()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        # ── Boot sequence ──────────────────────────────────────────────────
        _check_credentials()
        spec  = _setup_hardware()
        perms = _setup_permissions()
        _ensure_ollama()
        _show_brain_status()
        threading.Thread(target=_warmup, daemon=True).start()

        # ── Core imports ───────────────────────────────────────────────────
        from voice.listener  import listen, calibrate_microphone
        from voice.speaker   import speak
        from brain.router    import route_command
        from memory.graph    import VarisMemory
        from memory.black_box import BlackBox
        from memory.session  import save_session, get_resume_message
        from core.alert_queue import AlertQueue
        from agents.guardian_agent  import GuardianAgent
        from agents.morning_debrief import morning_debrief

        # ── Initialise subsystems ──────────────────────────────────────────
        memory    = VarisMemory()
        black_box = BlackBox()
        alert_queue = AlertQueue()

        # Guardian — background security monitor
        guardian = GuardianAgent()
        guardian.set_alert_queue(alert_queue)
        threading.Thread(target=guardian.start, daemon=True).start()

        # Screen recall — visual memory capture (if permitted)
        if perms.get("screen", {}).get("enabled", False):
            try:
                from agents.recall_agent import RecallAgent
                recall = RecallAgent()
                recall.start_capture(interval=60)
                print("[RECALL] Screen memory capture active")
            except Exception as e:
                print(f"[RECALL] Not available: {e}")

        # Microphone calibration
        if perms.get("microphone", {}).get("enabled", True):
            calibrate_microphone()

        # ── Greet user ─────────────────────────────────────────────────────
        morning_debrief(speak)

        resume_msg = get_resume_message()
        if resume_msg:
            speak(resume_msg)

        speak("VARIS is online. How can I help you?")
        print("\n[VARIS] Listening... (say 'quit' to exit)\n")
        print("─" * 54)

        # ── Main voice loop ────────────────────────────────────────────────
        while True:
            # Deliver any guardian alerts before listening
            alert = alert_queue.get_alert()
            if alert:
                speak(f"Security alert: {alert}")
                black_box.record("guardian_alert", "", alert, "guardian")

            command = listen()
            if not command:
                continue

            # Exit commands
            if command.lower().strip() in {"quit","exit","stop","bye","goodbye","shutdown"}:
                speak("VARIS shutting down. Goodbye.")
                break

            print(f"[YOU]   {command}")
            command_history.append(command)
            if len(command_history) > 20:
                command_history.pop(0)

            # Save to memory
            if perms.get("memory", {}).get("enabled", True):
                memory.save_interaction(command, "user")

            # Route and execute
            try:
                response = route_command(command, memory, speak, command_history)
                if response:
                    # Save response to memory
                    if perms.get("memory", {}).get("enabled", True):
                        memory.save_interaction(response, "varis")
                    # Black box — audit log every interaction
                    black_box.record(
                        event_type="voice_command",
                        input_text=command,
                        output_text=response,
                        agent="router",
                        reasoning=f"history_len={len(command_history)}"
                    )

            except Exception as e:
                etype = type(e).__name__
                if "Connection" in etype:
                    msg = "Cannot reach AI. Check your connection."
                elif "Permission" in etype:
                    msg = "Permission denied for that action."
                elif "FileNotFound" in etype:
                    msg = "File or folder not found."
                elif "Timeout" in etype:
                    msg = "That took too long. Please try again."
                else:
                    msg = "Something went wrong. Please try again."
                    print(f"[ERROR] {etype}: {e}")
                speak(msg)
                black_box.record("error", command, msg, "main", str(e))

            # Auto-save session every 10 commands
            if len(command_history) % 10 == 0:
                save_session(command_history)

    finally:
        _release_pid_lock()

if __name__ == "__main__":
    main()
