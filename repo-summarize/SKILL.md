---
name: repo-summarize
description: Summarize a GitHub repository. Use when you need a quick overview of what a repo does, its structure, and key technologies. Returns a concise summary with purpose, tech stack, and structure.
license: Unlicense
metadata:
  author: jbpayton
  version: "0.1"
---

# Repo Summarize

Generate a quick summary of any GitHub repository.

## When to Use

- You found a repo and want to quickly understand what it does
- You need to evaluate whether a repo is relevant to your task
- You want a structured overview before diving into code

## Usage

```bash
python scripts/summarize.py <repo>
```

Where `<repo>` is either:
- Full URL: `https://github.com/owner/repo`
- Short form: `owner/repo`

## Examples

**Input:**
```bash
python scripts/summarize.py facebook/react
```

**Output:**
```
Repository: facebook/react
Stars: 220k | Forks: 45k | Language: JavaScript

PURPOSE:
A JavaScript library for building user interfaces.

TECH STACK:
- Primary: JavaScript (98%)
- Also: TypeScript, HTML

STRUCTURE:
- packages/ - Core React packages (react, react-dom, etc.)
- scripts/ - Build and release tooling
- fixtures/ - Test fixtures and examples

KEY FILES:
- README.md - Project overview
- package.json - Dependencies and scripts
- CONTRIBUTING.md - Contribution guidelines
```

## Requirements

- Python 3.10+
- `requests` library (or uses urllib as fallback)
- GitHub token in `.env` for higher rate limits (optional but recommended)

## Notes

- Without a token, GitHub API limits to 60 requests/hour
- Large repos may have truncated file listings
- Private repos require a token with appropriate access
