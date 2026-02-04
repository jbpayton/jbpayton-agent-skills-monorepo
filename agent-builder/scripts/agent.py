"""Core agent: orchestrates LLM, skills, code execution, and memory."""

import re
from pathlib import Path

from llm_client import LLMClient
from skill_loader import SkillLoader
from code_runner import CodeRunner
from memory import Memory


# ---------------------------------------------------------------------------
# System prompt template — injected once per turn; skill/memory sections are
# appended dynamically.
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an autonomous agent. Beyond normal conversation you can do three things
by embedding special syntax anywhere in your reply:

1  RUN CODE
   Wrap Python in a fenced block tagged `run`:

       ```run
       print("hello")
       ```

   The code executes in your workspace directory.  You can create, read, and
   modify files there.  Output (stdout/stderr) is captured and fed back to you.

2  MANAGE MEMORY
   Persist information across sessions:

       [MEMORY SET key=value]   — store a string
       [MEMORY GET key]         — retrieve it (result fed back)
       [MEMORY DEL key]         — forget it
       [MEMORY LIST]            — see all stored keys

   Values are single-line strings.  For structured data write a file in the
   workspace instead.

3  LOAD SKILLS
   Skills are reusable instruction sets.  A short summary of every available
   skill is listed below.  To read the full instructions for one:

       [SKILL LOAD <name>]

   The skill body will be injected as a follow-up message.

Be direct.  Use code blocks when computation or file I/O is needed.  Use
memory when something must survive across sessions.
"""


class Agent:
    """Single entry-point for a conversational turn."""

    MAX_ACTION_ROUNDS = 5   # cap the execute→feedback loop

    def __init__(
        self,
        llm: LLMClient,
        workspace: Path,
        skill_paths: list,
        max_short_term: int = 20,
        summary_threshold: int = 15,
    ):
        self.llm = llm
        self.workspace = workspace
        self.skills = SkillLoader(skill_paths)
        self.runner = CodeRunner(workspace)
        self.memory = Memory(workspace, max_short_term, summary_threshold)

    # ── system prompt ─────────────────────────────────────────

    def _system_prompt(self) -> str:
        parts = [_SYSTEM_PROMPT]

        skill_ctx = self.skills.descriptions()
        if skill_ctx:
            parts.append(skill_ctx)

        mem_keys = self.memory.keys()
        if mem_keys:
            parts.append(
                f"## Stored Memories\n"
                f"Keys: {mem_keys}\n"
                f"Use [MEMORY GET key] to read any of them.\n"
            )

        return "\n\n".join(parts)

    # ── action parsing ────────────────────────────────────────

    @staticmethod
    def _extract_run_blocks(text: str) -> list:
        """Pull every  ```run ... ```  block out of text."""
        return re.findall(r"```run\s*\n(.*?)```", text, re.DOTALL)

    # ── action execution ──────────────────────────────────────

    def _process(self, response: str) -> str:
        """Execute all actions embedded in an LLM response.

        Returns a combined feedback string.  Empty string means nothing was
        executed — the caller should stop the action loop.
        """
        out: list = []

        # --- MEMORY SET ---
        for m in re.finditer(r"\[MEMORY SET\s+(\S+?)=(.+?)\]", response):
            self.memory.set(m.group(1), m.group(2))
            out.append(f"[saved {m.group(1)}]")

        # --- MEMORY GET ---
        for m in re.finditer(r"\[MEMORY GET\s+(\S+)\]", response):
            val = self.memory.get(m.group(1))
            out.append(f"[{m.group(1)} = {val if val is not None else '(not set)'}]")

        # --- MEMORY DEL ---
        for m in re.finditer(r"\[MEMORY DEL\s+(\S+)\]", response):
            if self.memory.delete(m.group(1)):
                out.append(f"[deleted {m.group(1)}]")
            else:
                out.append(f"[{m.group(1)} not found]")

        # --- MEMORY LIST ---
        if "[MEMORY LIST]" in response:
            out.append(f"[memory keys: {self.memory.keys()}]")

        # --- SKILL LOAD ---
        for m in re.finditer(r"\[SKILL LOAD\s+(\S+)\]", response):
            skill = self.skills.get(m.group(1))
            if skill:
                out.append(f"--- Skill: {skill.name} ---\n{skill.content}\n--- end ---")
            else:
                out.append(
                    f"[skill '{m.group(1)}' not found. "
                    f"Available: {self.skills.list_names()}]"
                )

        # --- RUN blocks ---
        for code in self._extract_run_blocks(response):
            result = self.runner.run(code.strip())
            lines: list = []
            if result.stdout.strip():
                lines.append(result.stdout.strip())
            if result.stderr.strip():
                lines.append(f"STDERR: {result.stderr.strip()}")
            if result.returncode != 0:
                lines.append(f"[exit code {result.returncode}]")
            out.append("[code output]\n" + ("\n".join(lines) if lines else "(no output)"))

        return "\n\n".join(out)

    # ── public API ────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        """Process one user turn end-to-end.  Returns the final reply text."""

        # compress history if the window is getting long
        if self.memory.needs_summarization():
            summary = self.llm.chat(
                [{"role": "user", "content": self.memory.summarization_prompt()}],
                temperature=0.0,
            )
            self.memory.apply_summary(summary)

        self.memory.add_message("user", user_input)

        response = ""
        for _ in range(self.MAX_ACTION_ROUNDS):
            messages = [
                {"role": "system", "content": self._system_prompt()}
            ] + self.memory.get_messages()

            response = self.llm.chat(messages)
            self.memory.add_message("assistant", response)

            feedback = self._process(response)
            if not feedback:
                break                          # nothing to execute — done

            self.memory.add_message("user", feedback)

        return response
