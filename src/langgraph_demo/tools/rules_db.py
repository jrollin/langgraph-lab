"""SQLite tool for querying the code review rules database."""

import sqlite3
from pathlib import Path

from langchain_core.tools import tool

DB_PATH = Path(__file__).parent.parent / "data" / "rules.db"

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@tool
def query_rules_db(category: str, min_severity: str = "") -> str:
    """Query the code review rules database for rules matching the given category and optional minimum severity.

    Args:
        category: One of "security", "style", or "performance".
        min_severity: Optional minimum severity filter: "low", "medium", "high", or "critical".

    Returns:
        Matching rules with descriptions and code examples.
    """
    if not DB_PATH.exists():
        return f"Rules database not found at {DB_PATH}. Run: python -m langgraph_demo.data.seed_rules"

    conn = sqlite3.connect(str(DB_PATH))
    query = "SELECT rule_name, severity, description, bad_example, good_example FROM rules WHERE category = ?"
    params: list = [category]

    if min_severity:
        rank = SEVERITY_RANK.get(min_severity, 1)
        query += " AND severity_rank >= ?"
        params.append(rank)

    query += " ORDER BY severity_rank DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return f"No rules found for category='{category}', min_severity='{min_severity}'."

    result = []
    for name, sev, desc, bad, good in rows:
        result.append(
            f"## {name} [{sev}]\n{desc}\n\nBad:\n```python\n{bad}\n```\n\nGood:\n```python\n{good}\n```"
        )
    return "\n\n---\n\n".join(result)
