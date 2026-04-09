"""Security-focused code reviewer agent.

Focuses on OWASP Top 10, injection, secrets exposure, unsafe deserialization,
missing input validation, and authentication issues.
"""

from langgraph_demo.nodes import get_llm, parse_findings_from_text
from langgraph_demo.state import MultiAgentState

SYSTEM_PROMPT = """\
You are a security-focused code reviewer specializing in OWASP Top 10 vulnerabilities.

Analyze the diff for:
- SQL injection, command injection, code injection (eval/exec)
- Hardcoded secrets, API keys, passwords
- Unsafe deserialization (pickle.loads, yaml.unsafe_load)
- Missing input validation and sanitization
- Authentication / authorization issues
- Cross-site scripting (XSS) if web-related
- Insecure cryptographic practices

Respond ONLY with a JSON array of findings. Each finding must have:
- "severity": "low" | "medium" | "high" | "critical"
- "description": concise description of the issue
- "line_reference": approximate location in the diff
- "suggestion": how to fix it

Example: [{"severity": "critical", "description": "SQL injection via f-string", "line_reference": "views.py:15", "suggestion": "Use parameterized queries"}]

If no security issues found, return: []
"""


def review_security(state: MultiAgentState) -> dict:
    llm = get_llm()
    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"Review this diff for security issues:\n\n```diff\n{state['code_diff']}\n```"),
    ])
    findings = parse_findings_from_text(response.content, "security")
    return {"findings": findings}
