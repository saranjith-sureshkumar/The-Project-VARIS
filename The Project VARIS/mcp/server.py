"""
VARIS MCP Hub — all agents registered as plug-and-play MCP tools.
Improvements over V2:
  - Lazy imports (one failing agent won't crash the hub)
  - New tools: error agent, task agent, app agent, intent compiler
  - Tool metadata includes input/output format
  - Black box records every tool call
"""
import traceback
from memory.black_box import BlackBox

_black_box = BlackBox()

# ── Lazy agent loaders ────────────────────────────────────────────────────────
def _file():
    from agents.file_agent import FileAgent
    return FileAgent()

def _system():
    from agents.system_agent import SystemAgent
    return SystemAgent()

def _browser():
    from agents.browser_agent import BrowserAgent
    return BrowserAgent()

def _security():
    from agents.security_agent import SecurityAgent
    return SecurityAgent()

def _memory():
    from memory.graph import VarisMemory
    return VarisMemory()

def _error():
    from agents.error_agent import ErrorAgent
    return ErrorAgent()

def _task():
    from agents.task_agent import TaskAgent
    return TaskAgent()

def _app():
    from agents.app_agent import AppAgent
    return AppAgent()

def _intent():
    from brain.intent_compiler import IntentCompiler
    return IntentCompiler()

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = {
    "organise_files": {
        "description": "Organise files in a folder by type",
        "input":       "folder path or voice command",
        "output":      "summary of what was moved",
        "handler":     lambda c, _: _file().handle(c, lambda x: None),
    },
    "system_report": {
        "description": "Plain-English report of CPU, RAM, disk, processes",
        "input":       "any system query",
        "output":      "spoken system narration",
        "handler":     lambda c, _: _system().handle(c),
    },
    "open_browser": {
        "description": "Open a website or search query in browser",
        "input":       "site name or search term",
        "output":      "confirmation",
        "handler":     lambda c, _: _browser().handle(c),
    },
    "security_scan": {
        "description": "Run a full system security scan",
        "input":       "any text (ignored)",
        "output":      "security report",
        "handler":     lambda _, __: _security().full_scan(),
    },
    "recall_memory": {
        "description": "Search VARIS memory for past interactions",
        "input":       "search query",
        "output":      "matching memory entries",
        "handler":     lambda q, _: _memory().recall(q),
    },
    "audit_log": {
        "description": "Replay last N entries from the Black Box audit log",
        "input":       "number of entries (default 10)",
        "output":      "JSON list of audit entries",
        "handler":     lambda n, _: str(_black_box.replay(int(n) if str(n).isdigit() else 10)),
    },
    "explain_error": {
        "description": "Translate a stack trace or error into plain English",
        "input":       "error text or stack trace",
        "output":      "plain-English explanation and fix",
        "handler":     lambda c, _: _error().handle(c),
    },
    "set_task": {
        "description": "Set a reminder, timer, or exam countdown",
        "input":       "task description with time/date",
        "output":      "confirmation",
        "handler":     lambda c, speak: _task().handle(c, speak),
    },
    "open_app": {
        "description": "Launch an application by name",
        "input":       "application name",
        "output":      "confirmation",
        "handler":     lambda c, _: _app().handle(c),
    },
    "execute_goal": {
        "description": "Break a complex goal into steps and execute them",
        "input":       "goal description",
        "output":      "execution summary",
        "handler":     lambda c, speak: _intent().execute(c, speak),
    },
}

# ── Tool runner ───────────────────────────────────────────────────────────────
def call_tool(name: str, text: str, speak=None) -> str:
    """Call a registered tool by name. Logs to black box."""
    if name not in TOOLS:
        return f"Unknown tool: '{name}'. Use list_tools() to see available tools."

    tool = TOOLS[name]
    try:
        result = tool["handler"](text, speak)
        result = str(result) if result else "Done."
        _black_box.record("tool_call", text, result[:300], name)
        return result
    except Exception as e:
        error_msg = f"Tool '{name}' failed: {type(e).__name__}: {e}"
        print(f"[MCP] {error_msg}")
        _black_box.record("tool_error", text, error_msg, name,
                          traceback.format_exc()[:200])
        return error_msg

def list_tools() -> list:
    """Return all registered tools with metadata."""
    return [
        {
            "name":        name,
            "description": tool["description"],
            "input":       tool["input"],
            "output":      tool["output"],
        }
        for name, tool in TOOLS.items()
    ]

def tool_count() -> int:
    return len(TOOLS)
