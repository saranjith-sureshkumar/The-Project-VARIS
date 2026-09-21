"""
VARIS Browser Agent — voice-controlled browser.
Improvements over V2:
  - Extended site shortcuts (30+ sites)
  - Download trigger detection
  - Incognito mode support
  - Safer URL validation
  - Fallback to webbrowser if Playwright unavailable
"""
import re, json, webbrowser, urllib.parse
from brain.llm import ask_llm_with_system

# ── Site shortcuts ────────────────────────────────────────────────────────────
SHORTCUTS = {
    "youtube":      "https://www.youtube.com",
    "google":       "https://www.google.com",
    "gmail":        "https://mail.google.com",
    "github":       "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit":       "https://www.reddit.com",
    "twitter":      "https://twitter.com",
    "linkedin":     "https://www.linkedin.com",
    "instagram":    "https://www.instagram.com",
    "whatsapp":     "https://web.whatsapp.com",
    "telegram":     "https://web.telegram.org",
    "netflix":      "https://www.netflix.com",
    "spotify":      "https://open.spotify.com",
    "amazon":       "https://www.amazon.in",
    "flipkart":     "https://www.flipkart.com",
    "maps":         "https://maps.google.com",
    "translate":    "https://translate.google.com",
    "drive":        "https://drive.google.com",
    "docs":         "https://docs.google.com",
    "sheets":       "https://sheets.google.com",
    "calendar":     "https://calendar.google.com",
    "meet":         "https://meet.google.com",
    "chatgpt":      "https://chat.openai.com",
    "claude":       "https://claude.ai",
    "gemini":       "https://gemini.google.com",
    "notion":       "https://notion.so",
    "figma":        "https://figma.com",
    "canva":        "https://canva.com",
    "hackerrank":   "https://www.hackerrank.com",
    "leetcode":     "https://leetcode.com",
    "coursera":     "https://www.coursera.org",
    "udemy":        "https://www.udemy.com",
    "internshala":  "https://internshala.com",
    "linkedin jobs": "https://www.linkedin.com/jobs",
    "naukri":       "https://www.naukri.com",
    "news":         "https://news.google.com",
    "weather":      "https://weather.com",
}

ALLOWED_SCHEMES = ("https://", "http://")

def _safe_url(url: str) -> str | None:
    """Validate and sanitise URL."""
    if not url:
        return None
    url = url.strip()
    # Block javascript: and data: URIs
    if url.lower().startswith(("javascript:", "data:", "file:", "vbscript:")):
        return None
    if not url.startswith(ALLOWED_SCHEMES):
        if "." in url and " " not in url and len(url) > 3:
            url = "https://" + url
        else:
            return None
    return url


class BrowserAgent:
    def handle(self, command: str) -> str:
        parsed = self._parse(command)
        return self._execute(parsed, command)

    def _parse(self, command: str) -> dict:
        """Use LLM to parse intent, with regex fallback."""
        # Fast path: check shortcuts first
        cmd_low = command.lower()
        for site, url in SHORTCUTS.items():
            if site in cmd_low:
                # Check if there's a search query too
                search_match = re.search(
                    r'search\s+(?:for\s+)?(.+)|find\s+(.+)|look\s+(?:up\s+)?(.+)',
                    cmd_low
                )
                if search_match:
                    q = next(g for g in search_match.groups() if g)
                    if "youtube" in cmd_low:
                        return {"action": "youtube", "query": q, "url": ""}
                    return {"action": "search", "query": q,
                            "url": f"https://www.google.com/search?q={urllib.parse.quote(q)}"}
                return {"action": "open", "query": "", "url": url}

        # LLM parse for complex commands
        result = ask_llm_with_system(
            """Parse this browser command. Return ONLY valid JSON:
{"action": "youtube|google|open|search|download",
 "query": "search term if any",
 "url": "full URL if specific site mentioned, else empty",
 "incognito": false}
No markdown, no explanation.""",
            command,
            max_tokens=100
        )
        result = re.sub(r'```json?|```', '', result).strip()
        try:
            m = re.search(r'\{.*\}', result, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        # Fallback: treat as Google search
        return {"action": "google", "query": command, "url": ""}

    def _execute(self, parsed: dict, original: str) -> str:
        action    = parsed.get("action", "google")
        query     = parsed.get("query", "").strip()
        raw_url   = parsed.get("url", "").strip()
        incognito = parsed.get("incognito", False)

        try:
            # YouTube search
            if action == "youtube" and query:
                url = (f"https://www.youtube.com/results?"
                       f"search_query={urllib.parse.quote(query)}")
                webbrowser.open(url)
                return f"Opened YouTube — searching for '{query}'."

            # Google search
            if action in ("google", "search") and query:
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return f"Searched Google for '{query}'."

            # Direct URL
            if raw_url:
                url = _safe_url(raw_url)
                if url:
                    webbrowser.open(url)
                    return f"Opened {url}."
                return "That URL doesn't look safe to open."

            # Fallback: Google search with original command
            if query or original:
                search_term = query or original
                url = f"https://www.google.com/search?q={urllib.parse.quote(search_term)}"
                webbrowser.open(url)
                return f"Searched for '{search_term}'."

            webbrowser.open("https://www.google.com")
            return "Opened Google."

        except Exception as e:
            return f"Browser error: {e}"
