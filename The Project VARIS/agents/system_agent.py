"""
VARIS System Agent — "Explain My Computer" narrator + volume/brightness control.
This is the single feature most likely to go viral.

Voice commands:
  "What is my computer doing right now?"
  "Explain my system"
  "Volume up / down / set to 50 percent"
  "Mute / unmute"
  "Brightness up / down / set to 70 percent"
  "How much RAM do I have left?"
  "Is my laptop running hot?"
"""
import re, sys, psutil
from brain.llm import ask_llm_with_system

class SystemAgent:
    def handle(self, command: str) -> str:
        cmd = command.lower()

        # Volume control
        if any(w in cmd for w in ["volume", "mute", "unmute", "louder", "quieter", "sound"]):
            return self._handle_volume(command)

        # Brightness control
        if any(w in cmd for w in ["brightness", "bright", "dim", "screen brightness"]):
            return self._handle_brightness(command)

        # System narration (default)
        return self._narrate()

    # ── System narration — "Explain My Computer" ─────────────────────────────
    def _collect(self) -> dict:
        cpu  = psutil.cpu_percent(interval=1)
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net  = psutil.net_io_counters()
        temp = self._get_temperature()

        # Top 5 processes by CPU
        procs = []
        for p in sorted(
            psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
            key=lambda x: x.info['cpu_percent'] or 0,
            reverse=True
        )[:5]:
            try:
                name = p.info['name'] or "unknown"
                cpu_p = p.info['cpu_percent'] or 0
                mem_p = p.info['memory_percent'] or 0
                procs.append(f"{name}({cpu_p:.0f}%CPU,{mem_p:.1f}%RAM)")
            except Exception:
                pass

        # Battery
        battery = ""
        try:
            batt = psutil.sensors_battery()
            if batt:
                status = "charging" if batt.power_plugged else "on battery"
                battery = f"Battery:{batt.percent:.0f}%({status})"
        except Exception:
            pass

        return {
            "cpu":        cpu,
            "mem_pct":    mem.percent,
            "mem_used":   round(mem.used  / 1024**3, 1),
            "mem_total":  round(mem.total / 1024**3, 1),
            "mem_free":   round(mem.available / 1024**3, 1),
            "disk_used":  round(disk.used  / 1024**3, 1),
            "disk_total": round(disk.total / 1024**3, 1),
            "disk_free":  round(disk.free  / 1024**3, 1),
            "net_sent":   round(net.bytes_sent / 1024**2, 1),
            "net_recv":   round(net.bytes_recv / 1024**2, 1),
            "procs":      ", ".join(procs),
            "temp":       temp,
            "battery":    battery,
        }

    def _get_temperature(self) -> str:
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return ""
            for key in ["coretemp", "k10temp", "acpitz", "cpu_thermal"]:
                if key in temps:
                    t = temps[key][0].current
                    status = "hot" if t > 85 else "warm" if t > 70 else "normal"
                    return f"CPU temp:{t:.0f}°C({status})"
            # Take first available
            for readings in temps.values():
                if readings:
                    t = readings[0].current
                    return f"Temp:{t:.0f}°C"
        except Exception:
            pass
        return ""

    def _narrate(self) -> str:
        d = self._collect()
        summary = (
            f"CPU:{d['cpu']}% "
            f"RAM:{d['mem_used']}/{d['mem_total']}GB({d['mem_pct']}%,{d['mem_free']}GB free) "
            f"Disk:{d['disk_used']}/{d['disk_total']}GB({d['disk_free']}GB free) "
            f"Network:↑{d['net_sent']}MB ↓{d['net_recv']}MB "
            f"TopProcesses:{d['procs']} "
            f"{d['temp']} {d['battery']}"
        ).strip()

        return ask_llm_with_system(
            """Convert this system data into a clear, spoken 3-sentence report.
Use plain English — no jargon. Narrate like a news reporter.
Flag anything above 85% CPU or RAM as a concern.
Mention if the laptop is hot or battery is low.
End with one practical suggestion if performance is poor.""",
            summary,
            max_tokens=200
        )

    # ── Volume control ────────────────────────────────────────────────────────
    def _handle_volume(self, command: str) -> str:
        cmd = command.lower()

        # Extract percentage if given
        match = re.search(r'(\d+)\s*(%|percent)', cmd)
        level = int(match.group(1)) if match else None

        if "mute" in cmd and "unmute" not in cmd:
            return self._set_volume_action("mute")
        if "unmute" in cmd:
            return self._set_volume_action("unmute")
        if "up" in cmd or "louder" in cmd or "increase" in cmd or "raise" in cmd:
            return self._set_volume_action("up", level or 10)
        if "down" in cmd or "quieter" in cmd or "lower" in cmd or "decrease" in cmd:
            return self._set_volume_action("down", level or 10)
        if level is not None:
            return self._set_volume_action("set", level)

        return "Say 'volume up', 'volume down', 'mute', or 'set volume to 50 percent'."

    def _set_volume_action(self, action: str, amount: int = 10) -> str:
        if sys.platform == "win32":
            return self._volume_windows(action, amount)
        elif sys.platform == "darwin":
            return self._volume_mac(action, amount)
        else:
            return self._volume_linux(action, amount)

    def _volume_windows(self, action: str, amount: int) -> str:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            iface   = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume  = cast(iface, POINTER(IAudioEndpointVolume))
            current = round(volume.GetMasterVolumeLevelScalar() * 100)

            if action == "mute":
                volume.SetMute(1, None)
                return "Muted."
            elif action == "unmute":
                volume.SetMute(0, None)
                return "Unmuted."
            elif action == "up":
                new = min(100, current + amount)
            elif action == "down":
                new = max(0, current - amount)
            else:  # set
                new = max(0, min(100, amount))

            volume.SetMasterVolumeLevelScalar(new / 100, None)
            return f"Volume set to {new}%."

        except ImportError:
            # Fallback: PowerShell
            import subprocess
            if action == "mute":
                subprocess.run(
                    'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"',
                    shell=True)
                return "Muted."
            elif action == "up":
                for _ in range(amount // 2):
                    subprocess.run(
                        'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"',
                        shell=True)
                return f"Volume increased."
            elif action == "down":
                for _ in range(amount // 2):
                    subprocess.run(
                        'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"',
                        shell=True)
                return f"Volume decreased."
            return "Volume control requires pycaw: pip install pycaw comtypes"

    def _volume_mac(self, action: str, amount: int) -> str:
        import subprocess
        if action == "mute":
            subprocess.run(["osascript", "-e", "set volume output muted true"])
            return "Muted."
        elif action == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"])
            return "Unmuted."
        elif action in ("up", "down", "set"):
            if action == "set":
                level = max(0, min(100, amount)) // 10
            else:
                # Get current
                result = subprocess.run(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    capture_output=True, text=True)
                current = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 50
                level   = max(0, min(100, current + (amount if action == "up" else -amount))) // 10
            subprocess.run(["osascript", "-e", f"set volume output volume {level * 10}"])
            return f"Volume set to {level * 10}%."
        return "Volume control failed."

    def _volume_linux(self, action: str, amount: int) -> str:
        import subprocess
        try:
            if action == "mute":
                subprocess.run(["amixer", "set", "Master", "mute"], capture_output=True)
                return "Muted."
            elif action == "unmute":
                subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True)
                return "Unmuted."
            elif action == "up":
                subprocess.run(["amixer", "set", "Master", f"{amount}%+"], capture_output=True)
                return f"Volume up {amount}%."
            elif action == "down":
                subprocess.run(["amixer", "set", "Master", f"{amount}%-"], capture_output=True)
                return f"Volume down {amount}%."
            elif action == "set":
                subprocess.run(["amixer", "set", "Master", f"{amount}%"], capture_output=True)
                return f"Volume set to {amount}%."
        except FileNotFoundError:
            return "Volume control requires 'amixer' (alsa-utils)."
        return "Volume control failed."

    # ── Brightness control ────────────────────────────────────────────────────
    def _handle_brightness(self, command: str) -> str:
        cmd   = command.lower()
        match = re.search(r'(\d+)\s*(%|percent)', cmd)
        level = int(match.group(1)) if match else None

        if "up" in cmd or "increase" in cmd or "brighter" in cmd:
            return self._set_brightness("up", level or 10)
        if "down" in cmd or "decrease" in cmd or "dimmer" in cmd or "dim" in cmd:
            return self._set_brightness("down", level or 10)
        if level is not None:
            return self._set_brightness("set", level)

        return "Say 'brightness up', 'brightness down', or 'set brightness to 70 percent'."

    def _set_brightness(self, action: str, amount: int) -> str:
        if sys.platform == "win32":
            try:
                import wmi
                c      = wmi.WMI(namespace='wmi')
                method = c.WmiMonitorBrightnessMethods()[0]
                current = c.WmiMonitorBrightness()[0].CurrentBrightness
                if action == "up":
                    new = min(100, current + amount)
                elif action == "down":
                    new = max(0, current - amount)
                else:
                    new = max(0, min(100, amount))
                method.WmiSetBrightness(new, 0)
                return f"Brightness set to {new}%."
            except ImportError:
                return "Brightness control requires: pip install wmi"
            except Exception as e:
                return f"Brightness control failed: {e}"

        elif sys.platform == "darwin":
            import subprocess
            val = amount / 100
            if action != "set":
                val = 0.5  # Default
            subprocess.run(["osascript", "-e",
                f'tell application "System Events" to set brightness of first desktop to {val}'])
            return f"Brightness adjusted."

        else:
            try:
                import subprocess
                result = subprocess.run(
                    ["brightnessctl", "get"], capture_output=True, text=True)
                current = int(result.stdout.strip()) if result.returncode == 0 else 50
                if action == "up":
                    subprocess.run(["brightnessctl", "set", f"{amount}%+"])
                elif action == "down":
                    subprocess.run(["brightnessctl", "set", f"{amount}%-"])
                else:
                    subprocess.run(["brightnessctl", "set", f"{amount}%"])
                return f"Brightness adjusted."
            except FileNotFoundError:
                return "Brightness control requires: sudo apt install brightnessctl"
