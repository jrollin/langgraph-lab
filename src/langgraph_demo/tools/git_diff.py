"""Git diff tool for analyzing local repository changes."""

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def git_diff(ref: str = "", path: str = ".") -> str:
    """Get the git diff for a local repository.

    Args:
        ref: Git ref to diff against. Examples:
            - "" (empty): unstaged changes (working tree vs index)
            - "HEAD": all uncommitted changes (staged + unstaged)
            - "main": diff current branch against main
            - "HEAD~3": last 3 commits
            - "abc123..def456": between two commits
        path: Path to the git repository. Defaults to current directory.

    Returns:
        The unified diff output, or an error message.
    """
    repo = Path(path).resolve()
    cmd = ["git", "-C", str(repo), "diff"]
    if ref:
        cmd.append(ref)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        return f"git diff failed: {result.stderr.strip()}"

    diff = result.stdout.strip()
    if not diff:
        return "No changes found for the given ref."

    # Truncate very large diffs to avoid overwhelming the LLM
    max_chars = 8000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + f"\n\n... (truncated, {len(diff)} total chars)"

    return diff


@tool
def git_log(count: int = 10, path: str = ".") -> str:
    """Get recent git commit log for a local repository.

    Args:
        count: Number of recent commits to show (default 10, max 50).
        path: Path to the git repository. Defaults to current directory.

    Returns:
        Recent commit history with hash, author, date, and message.
    """
    count = min(count, 50)
    repo = Path(path).resolve()
    cmd = [
        "git", "-C", str(repo), "log",
        f"-{count}",
        "--format=%h %an %ar %s",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        return f"git log failed: {result.stderr.strip()}"

    return result.stdout.strip() or "No commits found."


@tool
def git_changed_files(ref: str = "HEAD", path: str = ".") -> str:
    """List files changed in a git diff.

    Args:
        ref: Git ref to diff against (default: HEAD for uncommitted changes).
        path: Path to the git repository. Defaults to current directory.

    Returns:
        List of changed files with their status (Added/Modified/Deleted).
    """
    repo = Path(path).resolve()
    cmd = ["git", "-C", str(repo), "diff", "--name-status", ref]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        return f"git diff --name-status failed: {result.stderr.strip()}"

    output = result.stdout.strip()
    if not output:
        return "No changed files found."

    return output
