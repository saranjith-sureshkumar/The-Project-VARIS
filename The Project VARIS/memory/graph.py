"""
VARIS Memory — ChromaDB vector search with JSON fallback.
Improvements over V2:
  - Timestamps returned with recall results
  - Separate collections: interactions, screen, facts
  - Fact extraction: saves named facts ("my exam is Dec 20")
  - Safe ID generation (no hash collisions)
  - Corruption recovery with backup
  - JSON fallback works without chromadb installed
"""
import os, json, uuid
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    CHROMA = True
except ImportError:
    CHROMA = False

MAX_ENTRIES = 10_000

class VarisMemory:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.json_path = Path("data/memory.json")

        if CHROMA:
            self._init_chroma()
        else:
            print("[MEMORY] ChromaDB not installed — using JSON memory")
            print("[MEMORY]   Install: pip install chromadb")
            self._load_json()

    # ── ChromaDB initialisation ───────────────────────────────────────────────
    def _init_chroma(self):
        try:
            self.client = chromadb.PersistentClient(path="data/chromadb")
            self.interactions = self.client.get_or_create_collection(
                "varis_interactions"
            )
            self.facts = self.client.get_or_create_collection(
                "varis_facts"
            )
            print(f"[MEMORY] ChromaDB active "
                  f"({self.interactions.count()} interactions stored)")
        except Exception as e:
            print(f"[MEMORY] ChromaDB error: {e} — rebuilding...")
            self._rebuild_chroma()

    def _rebuild_chroma(self):
        """Backup corrupted DB and rebuild fresh."""
        import shutil
        db_path = Path("data/chromadb")
        if db_path.exists():
            backup = f"data/chromadb_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(db_path), backup)
            print(f"[MEMORY] Corrupted DB backed up to {backup}")
        try:
            self.client       = chromadb.PersistentClient(path="data/chromadb")
            self.interactions = self.client.get_or_create_collection("varis_interactions")
            self.facts        = self.client.get_or_create_collection("varis_facts")
            print("[MEMORY] ChromaDB rebuilt successfully")
        except Exception as e:
            print(f"[MEMORY] Rebuild failed: {e} — switching to JSON")
            global CHROMA
            CHROMA = False
            self._load_json()

    # ── JSON fallback ─────────────────────────────────────────────────────────
    def _load_json(self):
        try:
            if self.json_path.exists():
                self.data = json.loads(self.json_path.read_text())
            else:
                self.data = {"interactions": [], "facts": []}
        except Exception:
            self.data = {"interactions": [], "facts": []}

    def _save_json(self):
        self.json_path.write_text(
            json.dumps(self.data, indent=2)
        )

    # ── Public API ────────────────────────────────────────────────────────────
    def save_interaction(self, text: str, role: str):
        """Save a voice command, response, or screen capture to memory."""
        if not text or not text.strip():
            return
        ts  = datetime.now().isoformat()
        uid = str(uuid.uuid4())

        if CHROMA:
            try:
                # Prune if at limit
                count = self.interactions.count()
                if count >= MAX_ENTRIES:
                    oldest = self.interactions.get(limit=500)["ids"]
                    if oldest:
                        self.interactions.delete(ids=oldest)

                self.interactions.add(
                    documents=[text],
                    metadatas=[{"role": role, "timestamp": ts}],
                    ids=[uid]
                )
            except Exception as e:
                print(f"[MEMORY] Save error: {e}")
        else:
            self.data["interactions"].append({
                "text":      text,
                "role":      role,
                "timestamp": ts
            })
            # Keep only last MAX_ENTRIES
            self.data["interactions"] = self.data["interactions"][-MAX_ENTRIES:]
            self._save_json()

    def save_fact(self, fact: str, category: str = "general"):
        """Save a named fact for precise recall (e.g. exam dates, preferences)."""
        ts  = datetime.now().isoformat()
        uid = str(uuid.uuid4())

        if CHROMA:
            try:
                self.facts.add(
                    documents=[fact],
                    metadatas=[{"category": category, "timestamp": ts}],
                    ids=[uid]
                )
            except Exception as e:
                print(f"[MEMORY] Fact save error: {e}")
        else:
            self.data.setdefault("facts", []).append({
                "fact":      fact,
                "category":  category,
                "timestamp": ts
            })
            self._save_json()

    def recall(self, query: str, n: int = 5) -> str:
        """Search memory for content related to query. Returns formatted string."""
        if not query or not query.strip():
            return ""

        if CHROMA:
            return self._recall_chroma(query, n)
        else:
            return self._recall_json(query, n)

    def _recall_chroma(self, query: str, n: int) -> str:
        results = []

        # Search interactions
        try:
            count = self.interactions.count()
            if count > 0:
                r    = self.interactions.query(
                    query_texts=[query],
                    n_results=min(n, count)
                )
                docs = r.get("documents", [[]])[0]
                metas = r.get("metadatas", [[]])[0]
                for doc, meta in zip(docs, metas):
                    ts   = meta.get("timestamp", "")[:16].replace("T", " ")
                    role = meta.get("role", "")
                    results.append(f"[{ts}] {doc[:150]}")
        except Exception:
            pass

        # Search facts
        try:
            fcount = self.facts.count()
            if fcount > 0:
                fr = self.facts.query(
                    query_texts=[query],
                    n_results=min(3, fcount)
                )
                fdocs = fr.get("documents", [[]])[0]
                for doc in fdocs:
                    results.append(f"[FACT] {doc}")
        except Exception:
            pass

        return " | ".join(results[:n]) if results else ""

    def _recall_json(self, query: str, n: int) -> str:
        query_low = query.lower()
        matches   = []

        for entry in self.data.get("interactions", []):
            text = entry.get("text", "")
            if query_low in text.lower():
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                matches.append(f"[{ts}] {text[:150]}")

        for fact in self.data.get("facts", []):
            text = fact.get("fact", "")
            if query_low in text.lower():
                matches.append(f"[FACT] {text}")

        return " | ".join(matches[-n:]) if matches else ""

    def count(self) -> int:
        """Return total number of stored interactions."""
        if CHROMA:
            try:
                return self.interactions.count()
            except Exception:
                return 0
        return len(self.data.get("interactions", []))

    def clear(self):
        """Clear all memory (use with caution)."""
        if CHROMA:
            try:
                self.client.delete_collection("varis_interactions")
                self.client.delete_collection("varis_facts")
                self._init_chroma()
            except Exception as e:
                print(f"[MEMORY] Clear error: {e}")
        else:
            self.data = {"interactions": [], "facts": []}
            self._save_json()
        print("[MEMORY] All memory cleared")
