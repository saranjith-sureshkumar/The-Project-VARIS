"""
VARIS System Detector — auto-detect hardware, pick optimal models.
Now called from main.py at startup and applied to env vars.
"""
import os, psutil

def detect() -> dict:
    """Detect hardware and return optimal model recommendations."""
    mem_gb     = psutil.virtual_memory().total / 1024**3
    cpu_cores  = psutil.cpu_count(logical=True)
    disk_free  = psutil.disk_usage("/").free / 1024**3

    # Whisper model selection
    if mem_gb < 6:
        whisper = "tiny"      # 39MB  — low-end
    elif mem_gb < 12:
        whisper = "base"      # 142MB — mid-range
    elif mem_gb < 20:
        whisper = "small"     # 461MB — good quality
    else:
        whisper = "medium"    # 1.5GB — high quality

    # Ollama model selection
    if mem_gb < 8:
        ollama = "phi3:mini"    # 2.3GB — minimum
    elif mem_gb < 20:
        ollama = "phi3"         # 2.3GB — standard (your device)
    else:
        ollama = "llama3.2"     # 2.0GB — better reasoning

    return {
        "ram_gb":       round(mem_gb, 1),
        "cpu_cores":    cpu_cores,
        "disk_free_gb": round(disk_free, 1),
        "whisper_model": whisper,
        "ollama_model":  ollama,
        "performance_tier": (
            "high"   if mem_gb >= 16 else
            "medium" if mem_gb >= 8  else
            "low"
        )
    }

def print_report() -> dict:
    """Print hardware report and return spec dict."""
    d = detect()
    print(f"[SYSTEM] RAM: {d['ram_gb']}GB | "
          f"CPU: {d['cpu_cores']} cores | "
          f"Disk free: {d['disk_free_gb']}GB")
    print(f"[SYSTEM] Tier: {d['performance_tier']} | "
          f"Whisper: {d['whisper_model']} | "
          f"Local LLM: {d['ollama_model']}")
    return d
