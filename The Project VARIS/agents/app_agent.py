"""
VARIS App Agent — launch, close, switch applications by voice.
Works cross-platform: Windows, Linux, macOS.

Voice commands:
  "Open Spotify"
  "Launch VS Code"
  "Open calculator"
  "Close Notepad"
  "Switch to Chrome"
"""
import os, re, subprocess, sys
from brain.llm import ask_llm_with_system

# ── Common app name → executable map ─────────────────────────────────────────
_WINDOWS_APPS = {
    "notepad":      "notepad.exe",
    "calculator":   "calc.exe",
    "paint":        "mspaint.exe",
    "word":         "winword.exe",
    "excel":        "excel.exe",
    "powerpoint":   "powerpnt.exe",
    "chrome":       "chrome.exe",
    "firefox":      "firefox.exe",
    "edge":         "msedge.exe",
    "vscode":       "code.exe",
    "vs code":      "code.exe",
    "visual studio code": "code.exe",
    "spotify":      "Spotify.exe",
    "discord":      "Discord.exe",
    "zoom":         "Zoom.exe",
    "teams":        "Teams.exe",
    "telegram":     "Telegram.exe",
    "whatsapp":     "WhatsApp.exe",
    "vlc":          "vlc.exe",
    "explorer":     "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "cmd":          "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell":   "powershell.exe",
    "terminal":     "wt.exe",
    "windows terminal": "wt.exe",
    "snipping tool": "SnippingTool.exe",
    "camera":       "microsoft.windows.camera:",
    "settings":     "ms-settings:",
    "control panel": "control.exe",
    "device manager": "devmgmt.msc",
    "clock":        "ms-clock:",
    "photos":       "ms-photos:",
    "maps":         "bingmaps:",
    "weather":      "bingweather:",
    "sticky notes": "Microsoft.MicrosoftStickyNotes:",
    "paint 3d":     "ms-paint:",
    "wordpad":      "wordpad.exe",
    "pycharm":      "pycharm64.exe",
    "jupyter":      "jupyter notebook",
    "obsidian":     "Obsidian.exe",
    "notion":       "Notion.exe",
}

_LINUX_APPS = {
    "terminal":     "gnome-terminal",
    "calculator":   "gnome-calculator",
    "files":        "nautilus",
    "firefox":      "firefox",
    "chrome":       "google-chrome",
    "vscode":       "code",
    "vs code":      "code",
    "spotify":      "spotify",
    "discord":      "discord",
    "vlc":          "vlc",
    "gedit":        "gedit",
    "settings":     "gnome-control-center",
    "pycharm":      "pycharm",
    "jupyter":      "jupyter notebook",
}

_MAC_APPS = {
    "finder":       "Finder",
    "safari":       "Safari",
    "chrome":       "Google Chrome",
    "vscode":       "Visual Studio Code",
    "vs code":      "Visual Studio Code",
    "spotify":      "Spotify",
    "discord":      "Discord",
    "terminal":     "Terminal",
    "calculator":   "Calculator",
    "notes":        "Notes",
    "calendar":     "Calendar",
    "mail":         "Mail",
    "maps":         "Maps",
    "photos":       "Photos",
    "vlc":          "VLC",
    "pycharm":      "PyCharm",
}

# ── Blocked apps (security) ───────────────────────────────────────────────────
_BLOCKED = {
    "regedit", "registry editor", "gpedit", "secpol",
    "format", "diskpart", "bcdedit"
}

class AppAgent:
    def __init__(self):
        self._platform = sys.platform  # "win32", "linux", "darwin"

    def handle(self, command: str) -> str:
        cmd = command.lower()

        # Determine action
        action = "open"
        if any(w in cmd for w in ["close", "quit", "exit", "kill", "terminate"]):
            action = "close"
        elif any(w in cmd for w in ["switch to", "bring up", "show", "focus"]):
            action = "switch"

        # Extract app name
        app_name = self._extract_app_name(command)
        if not app_name:
            return "Which app would you like to open? Try 'open VS Code' or 'launch Spotify'."

        # Security check
        if app_name.lower() in _BLOCKED:
            return f"Opening '{app_name}' is restricted for security reasons."

        if action == "open":
            return self._open_app(app_name)
        elif action == "close":
            return self._close_app(app_name)
        else:
            return self._open_app(app_name)  # Switch = focus = open

    def _extract_app_name(self, command: str) -> str:
        """Extract app name from voice command."""
        # Remove action words
        clean = re.sub(
            r'\b(open|launch|start|run|close|quit|exit|kill|switch to|'
            r'bring up|show me|focus on|please|can you|could you)\b',
            '', command, flags=re.IGNORECASE
        ).strip()

        # Check known apps first (avoid LLM call for common apps)
        app_map = self._get_app_map()
        for known_name in app_map:
            if known_name in clean.lower():
                return known_name

        # LLM fallback for unknown app names
        if len(clean) > 2:
            result = ask_llm_with_system(
                "Extract ONLY the application name from this command. "
                "Return just the app name, nothing else. "
                "Example: 'Open Spotify please' → 'Spotify'",
                command, max_tokens=15
            ).strip()
            return result if result else clean

        return clean

    def _get_app_map(self) -> dict:
        if self._platform == "win32":
            return _WINDOWS_APPS
        elif self._platform == "darwin":
            return _MAC_APPS
        else:
            return _LINUX_APPS

    def _open_app(self, app_name: str) -> str:
        app_map    = self._get_app_map()
        executable = app_map.get(app_name.lower())

        try:
            if self._platform == "win32":
                return self._open_windows(app_name, executable)
            elif self._platform == "darwin":
                return self._open_mac(app_name, executable)
            else:
                return self._open_linux(app_name, executable)
        except FileNotFoundError:
            return (f"'{app_name}' not found. Make sure it's installed. "
                    "If it has a different name on your PC, tell me its executable name.")
        except Exception as e:
            return f"Could not open '{app_name}': {e}"

    def _open_windows(self, app_name: str, executable: str | None) -> str:
        if executable:
            if ":" in executable:  # ms-settings: style URI
                os.startfile(executable)
            elif " " in executable:  # Multi-word command like "jupyter notebook"
                subprocess.Popen(executable, shell=True)
            else:
                subprocess.Popen(executable, shell=True)
        else:
            # Try direct execution by name
            subprocess.Popen(app_name, shell=True)
        return f"Opening {app_name}."

    def _open_mac(self, app_name: str, app_display: str | None) -> str:
        target = app_display or app_name
        subprocess.Popen(["open", "-a", target])
        return f"Opening {target}."

    def _open_linux(self, app_name: str, executable: str | None) -> str:
        target = executable or app_name
        if " " in target:
            subprocess.Popen(target, shell=True)
        else:
            subprocess.Popen([target])
        return f"Opening {app_name}."

    def _close_app(self, app_name: str) -> str:
        try:
            import psutil
            app_low = app_name.lower()
            killed  = 0
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    pname = (proc.info['name'] or "").lower()
                    if app_low in pname or pname.replace(".exe","") in app_low:
                        proc.terminate()
                        killed += 1
                except Exception:
                    pass
            if killed:
                return f"Closed {app_name}."
            return f"'{app_name}' doesn't appear to be running."
        except ImportError:
            return "Cannot close apps — psutil not installed."
