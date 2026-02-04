#!/usr/bin/env python3
"""agent-builder — interactive agent with LLM, skills, code execution, and memory.

Usage
-----
    python main.py                                          # config.json next to this file
    python main.py --config /path/to/config.json
    python main.py --url http://localhost:11434/v1 --model llama3
    python main.py --workspace ./my-workspace
    python main.py --key sk-...                             # or set OPENAI_API_KEY
"""

import argparse
import json
import sys
import os
from pathlib import Path

# make sibling modules importable regardless of CWD
sys.path.insert(0, str(Path(__file__).parent))

from llm_client import LLMClient   # noqa: E402
from agent import Agent            # noqa: E402


# ---------------------------------------------------------------------------
# config loading
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "llm":       {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "llama3"},
    "workspace": "./workspace",
    "skills":    {"paths": ["./skills/"]},
    "memory":    {"max_short_term": 20, "summary_threshold": 15},
}


def _load_config(path: Path) -> dict:
    """Merge user config on top of defaults.  Missing keys fall back silently."""
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULTS.items()}
    if path.is_file():
        try:
            user = json.loads(path.read_text(encoding="utf-8"))
            for key in cfg:
                if key in user:
                    if isinstance(cfg[key], dict) and isinstance(user[key], dict):
                        cfg[key] = {**cfg[key], **user[key]}
                    else:
                        cfg[key] = user[key]
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[warn] {path}: {exc}", file=sys.stderr)
    return cfg


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

_SLASH_HELP = """\
  /skills   list loaded skills
  /memory   dump long-term memory
  /clear    wipe short-term conversation history
  /help     this message
  quit      exit"""


def main():
    parser = argparse.ArgumentParser(
        description="Interactive agent with skills, code execution, and memory."
    )
    parser.add_argument("--config",    type=Path, default=Path(__file__).parent / "config.json")
    parser.add_argument("--url",       help="Override LLM base URL")
    parser.add_argument("--model",     help="Override model name")
    parser.add_argument("--workspace", help="Override workspace directory")
    parser.add_argument("--key",       help="Override API key  (or set OPENAI_API_KEY)")
    args = parser.parse_args()

    cfg = _load_config(args.config)

    # CLI flags override config
    if args.url:       cfg["llm"]["base_url"] = args.url
    if args.model:     cfg["llm"]["model"]    = args.model
    if args.workspace: cfg["workspace"]       = args.workspace

    # API-key resolution: CLI > env > config file
    api_key = args.key or cfg["llm"]["api_key"] or os.environ.get("OPENAI_API_KEY", "")

    workspace = Path(cfg["workspace"]).resolve()

    llm   = LLMClient(base_url=cfg["llm"]["base_url"], api_key=api_key, model=cfg["llm"]["model"])
    agent = Agent(
        llm=llm,
        workspace=workspace,
        skill_paths=cfg["skills"]["paths"],
        max_short_term=cfg["memory"]["max_short_term"],
        summary_threshold=cfg["memory"]["summary_threshold"],
    )

    # discover skills and print startup banner
    skills = agent.skills.discover()
    print("agent-builder ready")
    print(f"  model:     {cfg['llm']['model']}  ({cfg['llm']['base_url']})")
    print(f"  workspace: {workspace}")
    print(f"  skills:    {', '.join(s.name for s in skills) or '(none)'}")
    print(f"  memory:    {len(agent.memory.keys())} long-term key(s)")
    print(f"  type /help for local commands, or just start chatting.\n")

    # ── interactive loop ──────────────────────────────────────
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not line:
            continue

        if line.lower() in ("quit", "exit", "q"):
            print("bye.")
            break

        # slash commands handled locally (no LLM call)
        if line.startswith("/"):
            cmd = line.split()[0].lower()

            if cmd == "/help":
                print(_SLASH_HELP)
            elif cmd == "/skills":
                names = agent.skills.list_names()
                print(f"skills: {names or '(none)'}")
            elif cmd == "/memory":
                if not agent.memory.keys():
                    print("(empty)")
                else:
                    for k in agent.memory.keys():
                        print(f"  {k} = {agent.memory.get(k)}")
            elif cmd == "/clear":
                agent.memory.clear()
                print("short-term memory cleared.")
            else:
                print(f"unknown command: {cmd}  (try /help)")
            continue

        # ── send to agent ───────────────────────────────────
        try:
            reply = agent.chat(line)
            print(f"\n{reply}\n")
        except Exception as exc:
            print(f"\n[error] {exc}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
