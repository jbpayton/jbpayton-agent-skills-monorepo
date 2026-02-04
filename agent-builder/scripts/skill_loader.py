"""Discovers and loads skills from local filesystem paths."""

import re
from pathlib import Path
from typing import Optional


class Skill:
    """One loaded skill: parsed frontmatter + full body."""

    __slots__ = ("name", "description", "content", "path")

    def __init__(self, name: str, description: str, content: str, path: Path):
        self.name = name
        self.description = description
        self.content = content   # markdown body (everything after frontmatter)
        self.path = path


def parse_skill_md(text: str) -> dict:
    """Split a SKILL.md into a flat frontmatter dict and the body string."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not match:
        return {"frontmatter": {}, "body": text.strip()}

    frontmatter: dict = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        # only top-level key: value lines (skip comments, list items, nested blocks)
        if ":" in stripped and not stripped.startswith(("#", "-", " ")):
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and val:
                frontmatter[key] = val

    return {"frontmatter": frontmatter, "body": match.group(2).strip()}


class SkillLoader:
    """Scans configured directories for SKILL.md files, caches results."""

    def __init__(self, paths: list):
        self.paths = [Path(p).expanduser().resolve() for p in paths]
        self._cache: dict = {}   # name -> Skill

    # ── discovery ─────────────────────────────────────────────

    def discover(self) -> list:
        """(Re-)scan all paths and return every skill found."""
        self._cache.clear()
        for base in self.paths:
            if not base.is_dir():
                continue
            for entry in base.iterdir():
                self._try_load(entry)
                # one level deeper for monorepo layouts
                if entry.is_dir():
                    for nested in entry.iterdir():
                        self._try_load(nested)
        return list(self._cache.values())

    def _try_load(self, path: Path):
        skill_md = path / "SKILL.md"
        if not skill_md.is_file():
            return
        try:
            text = skill_md.read_text(encoding="utf-8")
            parsed = parse_skill_md(text)
            name = parsed["frontmatter"].get("name", path.name)
            if name not in self._cache:
                self._cache[name] = Skill(
                    name=name,
                    description=parsed["frontmatter"].get("description", ""),
                    content=parsed["body"],
                    path=path,
                )
        except OSError:
            pass   # unreadable — skip silently

    # ── accessors ─────────────────────────────────────────────

    def get(self, name: str) -> Optional[Skill]:
        """Retrieve one skill by name.  Triggers discovery if cache is empty."""
        if not self._cache:
            self.discover()
        return self._cache.get(name)

    def list_names(self) -> list:
        """Sorted list of every known skill name."""
        if not self._cache:
            self.discover()
        return sorted(self._cache.keys())

    # ── context helpers ───────────────────────────────────────

    def descriptions(self) -> str:
        """Compact name+description block for the LLM system prompt.

        Full skill bodies are intentionally excluded here — they are loaded
        on demand when the agent emits [SKILL LOAD <name>].
        """
        if not self._cache:
            self.discover()
        if not self._cache:
            return ""

        lines = ["## Available Skills", ""]
        for name in sorted(self._cache):
            lines.append(f"- **{name}** — {self._cache[name].description}")
        lines.append("")
        lines.append("Use [SKILL LOAD <name>] to read a skill's full instructions.")
        return "\n".join(lines)
