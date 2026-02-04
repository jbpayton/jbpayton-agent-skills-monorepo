"""Two-tier memory: ephemeral conversation window + persistent key-value store.

Short-term
    A list of {role, content} message dicts that mirrors what gets sent to the
    LLM.  When the list reaches *summary_threshold* messages the agent can ask
    the LLM to summarise it; call apply_summary() with the result to compress
    history down to a summary + a short tail of recent messages.

Long-term
    A JSON-backed dict (workspace/_memory.json) that is written to disk on
    every mutation.  Survives process restarts.  Values are limited to
    JSON-serialisable scalars for simplicity; store structured data as files
    in the workspace instead.
"""

import json
from pathlib import Path
from typing import Any


class Memory:

    STORE_FILE = "_memory.json"

    def __init__(self, workspace: Path, max_short_term: int = 20, summary_threshold: int = 15):
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._store_path = workspace / self.STORE_FILE

        self.max_short_term = max_short_term
        self.summary_threshold = summary_threshold

        self.short_term: list = []        # [{role, content}, ...]
        self.long_term: dict = {}         # key -> value
        self._load()

    # ── short-term ────────────────────────────────────────────

    def add_message(self, role: str, content: str):
        self.short_term.append({"role": role, "content": content})

    def get_messages(self) -> list:
        return list(self.short_term)

    def needs_summarization(self) -> bool:
        """True once the window has grown large enough to warrant compression."""
        return len(self.short_term) >= self.summary_threshold

    def summarization_prompt(self) -> str:
        """Produce the prompt text to hand to the LLM for summarisation."""
        transcript = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in self.short_term
        )
        return (
            "Summarize the following conversation. Preserve every key decision, "
            "fact, file path, and pending action item. Be concise.\n\n"
            + transcript
        )

    def apply_summary(self, summary: str):
        """Compress history: one summary message + the most recent tail."""
        keep = max(0, self.max_short_term - self.summary_threshold)
        tail = self.short_term[-keep:] if keep > 0 else []
        self.short_term = [
            {"role": "system", "content": f"[Previous conversation summary]\n{summary}"}
        ] + tail

    def clear(self):
        """Discard all short-term messages."""
        self.short_term.clear()

    # ── long-term ─────────────────────────────────────────────

    def set(self, key: str, value: Any):
        self.long_term[key] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.long_term.get(key, default)

    def delete(self, key: str) -> bool:
        if key in self.long_term:
            del self.long_term[key]
            self._save()
            return True
        return False

    def keys(self) -> list:
        return list(self.long_term.keys())

    # ── persistence ───────────────────────────────────────────

    def _load(self):
        if self._store_path.is_file():
            try:
                self.long_term = json.loads(
                    self._store_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                self.long_term = {}

    def _save(self):
        self._store_path.write_text(
            json.dumps(self.long_term, indent=2, default=str),
            encoding="utf-8",
        )
