"""
VARIS Error Agent — stack trace translator + clipboard AI.
Two features nobody else has at OS level:

1. Clipboard AI: copy any text from ANY app → say "explain this" →
   VARIS reads your clipboard and explains/translates/summarises it by voice.

2. Error translator: paste a Python/JS/Java stack trace → VARIS speaks
   plain-English explanation + the exact fix. No googling required.
"""
import re, subprocess, sys
from brain.llm import ask_llm_with_system

# ── Error type patterns ────────────────────────────────────────────────────────
_ERROR_PATTERNS = {
    "python": [
        r"Traceback \(most recent call last\)",
        r"(NameError|TypeError|ValueError|AttributeError|ImportError|"
        r"IndentationError|SyntaxError|KeyError|IndexError|ZeroDivision"
        r"Error|FileNotFoundError|PermissionError|RuntimeError|Exception):",
    ],
    "javascript": [
        r"(TypeError|ReferenceError|SyntaxError|RangeError):",
        r"at\s+\w+\s+\(.*\.js:\d+:\d+\)",
    ],
    "java": [
        r"Exception in thread",
        r"at\s+[\w.]+\([\w.]+\.java:\d+\)",
    ],
    "general": [
        r"error|exception|failed|fatal|crash|undefined|null",
    ],
}

_ERROR_SYSTEM = """You are VARIS, an expert debugger. The user has pasted an error or stack trace.
Your job:
1. State what went wrong in ONE plain sentence (no jargon).
2. State exactly which file and line caused it (if visible).
3. Give the specific fix in ONE sentence starting with "Fix:".
4. If relevant, give one line of corrected code.
Keep total response under 5 sentences. Be direct and specific."""

_CLIPBOARD_SYSTEM = """You are VARIS, a concise AI assistant. The user has copied text from their screen
and wants you to process it. Based on their request:
- If they want explanation: explain clearly in 3 sentences or less.
- If they want summary: summarise in 2-3 bullet points.
- If they want translation: translate it.
- If they want improvement: rewrite it better.
Be direct, helpful, and specific to the text provided."""

class ErrorAgent:

    def handle(self, command: str) -> str:
        cmd_low = command.lower()

        # Clipboard AI — reads clipboard and processes it
        clipboard_triggers = [
            "clipboard", "what i copied", "explain this",
            "summarise this", "summarize this", "translate this",
            "what does this mean", "fix this", "improve this",
            "what is this", "read clipboard"
        ]
        if any(t in cmd_low for t in clipboard_triggers):
            return self._handle_clipboard(command)

        # Direct error text in command
        if self._looks_like_error(command):
            return self._translate_error(command)

        # Try clipboard automatically if command mentions error
        error_triggers = ["error", "exception", "traceback", "crash", "bug", "not working", "failed"]
        if any(t in cmd_low for t in error_triggers):
            clipboard_text = self._read_clipboard()
            if clipboard_text and self._looks_like_error(clipboard_text):
                return self._translate_error(clipboard_text)
            return self._translate_error(command)

        return self._handle_clipboard(command)

    def _looks_like_error(self, text: str) -> bool:
        text_low = text.lower()
        for lang_patterns in _ERROR_PATTERNS.values():
            for pattern in lang_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False

    def _translate_error(self, error_text: str) -> str:
        # Truncate very long traces — keep first 1500 chars (most relevant part)
        if len(error_text) > 1500:
            error_text = error_text[:1500] + "\n... (truncated)"

        result = ask_llm_with_system(
            _ERROR_SYSTEM,
            f"Error to explain:\n{error_text}",
            max_tokens=300
        )
        return result or "Could not analyse that error. Paste the full traceback and try again."

    def _read_clipboard(self) -> str:
        """Read clipboard — Windows, Linux, macOS."""
        # Windows
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return str(data).strip()
        except ImportError:
            pass
        except Exception:
            pass

        # Linux (xclip or xsel)
        for cmd in [["xclip", "-selection", "clipboard", "-o"],
                    ["xsel",  "--clipboard", "--output"],
                    ["wl-paste"]]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        # macOS
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return ""

    def _handle_clipboard(self, command: str) -> str:
        text = self._read_clipboard()
        if not text:
            return ("Clipboard is empty. Copy some text first — "
                    "an error, a paragraph, anything — then ask me again.")
        if len(text) < 5:
            return "The clipboard doesn't have enough text to work with."

        # Truncate if too long
        display_len = len(text)
        if len(text) > 2000:
            text = text[:2000] + "\n... (truncated)"

        # If it looks like an error, always translate it
        if self._looks_like_error(text):
            return self._translate_error(text)

        # Otherwise follow the user's intent
        result = ask_llm_with_system(
            _CLIPBOARD_SYSTEM,
            f"User request: {command}\n\nClipboard content ({display_len} chars):\n{text}",
            max_tokens=400
        )
        return result or "Could not process the clipboard content."
