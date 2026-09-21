"""
VARIS Recall Agent — visual screen memory.
Fix from V2: Tesseract path auto-detected on Windows, Linux, macOS.
Captures screen every N seconds, OCRs text, stores in memory for later recall.
"""
import sys, os, threading, time
from datetime import datetime
from pathlib import Path
from memory.graph import VarisMemory

# ── Tesseract path detection ──────────────────────────────────────────────────
def _setup_tesseract():
    """Auto-detect and configure Tesseract path."""
    try:
        import pytesseract
        # Windows: check common install paths
        if sys.platform == "win32":
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            for path in candidates:
                if Path(path).exists():
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"[RECALL] Tesseract found at: {path}")
                    return True
            # Try PATH
            import shutil
            if shutil.which("tesseract"):
                print("[RECALL] Tesseract found in PATH")
                return True
            print("[RECALL] Tesseract not found. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        else:
            # Linux/macOS — usually in PATH
            import shutil
            if shutil.which("tesseract"):
                return True
            print("[RECALL] Install tesseract: sudo apt install tesseract-ocr")
            return False
    except ImportError:
        return False

# Check dependencies
try:
    import mss
    import pytesseract
    from PIL import Image
    TESSERACT_OK = _setup_tesseract()
    AVAILABLE    = TESSERACT_OK
except ImportError as e:
    AVAILABLE = False
    print(f"[RECALL] Not available — missing: {e}")
    print("[RECALL] Install: pip install mss pytesseract pillow")


class RecallAgent:
    def __init__(self):
        self.memory   = VarisMemory()
        self._running = False

    def handle(self, command: str) -> str:
        if not AVAILABLE:
            return ("Visual memory not available. "
                    "Install: pip install mss pytesseract pillow, then install Tesseract OCR.")

        results = self.memory.recall(command, n=5)
        if results:
            return f"Found in visual memory: {results[:300]}"
        return ("Not in visual memory yet. "
                "I'll capture it next time it appears on screen.")

    def start_capture(self, interval: int = 60):
        """Start background screen capture loop."""
        if not AVAILABLE:
            print("[RECALL] Capture skipped — dependencies missing")
            return
        self._running = True
        threading.Thread(
            target=self._capture_loop,
            args=(interval,),
            daemon=True
        ).start()
        print(f"[RECALL] Screen capture active (every {interval}s)")

    def stop_capture(self):
        self._running = False

    def _capture_loop(self, interval: int):
        while self._running:
            try:
                self._capture_once()
            except Exception as e:
                print(f"[RECALL] Capture error: {e}")
            time.sleep(interval)

    def _capture_once(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            shot    = sct.grab(monitor)
            img     = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

        # Resize for faster OCR — 50% of original
        w, h = img.size
        img  = img.resize((w // 2, h // 2), Image.LANCZOS)

        # OCR
        text = pytesseract.image_to_string(img, lang="eng").strip()
        text = " ".join(text.split())  # Collapse whitespace

        # Only store if meaningful content found
        if len(text) > 80:
            entry = f"[SCREEN {datetime.now().strftime('%Y-%m-%d %H:%M')}] {text[:600]}"
            self.memory.save_interaction(entry, "screen")
