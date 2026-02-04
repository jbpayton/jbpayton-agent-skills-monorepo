"""Executes Python code snippets inside an isolated workspace directory."""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional


class RunResult:
    """Outcome of a single code execution."""

    __slots__ = ("stdout", "stderr", "returncode")

    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    @property
    def success(self) -> bool:
        return self.returncode == 0


class CodeRunner:
    """Runs Python inside a sandboxed workspace directory.

    * CWD is always set to *workspace*.
    * The env var AGENT_WORKSPACE is exposed so scripts can locate the dir
      programmatically.
    * Temp execution scripts are cleaned up automatically.
    """

    def __init__(self, workspace: Path, timeout: int = 30):
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    # ── core ──────────────────────────────────────────────────

    def run(self, code: str, timeout: Optional[int] = None) -> RunResult:
        """Execute an arbitrary code string.  Returns captured output."""
        timeout = timeout if timeout is not None else self.timeout
        script = self.workspace / "_exec.py"
        script.write_text(code, encoding="utf-8")
        try:
            return self._invoke(script, timeout)
        finally:
            script.unlink(missing_ok=True)

    def run_file(self, filename: str, timeout: Optional[int] = None) -> RunResult:
        """Execute a file that already exists inside the workspace.

        Rejects absolute paths and any path that resolves outside the
        workspace (path-traversal guard).
        """
        if Path(filename).is_absolute():
            return RunResult("", "Only relative filenames are allowed.", -1)

        target = (self.workspace / filename).resolve()
        try:
            target.relative_to(self.workspace.resolve())
        except ValueError:
            return RunResult("", f"Path escapes workspace: {filename}", -1)

        if not target.is_file():
            return RunResult("", f"File not found in workspace: {filename}", -1)

        timeout = timeout if timeout is not None else self.timeout
        return self._invoke(target, timeout)

    # ── shared subprocess logic ───────────────────────────────

    def _invoke(self, script: Path, timeout: int) -> RunResult:
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace),
                env={**os.environ, "AGENT_WORKSPACE": str(self.workspace)},
            )
            return RunResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            return RunResult("", f"Timed out after {timeout}s.", -1)
        except Exception as exc:
            return RunResult("", str(exc), -1)
