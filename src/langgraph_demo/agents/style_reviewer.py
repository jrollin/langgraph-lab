"""Style-focused code reviewer agent.

Focuses on PEP 8, naming conventions, code complexity, docstrings,
exception handling patterns, and dead code.
"""

from langgraph_demo.nodes import get_llm, parse_findings_from_text
from langgraph_demo.state import MultiAgentState

SYSTEM_PROMPT = """\
You are a style-focused code reviewer specializing in Python best practices.

Analyze the diff for:
- PEP 8 violations (naming: snake_case for functions/variables, PascalCase for classes)
- Missing or inadequate docstrings
- Functions with too many parameters (>5)
- Functions that are too long (>50 lines)
- Bare except clauses (should catch specific exceptions)
- Unused imports
- Magic numbers (use named constants)
- Comparison to None using == instead of `is`
- Overly complex boolean expressions
- Missing type hints on function signatures

Respond ONLY with a JSON array of findings. Each finding must have:
- "severity": "low" | "medium" | "high" | "critical"
- "description": concise description of the issue
- "line_reference": approximate location in the diff
- "suggestion": how to fix it

Example: [{"severity": "low", "description": "Function uses camelCase instead of snake_case", "line_reference": "services.py:8", "suggestion": "Rename getUserById to get_user_by_id"}]

If no style issues found, return: []
"""


def review_style(state: MultiAgentState) -> dict:
    llm = get_llm()
    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"Review this diff for style issues:\n\n```diff\n{state['code_diff']}\n```"),
    ])
    findings = parse_findings_from_text(response.content, "style")
    return {"findings": findings}
