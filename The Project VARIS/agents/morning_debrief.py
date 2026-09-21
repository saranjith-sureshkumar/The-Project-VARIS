"""
VARIS Morning Debrief — once per day, fully personalised.
Improvement from V2: now includes tasks, exam countdowns, memory context.
"""
import psutil, platform
from datetime import date, datetime
from pathlib import Path
from brain.llm import ask_llm_with_system

def morning_debrief(speak):
    """Run morning brief once per day. Skips if already run today."""
    date_file = Path("data/debrief_date.txt")
    date_file.parent.mkdir(exist_ok=True)
    today = str(date.today())

    if date_file.exists() and date_file.read_text().strip() == today:
        return  # Already ran today

    now  = datetime.now()
    hour = now.hour
    if hour < 5 or hour >= 23:
        return  # Don't run in middle of night

    greet = (
        "Good morning" if 5 <= hour < 12 else
        "Good afternoon" if 12 <= hour < 17 else
        "Good evening"
    )

    # System stats
    cpu  = psutil.cpu_percent(interval=1)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    mem_free_gb  = round(mem.available / 1024**3, 1)
    disk_free_gb = round(disk.free / 1024**3, 1)

    # Battery
    battery_info = ""
    try:
        batt = psutil.sensors_battery()
        if batt:
            status = "charging" if batt.power_plugged else "on battery"
            battery_info = f"Battery:{batt.percent:.0f}%({status})"
    except Exception:
        pass

    # Tasks and exam countdowns
    tasks_info = ""
    try:
        import json
        tasks_file = Path("data/tasks.json")
        if tasks_file.exists():
            data = json.loads(tasks_file.read_text())
            pending = [r for r in data.get("reminders", []) if not r.get("done")]
            exams   = data.get("exams", [])
            parts   = []
            if pending:
                parts.append(f"{len(pending)} pending reminder(s)")
            for exam in exams:
                try:
                    days = (datetime.strptime(exam["date"], "%Y-%m-%d").date()
                            - date.today()).days
                    if 0 <= days <= 30:
                        parts.append(f"{exam['subject']} exam in {days} day(s)")
                except Exception:
                    pass
            if parts:
                tasks_info = "Tasks: " + ", ".join(parts)
    except Exception:
        pass

    # Build context for LLM
    context = (
        f"Greeting:{greet} "
        f"Day:{now.strftime('%A %B %d %Y')} "
        f"Time:{now.strftime('%I:%M %p')} "
        f"CPU:{cpu:.0f}% "
        f"RAM_free:{mem_free_gb}GB "
        f"Disk_free:{disk_free_gb}GB "
        f"{battery_info} "
        f"{tasks_info}"
    ).strip()

    try:
        brief = ask_llm_with_system(
            """Create a warm, personal morning briefing — spoken aloud, under 5 sentences.
Include: personalised greeting with day and time, system health (only flag if something is low),
any upcoming tasks or exam countdowns, one motivational or practical suggestion.
Sound like a knowledgeable friend, not a robot. Be warm and brief.""",
            context,
            max_tokens=250
        )
    except Exception:
        brief = (f"{greet}. It's {now.strftime('%A, %B %d')} at {now.strftime('%I:%M %p')}. "
                 f"{tasks_info or 'No tasks pending.'} VARIS is ready.")

    speak(brief)
    date_file.write_text(today)
