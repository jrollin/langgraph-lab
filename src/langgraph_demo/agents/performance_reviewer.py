"""Performance-focused code reviewer agent.

Focuses on N+1 queries, algorithmic complexity, memory usage,
string concatenation patterns, and caching opportunities.
"""

from langgraph_demo.nodes import get_llm, parse_findings_from_text
from langgraph_demo.state import MultiAgentState

SYSTEM_PROMPT = """\
You are a performance-focused code reviewer specializing in Python optimization.

Analyze the diff for:
- N+1 query patterns (database queries inside loops)
- String concatenation in loops (use str.join or list append)
- Loading entire datasets into memory without pagination
- Repeated expensive computations that could be cached
- Unbounded queries (missing LIMIT clauses)
- Synchronous I/O blocking an async context
- Inefficient data structures for the use case
- Unnecessary object creation in hot paths

Respond ONLY with a JSON array of findings. Each finding must have:
- "severity": "low" | "medium" | "high" | "critical"
- "description": concise description of the issue
- "line_reference": approximate location in the diff
- "suggestion": how to fix it

Example: [{"severity": "high", "description": "N+1 query: session.query(Event) called inside loop over users", "line_reference": "analytics.py:25", "suggestion": "Use a single query with JOIN or IN clause"}]

If no performance issues found, return: []
"""


def review_performance(state: MultiAgentState) -> dict:
    llm = get_llm()
    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"Review this diff for performance issues:\n\n```diff\n{state['code_diff']}\n```"),
    ])
    findings = parse_findings_from_text(response.content, "performance")
    return {"findings": findings}
