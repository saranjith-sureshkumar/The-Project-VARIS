"""
VARIS Email Agent — contacts system, validated addresses, AI drafts, you confirm.
Fix from V2: LLM no longer guesses email addresses — contacts.json used instead.

Setup:
  1. Add VARIS_EMAIL and VARIS_EMAIL_PASSWORD to .env
  2. Edit data/contacts.json to add your contacts
"""
import os, re, json, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr
from pathlib import Path
from brain.llm import ask_llm_with_system
from dotenv import load_dotenv
load_dotenv()

CONTACTS_FILE = Path("data/contacts.json")

# ── Contacts system ───────────────────────────────────────────────────────────
def _load_contacts() -> dict:
    """Load name → email map from data/contacts.json"""
    CONTACTS_FILE.parent.mkdir(exist_ok=True)
    if not CONTACTS_FILE.exists():
        # Create a starter template
        starter = {
            "_instructions": "Add your contacts here. Key = name (lowercase), value = email",
            "professor": "professor@example.com",
            "mom": "mom@example.com",
            "dad": "dad@example.com"
        }
        CONTACTS_FILE.write_text(json.dumps(starter, indent=2))
        print(f"[EMAIL] Created contacts template at {CONTACTS_FILE}")
    try:
        data = json.loads(CONTACTS_FILE.read_text())
        # Remove instruction key
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}

def _find_contact(name: str, contacts: dict) -> str | None:
    """Find email by name — fuzzy match."""
    if not name:
        return None
    name_low = name.lower().strip()
    # Exact match first
    if name_low in contacts:
        return contacts[name_low]
    # Partial match
    for key, email in contacts.items():
        if name_low in key or key in name_low:
            return email
    # Direct email given?
    if "@" in name and "." in name:
        return name
    return None


class EmailAgent:
    def __init__(self):
        self.email    = os.getenv("VARIS_EMAIL", "")
        self.password = os.getenv("VARIS_EMAIL_PASSWORD", "")

    def handle(self, command: str, speak) -> str:
        if not self.email or not self.password:
            return ("Email not configured. "
                    "Add VARIS_EMAIL and VARIS_EMAIL_PASSWORD to your .env file.")

        # Extract intent
        details = self._extract(command)
        recipient_name = details.get("to_name", "")
        recipient_email = details.get("to_email", "")

        # Resolve recipient from contacts
        contacts = _load_contacts()
        if not recipient_email or "@" not in recipient_email:
            recipient_email = _find_contact(recipient_name or recipient_email, contacts)

        if not recipient_email:
            # Ask user
            speak(f"I don't have an email address for '{recipient_name}'. "
                  "Please say or type their email address.")
            try:
                recipient_email = input("[VARIS] Email address: ").strip()
            except Exception:
                return "Email cancelled — no recipient address."

        if not self._validate(recipient_email):
            return f"'{recipient_email}' is not a valid email address. Email cancelled."

        # Generate email
        subject, body = self._generate(details)

        # Preview and confirm
        preview = (
            f"\n{'='*50}\n"
            f"TO:      {recipient_email}\n"
            f"SUBJECT: {subject}\n"
            f"\n{body}\n"
            f"{'='*50}\n"
        )
        print(preview)
        speak(f"Email to {recipient_email}. Subject: {subject}. Say yes to send, no to cancel.")

        from voice.listener import listen_for_yes_no
        confirmed = listen_for_yes_no(speak)

        if confirmed:
            return self._send(recipient_email, subject, body)
        return "Email cancelled. Nothing was sent."

    def _extract(self, command: str) -> dict:
        result = ask_llm_with_system(
            """Extract email details from command. Return ONLY valid JSON:
{"to_name": "recipient name or empty", "to_email": "email if mentioned or empty",
 "subject_hint": "topic", "tone": "formal or casual", "key_points": "what to say"}""",
            command, max_tokens=150
        )
        try:
            m = re.search(r'\{.*\}', result, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception:
            pass
        return {"to_name": "", "to_email": "", "subject_hint": command,
                "tone": "formal", "key_points": ""}

    def _generate(self, details: dict) -> tuple[str, str]:
        tone       = details.get("tone", "formal")
        topic      = details.get("subject_hint", "")
        key_points = details.get("key_points", "")

        content = ask_llm_with_system(
            f"""Write a {tone} email. Format exactly:
SUBJECT: [subject line]
BODY:
[email body with greeting and sign-off]

Keep it concise and professional. Sign off as VARIS (AI assistant).""",
            f"Topic: {topic}\nKey points: {key_points}",
            max_tokens=500
        )

        subject = "VARIS Email"
        body    = content
        lines   = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.upper().startswith("SUBJECT:"):
                subject = stripped[8:].strip()
            elif stripped.upper().startswith("BODY:"):
                body = '\n'.join(lines[i+1:]).strip()
                break

        return subject, body

    def _validate(self, addr: str) -> bool:
        if not addr or '\n' in addr or '\r' in addr:
            return False
        _, a = parseaddr(addr)
        if not a:
            return False
        return bool(re.match(
            r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', a
        ))

    def _send(self, to: str, subject: str, body: str) -> str:
        # Sanitize headers
        subject = subject.replace('\n', '').replace('\r', '')[:200]
        to      = to.replace('\n', '').replace('\r', '').strip()

        try:
            msg = MIMEMultipart()
            msg['From']    = self.email
            msg['To']      = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email, self.password)
                server.sendmail(self.email, to, msg.as_string())

            print(f"[EMAIL] Sent to {to}")
            return f"Email sent successfully to {to}."

        except smtplib.SMTPAuthenticationError:
            return ("Gmail authentication failed. "
                    "Check your App Password in .env — not your regular Gmail password.")
        except smtplib.SMTPException as e:
            return f"Email failed to send: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
