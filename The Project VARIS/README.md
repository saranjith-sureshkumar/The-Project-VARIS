# V.A.R.I.S — Virtual Agent for Reasoning, Intelligence & Sovereignty

> *Every AI company is racing to build smarter AI. Nobody is racing to build **loyal** AI.*

## 🎬 Demo Video
**[▶ Watch VARIS in action](https://your-demo-link-here)**

---

## What is VARIS?

VARIS lives **inside your operating system** — not a browser tab, not a chat window, not a cloud subscription. It is your laptop's loyal intelligence, voice-controlled, locally-run, and architecturally incapable of serving anyone except you.

**Google's AI serves Google. Microsoft's AI serves Microsoft. VARIS serves one person: you.**

It runs on your machine. Your memory never leaves your device. There is no company in the middle.

---

## Why VARIS beats cloud assistants

| Feature | Google Astra | ChatGPT Voice | Microsoft Copilot | **VARIS** |
|---------|:-----------:|:-------------:|:-----------------:|:---------:|
| Works offline | ❌ | ❌ | ❌ | ✅ |
| Controls your OS | ❌ | ❌ | Partial | ✅ |
| Organises your files | ❌ | ❌ | ❌ | ✅ |
| Sends your emails | ❌ | ❌ | ❌ | ✅ |
| Security monitoring | ❌ | ❌ | ❌ | ✅ |
| Your data stays local | ❌ | ❌ | ❌ | ✅ |
| Costs after setup | Subscription | Subscription | Subscription | **₹0** |
| Remembers you forever | Session only | Session only | Limited | **Always** |

---

## Voice Commands

| Say this | What happens |
|----------|-------------|
| "What is my computer doing right now?" | Spoken plain-English system report |
| "Organise my Downloads folder" | Files sorted by type with undo support |
| "Open YouTube and search Tamil lofi" | Browser opens, searches automatically |
| "Write an email to my professor about leave" | AI drafts, you confirm, VARIS sends |
| "Explain this error" | Reads clipboard stack trace, gives fix |
| "Set a 25 minute Pomodoro" | Focus timer with halfway alert |
| "My exam is on December 20th" | Countdown added, included in morning brief |
| "Open VS Code" | Launches application by voice |
| "Volume up" / "Brightness down" | OS-level control |
| "Speed up my laptop" | Identifies closeable apps, asks permission |
| "Run a security scan" | Full threat + startup + firewall check |
| "Get me ready for my 3pm meeting" | 60-second personalised brief |
| "What was I working on yesterday?" | Memory recall from ChromaDB |
| "Get me ready for tomorrow's exam" | Intent Compiler: multi-step plan + execution |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR MACHINE                              │
│                                                             │
│  Voice Input        Brain              Agents               │
│  ──────────────     ──────────         ──────────────────   │
│  Whisper (local) →  Router         →   File  │ System       │
│  Microphone         Intent Compiler    Browser│ Email        │
│                     ↑                  Error  │ Task         │
│                     Groq API (online)  App    │ Security     │
│                     Phi-3 (offline)    Guardian (24/7)       │
│                                                             │
│  Memory             Core               Output               │
│  ──────────         ──────────         ──────────────────   │
│  ChromaDB      ←   Permissions    →   edge-tts (neural)    │
│  Black Box          Alert Queue        SAPI (offline)       │
│  Session            MCP Hub                                  │
└─────────────────────────────────────────────────────────────┘
         ↕ Only task text (no personal data)
    ┌─────────────┐
    │  Groq API   │  ← Free tier: 14,400 requests/day
    │  (online)   │    llama-3.3-70B quality
    └─────────────┘
```

**Privacy architecture:**
- Your voice → transcribed locally by Whisper → never sent anywhere
- Your files, memory, screen → 100% local, never uploaded
- Only the text of your command → sent to Groq (if online)
- No account required. No data collection. No telemetry.

---

## Quick Start

```bash
# Windows
setup.bat

# Linux / macOS
chmod +x setup.sh && ./setup.sh
```

Then:
1. Open `.env` — add your free [Groq API key](https://console.groq.com) and Gmail App Password
2. Edit `data/contacts.json` — add your contacts
3. In a separate terminal: `ollama serve`
4. `python main.py`

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Primary LLM | Groq (llama-3.3-70B, free) | GPT-4 class, 0.5s response |
| Fallback LLM | Ollama + Phi-3 Mini | Works 100% offline |
| Voice input | OpenAI Whisper (local) | Never sends audio anywhere |
| Voice output | edge-tts Neural (Indian English) | Natural, warm voice |
| Memory | ChromaDB (local vector DB) | Semantic search across history |
| Audit log | Black Box (append-only, hashed) | Every decision accountable |
| Browser | Playwright + webbrowser | Voice-controlled browsing |
| Security | psutil + scikit-learn IsolationForest | ML anomaly detection |
| OS control | psutil, Win32 API, subprocess | Real OS-level access |
| Protocol | Anthropic MCP | Plug-and-play tool registry |
| Setup | Python 3.11, one-command install | Beginner-friendly |

---

## Project Structure

```
VARIS/
├── main.py                  # Entry point — fully wired
├── brain/
│   ├── llm.py               # Groq (fast) + Phi-3 (offline) hybrid
│   ├── router.py            # Intent classifier → 14 agent routes
│   └── intent_compiler.py   # Goal → multi-step execution
├── voice/
│   ├── listener.py          # Whisper (cached, local)
│   └── speaker.py           # Neural voice + offline fallback
├── agents/
│   ├── file_agent.py        # File organiser with undo
│   ├── system_agent.py      # System narrator + volume/brightness
│   ├── browser_agent.py     # 30+ site shortcuts
│   ├── email_agent.py       # AI draft + contacts + validation
│   ├── error_agent.py       # Stack trace translator + clipboard AI
│   ├── task_agent.py        # Reminders + Pomodoro + exam countdown
│   ├── app_agent.py         # Launch any app by voice
│   ├── security_agent.py    # Full scan: processes + network + startup
│   ├── guardian_agent.py    # 24/7 ML anomaly detection
│   ├── optimizer.py         # RAM cleanup with confirmation
│   ├── morning_debrief.py   # Daily personalised brief
│   ├── recall_agent.py      # Visual screen memory
│   └── prep_agent.py        # Meeting/exam/interview prep
├── memory/
│   ├── graph.py             # ChromaDB + JSON fallback
│   ├── black_box.py         # Tamper-evident audit log
│   └── session.py           # Crash recovery
├── core/
│   ├── system_detector.py   # Hardware → optimal model selection
│   ├── alert_queue.py       # Guardian → main thread alerts
│   └── permissions.py       # First-launch consent system
├── mcp/
│   └── server.py            # 10 MCP tools registered
└── data/
    └── contacts.json        # Your email contacts
```

---

## The Philosophy

Every technology company in history was built to capture your attention, your data, or your money.

VARIS is built on one different idea: **your AI should work for you the way a senior colleague would — with full context, complete loyalty, and no agenda of its own.**

Google's AI answers your question and serves you an ad. VARIS answers your question, organises your files, monitors your security, sends your emails, and asks nothing in return — because it runs on your machine, your memory stays local, and there is no company in the middle.

This is not just a different product. It is a different idea about what computing should be.

---

## Built by

An IT graduate from Tamil Nadu, India — on a consumer laptop, in 12 days, with no research lab, no team, and no funding.

**Proof that the most important invention doesn't need a research lab. It needs the right idea.**

---

*[LinkedIn](your-linkedin) · [GitHub](https://github.com/your-username/VARIS) · [Demo](your-demo-link)*
