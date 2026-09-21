"""
VARIS Task Agent — reminders, Pomodoro focus timer, exam countdown.
All stored locally in data/tasks.json. No cloud. No sync. Yours only.

Voice commands:
  "Remind me to call mum at 6pm"
  "Set a 25 minute Pomodoro timer"
  "Start focus mode for 45 minutes"
  "My exam is on the 20th — count down"
  "What are my tasks?"
  "Mark task 1 done"
"""
import json, re, threading, time
from datetime import datetime, timedelta
from pathlib import Path
from brain.llm import ask_llm_with_system

TASKS_FILE = Path("data/tasks.json")

def _load_tasks() -> dict:
    TASKS_FILE.parent.mkdir(exist_ok=True)
    if TASKS_FILE.exists():
        try:
            return json.loads(TASKS_FILE.read_text())
        except Exception:
            pass
    return {"reminders": [], "exams": [], "pomodoro": None}

def _save_tasks(data: dict):
    TASKS_FILE.parent.mkdir(exist_ok=True)
    TASKS_FILE.write_text(json.dumps(data, indent=2))

class TaskAgent:
    def __init__(self):
        self._speak    = None
        self._timer    = None
        self._running  = False

    def handle(self, command: str, speak) -> str:
        self._speak = speak
        cmd = command.lower()

        if any(w in cmd for w in ["pomodoro", "focus mode", "focus timer", "focus session"]):
            return self._start_pomodoro(command)

        if any(w in cmd for w in ["remind", "reminder", "remember to", "don't forget"]):
            return self._add_reminder(command)

        if any(w in cmd for w in ["exam", "test", "due date", "deadline", "count down"]):
            return self._add_exam(command)

        if any(w in cmd for w in ["what are my tasks", "list tasks", "show tasks",
                                   "what do i have", "my reminders"]):
            return self._list_tasks()

        if any(w in cmd for w in ["mark done", "complete", "finished", "done with"]):
            return self._mark_done(command)

        if any(w in cmd for w in ["stop timer", "cancel timer", "stop focus", "stop pomodoro"]):
            return self._stop_timer()

        # Let LLM decide what to do
        return self._smart_parse(command)

    # ── Pomodoro ───────────────────────────────────────────────────────────────
    def _start_pomodoro(self, command: str) -> str:
        # Extract duration
        match = re.search(r"(\d+)\s*(min|minute|hour|hr)", command.lower())
        if match:
            val  = int(match.group(1))
            unit = match.group(2)
            minutes = val * 60 if "hour" in unit or unit == "hr" else val
        else:
            minutes = 25  # Classic Pomodoro

        if self._timer and self._timer.is_alive():
            return "A timer is already running. Say 'stop timer' first."

        self._running = True
        self._timer   = threading.Thread(
            target=self._run_timer,
            args=(minutes,),
            daemon=True
        )
        self._timer.start()

        msg = (f"Focus timer started — {minutes} minutes. "
               "I'll alert you when it's done. Stay focused, you've got this.")
        return msg

    def _run_timer(self, minutes: int):
        end_time = time.time() + (minutes * 60)
        # Alert at halfway
        halfway  = time.time() + (minutes * 30)
        alerted_half = False

        while time.time() < end_time and self._running:
            if not alerted_half and time.time() >= halfway:
                if self._speak:
                    self._speak(f"Halfway there — {minutes // 2} minutes done.")
                alerted_half = True
            time.sleep(5)

        if self._running and self._speak:
            self._speak(
                f"Focus session complete! {minutes} minutes done. "
                "Take a 5-minute break — stand up, stretch, hydrate."
            )
        self._running = False

    def _stop_timer(self) -> str:
        self._running = False
        return "Timer stopped."

    # ── Reminders ─────────────────────────────────────────────────────────────
    def _add_reminder(self, command: str) -> str:
        parsed = ask_llm_with_system(
            """Extract reminder details from the command. Return JSON:
{"task": "what to do", "time": "HH:MM or null", "date": "YYYY-MM-DD or null"}
Return ONLY valid JSON.""",
            command, max_tokens=100
        )
        try:
            m = re.search(r'\{.*\}', parsed, re.DOTALL)
            info = json.loads(m.group()) if m else {}
        except Exception:
            info = {}

        task_text = info.get("task", command)
        task_time = info.get("time")
        task_date = info.get("date", str(datetime.now().date()))

        data = _load_tasks()
        task_id = len(data["reminders"]) + 1
        data["reminders"].append({
            "id":    task_id,
            "task":  task_text,
            "time":  task_time,
            "date":  task_date,
            "done":  False,
            "added": datetime.now().isoformat()
        })
        _save_tasks(data)

        time_str = f" at {task_time}" if task_time else ""
        return f"Got it — reminder #{task_id}: '{task_text}'{time_str}."

    # ── Exam countdown ─────────────────────────────────────────────────────────
    def _add_exam(self, command: str) -> str:
        parsed = ask_llm_with_system(
            """Extract exam details. Return JSON:
{"subject": "subject name", "date": "YYYY-MM-DD"}
If no year given, assume current year. Return ONLY valid JSON.""",
            f"Today: {datetime.now().date()}\nCommand: {command}",
            max_tokens=80
        )
        try:
            m = re.search(r'\{.*\}', parsed, re.DOTALL)
            info = json.loads(m.group()) if m else {}
        except Exception:
            info = {}

        subject   = info.get("subject", "exam")
        exam_date = info.get("date")

        if not exam_date:
            return "I couldn't find a date. Try: 'My Python exam is on December 20th'."

        try:
            exam_dt = datetime.strptime(exam_date, "%Y-%m-%d")
            days_left = (exam_dt.date() - datetime.now().date()).days
        except ValueError:
            return f"Date format not recognised: {exam_date}."

        data = _load_tasks()
        data["exams"].append({
            "subject":  subject,
            "date":     exam_date,
            "added":    datetime.now().isoformat()
        })
        _save_tasks(data)

        if days_left < 0:
            return f"That date has passed. Update it with the correct exam date."
        elif days_left == 0:
            return f"{subject} exam is TODAY. Good luck — you've got this!"
        else:
            urgency = "Start revising now!" if days_left < 5 else "Plan your revision sessions."
            return f"{subject} exam in {days_left} days ({exam_date}). {urgency}"

    # ── List tasks ─────────────────────────────────────────────────────────────
    def _list_tasks(self) -> str:
        data   = _load_tasks()
        parts  = []
        today  = datetime.now().date()

        reminders = [r for r in data.get("reminders", []) if not r.get("done")]
        if reminders:
            parts.append(f"{len(reminders)} reminder(s):")
            for r in reminders[-5:]:  # Last 5
                t = f" at {r['time']}" if r.get("time") else ""
                parts.append(f"  #{r['id']}: {r['task']}{t}")

        exams = data.get("exams", [])
        if exams:
            for e in exams:
                try:
                    days = (datetime.strptime(e["date"], "%Y-%m-%d").date() - today).days
                    if days >= 0:
                        parts.append(f"  {e['subject']} exam in {days} day(s)")
                except Exception:
                    pass

        if not parts:
            return "No tasks saved. Say 'remind me to...' or 'my exam is on...' to add some."

        return ". ".join(parts)

    # ── Mark done ──────────────────────────────────────────────────────────────
    def _mark_done(self, command: str) -> str:
        match = re.search(r'\d+', command)
        if not match:
            return "Which task number? Say 'mark task 2 done'."
        task_id = int(match.group())
        data    = _load_tasks()
        for r in data["reminders"]:
            if r["id"] == task_id:
                r["done"] = True
                _save_tasks(data)
                return f"Task {task_id} marked as done."
        return f"Task {task_id} not found."

    # ── Smart parse fallback ───────────────────────────────────────────────────
    def _smart_parse(self, command: str) -> str:
        return ask_llm_with_system(
            "Help the user with their task or reminder request. Be specific and brief.",
            command, max_tokens=200
        )
