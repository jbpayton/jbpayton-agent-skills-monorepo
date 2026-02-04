#!/usr/bin/env python3
"""
Summarize a GitHub repository.

Usage:
    python summarize.py <repo>
    python summarize.py facebook/react
    python summarize.py https://github.com/facebook/react
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

def load_env_file() -> dict:
    """Load variables from .env file."""
    # Look for .env in project root (two levels up from scripts/)
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if not env_path.exists():
        env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return {}

    result = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result

def get_github_token() -> Optional[str]:
    """Get GitHub token from .env or environment."""
    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN") or env_vars.get("GH_TOKEN")
    if not token:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    return token

def github_request(endpoint: str) -> Optional[dict]:
    """Make a GitHub API request."""
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    headers = {
        "User-Agent": "repo-summarize",
        "Accept": "application/vnd.github.v3+json"
    }
    token = get_github_token()
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        return None

def fetch_raw_content(owner: str, repo: str, path: str) -> Optional[str]:
    """Fetch raw file content from a repo."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
    headers = {"User-Agent": "repo-summarize"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None

def parse_repo_arg(repo_arg: str) -> tuple[str, str]:
    """Parse repo argument into (owner, repo) tuple."""
    # Handle full URL
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_arg)
    if match:
        return match.groups()

    # Handle owner/repo format
    if "/" in repo_arg and not repo_arg.startswith("http"):
        parts = repo_arg.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    raise ValueError(f"Invalid repo format: {repo_arg}\nUse 'owner/repo' or 'https://github.com/owner/repo'")

def format_number(n: int) -> str:
    """Format large numbers (1234567 -> 1.2M)."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def extract_purpose(readme: str) -> str:
    """Extract the main purpose from README content."""
    if not readme:
        return "No README found."

    lines = readme.strip().split("\n")
    purpose_lines = []

    # Skip title and badges, find first real paragraph
    in_content = False
    for line in lines:
        stripped = line.strip()

        # Skip empty lines at start
        if not stripped and not in_content:
            continue

        # Skip markdown headers
        if stripped.startswith("#"):
            in_content = True
            continue

        # Skip badges and images
        if stripped.startswith("[![") or stripped.startswith("!["):
            continue

        # Skip HTML tags
        if stripped.startswith("<"):
            continue

        # Found content
        if stripped:
            in_content = True
            purpose_lines.append(stripped)
            if len(" ".join(purpose_lines)) > 200:
                break

    purpose = " ".join(purpose_lines)[:300]
    if len(purpose) == 300:
        purpose = purpose.rsplit(" ", 1)[0] + "..."

    return purpose or "No description found in README."

def summarize_structure(contents: list[dict]) -> list[str]:
    """Summarize the top-level directory structure."""
    dirs = []
    key_files = []

    important_files = {"README.md", "package.json", "setup.py", "pyproject.toml",
                       "Cargo.toml", "go.mod", "Makefile", "CONTRIBUTING.md"}

    for item in contents[:50]:  # Limit to first 50 items
        name = item.get("name", "")
        item_type = item.get("type", "")

        if item_type == "dir" and not name.startswith("."):
            dirs.append(name)
        elif item_type == "file" and name in important_files:
            key_files.append(name)

    return dirs[:10], key_files

def main():
    parser = argparse.ArgumentParser(description="Summarize a GitHub repository")
    parser.add_argument("repo", help="Repository (owner/repo or full URL)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        owner, repo = parse_repo_arg(args.repo)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Fetch repo info
    repo_data = github_request(f"/repos/{owner}/{repo}")
    if not repo_data:
        print(f"Repository not found: {owner}/{repo}", file=sys.stderr)
        sys.exit(1)

    # Fetch additional data
    languages = github_request(f"/repos/{owner}/{repo}/languages") or {}
    contents = github_request(f"/repos/{owner}/{repo}/contents") or []
    readme = fetch_raw_content(owner, repo, "README.md")

    # Process data
    total_bytes = sum(languages.values()) if languages else 1
    lang_percentages = {k: round(v / total_bytes * 100) for k, v in languages.items()}
    top_languages = sorted(lang_percentages.items(), key=lambda x: -x[1])[:5]

    dirs, key_files = summarize_structure(contents if isinstance(contents, list) else [])
    purpose = extract_purpose(readme)

    if args.json:
        output = {
            "repository": f"{owner}/{repo}",
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "primary_language": repo_data.get("language"),
            "description": repo_data.get("description"),
            "purpose": purpose,
            "languages": dict(top_languages),
            "directories": dirs,
            "key_files": key_files,
            "url": repo_data.get("html_url")
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        stars = format_number(repo_data.get("stargazers_count", 0))
        forks = format_number(repo_data.get("forks_count", 0))
        primary_lang = repo_data.get("language") or "Unknown"

        print(f"Repository: {owner}/{repo}")
        print(f"Stars: {stars} | Forks: {forks} | Language: {primary_lang}")
        print()

        print("PURPOSE:")
        print(purpose)
        print()

        if top_languages:
            print("TECH STACK:")
            primary = top_languages[0]
            print(f"- Primary: {primary[0]} ({primary[1]}%)")
            if len(top_languages) > 1:
                others = ", ".join(lang for lang, _ in top_languages[1:4])
                print(f"- Also: {others}")
            print()

        if dirs:
            print("STRUCTURE:")
            for d in dirs[:6]:
                print(f"- {d}/")
            if len(dirs) > 6:
                print(f"  ... and {len(dirs) - 6} more directories")
            print()

        if key_files:
            print("KEY FILES:")
            for f in key_files:
                print(f"- {f}")
            print()

        print(f"URL: {repo_data.get('html_url')}")

if __name__ == "__main__":
    main()
