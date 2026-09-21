"""
VARIS Prep Agent — meeting / interview / exam preparation brief.
Improvements over V2:
  - Detects prep type: meeting, interview, exam, presentation
  - Pulls relevant memory context per person/topic
  - Structures output differently for each type
  - Time-aware (morning vs afternoon prep)
"""
from datetime import datetime
from brain.llm import ask_llm, ask_llm_with_system

MEETING_SYSTEM = """Create a concise 60-second spoken meeting brief.
Structure: Who (1 sentence) → What was discussed before (1-2 sentences) →
Open items / promises made (1 sentence) → Your 2-3 talking points today.
Be specific. Sound like a sharp colleague briefing you in a hallway."""

INTERVIEW_SYSTEM = """Create a focused 90-second spoken interview prep brief.
Structure: Company/role summary (1 sentence) → Key things to emphasise (2 points) →
Likely questions to prepare for (2 questions) → One tip for this specific interview.
Be encouraging and practical."""

EXAM_SYSTEM = """Create a focused 60-second spoken exam prep brief.
Structure: Subject and scope (1 sentence) → Top 3 topics most likely to appear →
One study strategy for the time remaining → One confidence-building closing line.
Be warm and practical."""

PRESENTATION_SYSTEM = """Create a focused 60-second spoken presentation prep brief.
Structure: Topic and audience (1 sentence) → Key message to land (1 sentence) →
2 strongest points to emphasise → One tip for delivery.
Be encouraging and specific."""

class PrepAgent:
    def handle(self, command: str, memory) -> str:
        cmd_low  = command.lower()
        now      = datetime.now()
        time_str = now.strftime('%I:%M %p')

        # Detect prep type
        if any(w in cmd_low for w in ["interview", "job", "hiring"]):
            prep_type = "interview"
            system    = INTERVIEW_SYSTEM
        elif any(w in cmd_low for w in ["exam", "test", "paper", "revision"]):
            prep_type = "exam"
            system    = EXAM_SYSTEM
        elif any(w in cmd_low for w in ["presentation", "present", "demo", "pitch"]):
            prep_type = "presentation"
            system    = PRESENTATION_SYSTEM
        else:
            prep_type = "meeting"
            system    = MEETING_SYSTEM

        # Extract subject/person name
        subject = ask_llm(
            f"Extract the main topic, person name, or subject from: '{command}'. "
            f"Return ONLY the name/topic, nothing else.",
            max_tokens=20
        ).strip()

        # Pull memory context
        past_context = ""
        if memory and subject:
            try:
                recalled = memory.recall(subject, n=5)
                if recalled:
                    past_context = f"Past context about '{subject}': {recalled[:400]}"
            except Exception:
                pass

        # Build context
        context = (
            f"Prep type: {prep_type}\n"
            f"Topic/Person: {subject or 'unknown'}\n"
            f"Time: {time_str} on {now.strftime('%A %B %d')}\n"
            f"{past_context}"
        ).strip()

        return ask_llm_with_system(system, context, max_tokens=350)
