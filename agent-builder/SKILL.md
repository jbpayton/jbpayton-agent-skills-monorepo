---
name: agent-builder
description: "Zero-dependency scaffold for building autonomous agents: OpenAI-compatible LLM client, dynamic skill loading, Python code execution in an isolated workspace, and two-tier persistent memory. Use when you need to bootstrap a new agent or want a reusable agent template that works with any /v1 endpoint."
license: Unlicense
compatibility: "Python 3.9+"
metadata:
  author: joeyp
  version: "1.0"
---

# Agent Builder

A zero-dependency Python template for building autonomous agents.  Drop it
next to your skills, point it at any OpenAI-compatible endpoint, and it is
ready to go.

## When to Use

- You need a working agent loop that talks to an LLM and can act on its replies.
- You want the agent to discover and follow skills from the filesystem at runtime.
- You need the agent to write and execute Python code and keep files across turns.
- You want memory that survives session restarts without a database.

## Quick Start

```bash
# 1  point at your endpoint  (ollama, together.ai, openai …)
export OPENAI_API_KEY=sk-...          # only needed if your endpoint requires auth

# 2  put skills in ./skills/  (or change paths in config.json)

# 3  run
python agent-builder/scripts/main.py --url http://localhost:11434/v1 --model llama3
```

## Architecture

```
main.py            CLI entry-point, REPL, config loading
  └─ agent.py      Orchestrator: builds prompts, runs the action loop
       ├─ llm_client.py    HTTP POST → /chat/completions  (stdlib only)
       ├─ skill_loader.py  Scans paths for SKILL.md, parses frontmatter
       ├─ code_runner.py   subprocess → Python, CWD = workspace
       └─ memory.py        short-term window  +  long-term JSON store
```

All modules live in `scripts/`.  See [references/api.md](references/api.md)
for the per-module API.

## In-Agent Commands

The LLM can embed these anywhere in its reply; they are parsed and executed
automatically, and any output is fed back as a follow-up message.

### Code execution

Wrap Python in a fenced block tagged `run`:

    ```run
    print("hello")
    ```

stdout and stderr are captured and returned to the LLM.  The code runs with
CWD set to the workspace directory.

### Memory

| Command                  | Effect                                      |
|--------------------------|---------------------------------------------|
| `[MEMORY SET key=value]` | Persist a string to long-term memory        |
| `[MEMORY GET key]`       | Load a value; result fed back to the LLM    |
| `[MEMORY DEL key]`       | Remove a key                                |
| `[MEMORY LIST]`          | List all stored keys                        |

Values are single-line strings.  For structured/multi-line data, write a file
in the workspace from a `run` block instead.

### Skills

| Command              | Effect                                        |
|----------------------|-----------------------------------------------|
| `[SKILL LOAD name]`  | Inject that skill's full SKILL.md body        |

Skill *descriptions* (frontmatter only) are already in the system prompt.
The full body is loaded on-demand, keeping the initial context small.

### Action loop

Each turn the agent can produce multiple actions.  Execution output is fed
back as a follow-up message and the LLM gets another chance to act — up to
**5 rounds** per user turn.  This lets multi-step flows (run code, inspect
output, fix and re-run) finish in a single turn.

## Local Slash Commands (REPL)

| Command    | What it does                            |
|------------|-----------------------------------------|
| `/skills`  | List discovered skills                  |
| `/memory`  | Dump long-term memory                   |
| `/clear`   | Wipe short-term conversation history    |
| `/help`    | Print command list                      |
| `quit`     | Exit                                    |

## Configuration

`scripts/config.json` — every field is optional; sensible defaults everywhere.

```json
{
  "llm": {
    "base_url": "http://localhost:11434/v1",
    "api_key": "",
    "model":   "llama3"
  },
  "workspace": "./workspace",
  "skills":    { "paths": ["./skills/"] },
  "memory":    { "max_short_term": 20,
                 "summary_threshold": 15 }
}
```

| Key | Default | Notes |
|-----|---------|-------|
| `llm.base_url` | `http://localhost:11434/v1` | Any OpenAI-compatible URL |
| `llm.api_key` | `""` | See key-resolution order below |
| `llm.model` | `llama3` | Passed straight through to the endpoint |
| `workspace` | `./workspace` | Resolved relative to CWD |
| `skills.paths` | `["./skills/"]` | Resolved relative to CWD; 1- and 2-level scan |
| `memory.max_short_term` | 20 | Window size before summarisation |
| `memory.summary_threshold` | 15 | Message count that triggers summarisation |

### API-key resolution order

`--key` flag  →  `OPENAI_API_KEY` env var  →  `llm.api_key` in config  →  no auth

### Skill-path scanning

The loader checks every entry one and two levels deep, so both flat layouts
(`skills/my-skill/SKILL.md`) and monorepo layouts
(`skills/group/my-skill/SKILL.md`) are found automatically.

## Memory in Detail

### Short-term (conversation history)

Kept in memory; lost when the process exits.  When the message count reaches
`summary_threshold` the LLM is asked to summarise everything into a single
paragraph.  Only the summary and the most recent tail of messages are kept.
Use `/clear` to discard it manually.

### Long-term (key-value store)

Written to `<workspace>/_memory.json` immediately on every `SET`.  Loaded
automatically on startup — survives restarts.  Values are single-line strings.

## Notes

- **No pip installs.** Everything uses Python stdlib (`urllib`, `subprocess`,
  `json`, `pathlib`, `re`).
- **Any OpenAI-compatible endpoint.** Tested with Ollama, Together AI, and
  OpenAI.  Set `base_url` + `model` (+ `api_key` if needed).
- **Workspace isolation.** Code executes with CWD set to the workspace and
  `AGENT_WORKSPACE` in the environment.  The runner cleans up its own temp
  script after each execution.  `run_file()` rejects paths that escape the
  workspace.
- **Action-loop cap.** Five rounds max per turn prevents infinite loops while
  still allowing realistic multi-step flows.
- **Skill loading is lazy.** Only descriptions go into the system prompt.  Full
  bodies are loaded on demand via `[SKILL LOAD name]`, keeping context small
  when many skills are available.
