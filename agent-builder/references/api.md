# API Reference — agent-builder modules

All modules are in `scripts/`.  Zero external dependencies — stdlib only.

---

## LLMClient  (`llm_client.py`)

```python
from llm_client import LLMClient

client = LLMClient(
    base_url: str,          # e.g. "http://localhost:11434/v1"
    api_key:  str  = "",    # Bearer token; empty = no auth header
    model:    str  = "llama3",
)

reply: str = client.chat(
    messages:    list,              # [{"role": str, "content": str}, ...]
    temperature: float = 0.7,
    max_tokens:  int   = None,     # omitted → endpoint default
)
```

Raises `RuntimeError` on HTTP errors or connection failures.

---

## SkillLoader  (`skill_loader.py`)

```python
from skill_loader import SkillLoader, Skill

loader = SkillLoader(paths: list[str])   # filesystem paths to scan

skills: list[Skill] = loader.discover()  # (re-)scan and return all skills
skill:  Skill | None = loader.get("name")
names:  list[str]    = loader.list_names()
ctx:    str          = loader.descriptions()   # compact block for system prompt
```

### Skill object

| attribute     | type   | meaning                                        |
|---------------|--------|------------------------------------------------|
| `name`        | `str`  | frontmatter `name` field                       |
| `description` | `str`  | frontmatter `description` field                |
| `content`     | `str`  | full markdown body (after frontmatter)         |
| `path`        | `Path` | absolute path to the skill's directory         |

### parse_skill_md  (module-level helper)

```python
from skill_loader import parse_skill_md

parsed = parse_skill_md(text: str)
# → {"frontmatter": {key: value, ...}, "body": str}
```

Handles flat `key: value` frontmatter only (no nested YAML).

---

## CodeRunner  (`code_runner.py`)

```python
from code_runner import CodeRunner, RunResult

runner = CodeRunner(
    workspace: Path,
    timeout:   int = 30,      # default execution timeout in seconds
)

result: RunResult = runner.run(code: str, timeout: int = None)
result: RunResult = runner.run_file(filename: str, timeout: int = None)
```

### RunResult

| attribute      | type   | notes                              |
|----------------|--------|------------------------------------|
| `stdout`       | `str`  | captured standard output           |
| `stderr`       | `str`  | captured standard error            |
| `returncode`   | `int`  | 0 = success; -1 = timeout/error   |
| `success`      | `bool` | property: `returncode == 0`        |

### Behaviour details

* `run()` writes the code to a temp file in the workspace, executes it via
  `sys.executable`, then deletes the temp file — regardless of outcome.
* `run_file()` only executes files that already exist *inside* the workspace.
  Absolute paths and any resolved path that escapes the workspace are rejected
  before execution begins.
* CWD during execution is the workspace.  The env var `AGENT_WORKSPACE` is set
  to the workspace path so scripts can find it programmatically.

---

## Memory  (`memory.py`)

```python
from memory import Memory

mem = Memory(
    workspace:          Path,
    max_short_term:     int = 20,
    summary_threshold:  int = 15,
)
```

### Short-term (conversation window)

```python
mem.add_message(role: str, content: str)
messages: list   = mem.get_messages()          # [{role, content}, ...]
needs:    bool   = mem.needs_summarization()   # True when len >= threshold
prompt:   str    = mem.summarization_prompt()  # feed this to the LLM
mem.apply_summary(summary: str)                # compress history
mem.clear()                                    # discard everything
```

Summarisation workflow:

1. Check `needs_summarization()`.
2. If `True`, send `summarization_prompt()` to the LLM (temperature 0).
3. Pass the LLM's reply to `apply_summary()`.
4. History is now: one summary system-message + the most recent tail of
   real messages.

### Long-term (persistent key-value store)

```python
mem.set(key: str, value)          # write + flush to disk immediately
value = mem.get(key, default=None)
mem.delete(key) -> bool
keys: list = mem.keys()
```

Backed by `<workspace>/_memory.json`.  Written on every `set`/`delete`.
Loaded automatically from disk on `Memory.__init__`.

---

## Agent  (`agent.py`)

```python
from agent import Agent

agent = Agent(
    llm:               LLMClient,
    workspace:         Path,
    skill_paths:       list[str],
    max_short_term:    int = 20,
    summary_threshold: int = 15,
)

reply: str = agent.chat(user_input: str)
```

`chat()` is the only method you need for normal operation.  It:

1. Summarises short-term memory if the threshold is reached.
2. Appends the user message.
3. Enters an action loop (max 5 rounds):
   - Calls the LLM with the full system prompt + message history.
   - Parses the response for `[MEMORY …]`, `[SKILL LOAD …]`, and
     `` ```run ``` `` blocks.
   - Executes them and feeds the combined output back as a user message.
   - Stops when a response contains no actionable syntax.
4. Returns the final assistant reply.

### Exposed sub-components

| attribute   | type           | use                                     |
|-------------|----------------|-----------------------------------------|
| `skills`    | `SkillLoader`  | call `.discover()`, `.list_names()`, … |
| `runner`    | `CodeRunner`   | call `.run(code)` directly if needed    |
| `memory`    | `Memory`       | inspect or manipulate memory directly   |
