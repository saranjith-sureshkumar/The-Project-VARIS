"""
VARIS Listener — Whisper local, model cached at startup, auto-calibrated.
Fix from V2: model no longer reloads on every command (was causing 5-8s delay).
100% local — voice never leaves device.
"""
import os, threading
import speech_recognition as sr

_MODEL      = os.getenv("WHISPER_MODEL", "base")
recognizer  = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold          = 0.8
recognizer.energy_threshold         = 300

_calibrated     = False
_whisper_model  = None          # Cached model object
_model_lock     = threading.Lock()
_model_loading  = False

def _load_whisper_model():
    """Load Whisper model once and cache it — avoids 5-8s reload every command."""
    global _whisper_model, _model_loading
    with _model_lock:
        if _whisper_model is not None:
            return _whisper_model
        if _model_loading:
            return None
        _model_loading = True
    try:
        import whisper
        print(f"[LISTENER] Loading Whisper {_MODEL} model...")
        model = whisper.load_model(_MODEL)
        with _model_lock:
            _whisper_model = model
            _model_loading = False
        print(f"[LISTENER] Whisper {_MODEL} ready")
        return model
    except ImportError:
        print("[LISTENER] whisper not installed — run: pip install openai-whisper")
        with _model_lock:
            _model_loading = False
        return None
    except Exception as e:
        print(f"[LISTENER] Whisper load error: {e}")
        with _model_lock:
            _model_loading = False
        return None

def calibrate_microphone():
    """Calibrate ambient noise threshold. Call once at startup."""
    global _calibrated
    if _calibrated:
        return
    print("[LISTENER] Calibrating microphone...")
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"[LISTENER] Mic ready — threshold: {recognizer.energy_threshold:.0f}")
        _calibrated = True
    except OSError as e:
        print(f"[LISTENER] No microphone found: {e}")
        recognizer.energy_threshold = 400
        _calibrated = True
    except Exception as e:
        print(f"[LISTENER] Calibration failed: {e}")
        recognizer.energy_threshold = 400
        _calibrated = True

    # Pre-load Whisper in background so first command is instant
    threading.Thread(target=_load_whisper_model, daemon=True).start()

def listen(timeout: int = 10, phrase_limit: int = 30) -> str:
    """
    Listen for one voice command.
    Returns transcribed text string, or "" if nothing heard / error.
    """
    if not _calibrated:
        calibrate_microphone()

    # Capture audio
    try:
        with sr.Microphone() as source:
            print("[VARIS] Listening...", end=" ", flush=True)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
                print("got it")
            except sr.WaitTimeoutError:
                print("(timeout)")
                return ""
    except ImportError:
        print("\n[ERROR] PyAudio missing.")
        print("  Windows fix: pip install pipwin && pipwin install pyaudio")
        print("  Linux fix:   sudo apt install python3-pyaudio")
        return ""
    except OSError as e:
        print(f"\n[LISTENER] Mic error: {e}")
        return ""

    # Transcribe — use cached model if available
    model = _whisper_model  # Read without lock (safe — write-once after load)
    try:
        if model is not None:
            # Fast path: use cached model directly
            import numpy as np, io, wave, struct
            raw = audio.get_wav_data()
            with io.BytesIO(raw) as buf:
                with wave.open(buf) as wf:
                    frames = wf.readframes(wf.getnframes())
                    rate   = wf.getframerate()
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            result  = model.transcribe(samples, language="en", fp16=False)
            text    = result.get("text", "").strip()
        else:
            # Fallback: use SpeechRecognition's built-in Whisper wrapper
            text = recognizer.recognize_whisper(audio, model=_MODEL, language="english")

        if text:
            print(f"[HEARD]  {text}")
            return text.strip()
        return ""

    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"[LISTENER] Transcription error: {type(e).__name__}: {e}")
        return ""


def listen_for_yes_no(prompt_func=None, timeout: int = 8) -> bool:
    """
    Listen specifically for a yes/no confirmation.
    Falls back to keyboard input if voice fails.
    """
    if prompt_func:
        prompt_func("Say yes to confirm, or no to cancel.")

    response = listen(timeout=timeout, phrase_limit=5)

    if response:
        low = response.lower()
        if any(w in low for w in ["yes", "yeah", "yep", "sure", "confirm", "do it", "send it"]):
            return True
        if any(w in low for w in ["no", "nope", "cancel", "stop", "don't"]):
            return False

    # Keyboard fallback
    try:
        ans = input("[VARIS] Type yes/no: ").strip().lower()
        return ans in ("yes", "y")
    except Exception:
        return False
