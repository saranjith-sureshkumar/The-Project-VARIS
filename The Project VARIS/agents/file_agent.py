"""VARIS File Agent — path whitelist, undo, hidden files protected."""
import os, json, shutil
from pathlib import Path
from datetime import datetime
from brain.llm import ask_llm

SAFE_PATHS = {
    "downloads": Path.home()/"Downloads", "desktop": Path.home()/"Desktop",
    "documents": Path.home()/"Documents", "pictures": Path.home()/"Pictures",
    "music": Path.home()/"Music", "videos": Path.home()/"Videos",
}
BLOCKED = ["system32","windows","program files","programdata","appdata",
           "roaming","syswow64","drivers","boot","$recycle","varis","venv",".git"]
FILE_TYPES = {
    "Images":[".jpg",".jpeg",".png",".gif",".bmp",".svg",".webp",".ico"],
    "Videos":[".mp4",".avi",".mov",".mkv",".wmv",".flv",".webm"],
    "Audio":[".mp3",".wav",".flac",".aac",".ogg",".wma"],
    "Documents":[".pdf",".doc",".docx",".txt",".rtf",".odt"],
    "Spreadsheets":[".xls",".xlsx",".csv",".ods"],
    "Presentations":[".ppt",".pptx",".key",".odp"],
    "Code":[".py",".js",".ts",".html",".css",".java",".cpp",".c",
            ".json",".xml",".yaml",".yml",".sh",".bat",".go",".rs"],
    "Archives":[".zip",".rar",".tar",".gz",".7z",".bz2"],
    "Executables":[".exe",".msi",".dmg"],
}
PROTECTED_EXT = {".env",".gitignore",".gitattributes",".lock",".cfg",".ini",".toml",".config"}

class FileAgent:
    def handle(self, command, speak=None):
        if "undo" in command.lower():
            return self.undo_last()
        folder = self._safe_folder(command)
        if not folder:
            return "I can only organise: Downloads, Desktop, Documents, Pictures, Music, or Videos."
        if not folder.exists():
            return f"Folder not found: {folder.name}"
        files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")]
        if len(files) > 100 and speak:
            speak(f"Found {len(files)} files. Say yes to continue.")
            from voice.listener import listen
            c = listen()
            if not c or "yes" not in c.lower():
                return "Cancelled."
        return self._organise(folder)

    def _safe_folder(self, command):
        cl = command.lower()
        for b in BLOCKED:
            if b in cl: return None
        for name, path in SAFE_PATHS.items():
            if name in cl: return path
        hint = ask_llm(f"Which folder: downloads/desktop/documents/pictures/music/videos?\nCommand: {command}\nReturn ONLY folder name.", max_tokens=10).strip().lower()
        return SAFE_PATHS.get(hint)

    def _organise(self, folder):
        undo = {}; moved = skipped = errors = 0
        for f in folder.iterdir():
            if f.is_dir() or f.name.startswith(".") or f.suffix.lower() in PROTECTED_EXT: continue
            cat = next((c for c, exts in FILE_TYPES.items() if f.suffix.lower() in exts), "Others")
            dest_dir = folder/cat; dest_dir.mkdir(exist_ok=True)
            dest = dest_dir/f.name
            if dest.exists(): skipped += 1; continue
            try:
                shutil.move(str(f), str(dest))
                undo[str(dest)] = str(f); moved += 1
            except Exception: errors += 1
        if undo:
            p = Path("data/organisation_undo.json"); p.parent.mkdir(exist_ok=True)
            p.write_text(json.dumps({"timestamp":datetime.now().isoformat(),"folder":str(folder),"moves":undo},indent=2))
        return f"Organised {moved} files in {folder.name}. {skipped} skipped. Say 'undo organisation' to reverse."

    def undo_last(self):
        p = Path("data/organisation_undo.json")
        if not p.exists(): return "Nothing to undo."
        data = json.loads(p.read_text())
        restored = 0
        for dest, orig in data["moves"].items():
            try:
                if Path(dest).exists(): shutil.move(dest, orig); restored += 1
            except Exception: pass
        p.unlink(); return f"Restored {restored} files."
