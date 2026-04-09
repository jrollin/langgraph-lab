import os
import re

from langchain_ollama import ChatOllama, OllamaEmbeddings

from langgraph_demo.state import DiffHunk, Finding

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def get_llm() -> ChatOllama:
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model=model, base_url=base_url, temperature=0)


def get_embeddings() -> OllamaEmbeddings:
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return OllamaEmbeddings(model=model, base_url=base_url)


def compute_max_severity(findings: list[Finding]) -> str:
    if not findings:
        return "low"
    return max(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 0)).severity


def parse_diff(raw_diff: str) -> list[DiffHunk]:
    hunks: list[DiffHunk] = []
    current_file = "unknown"
    current_lines: list[str] = []

    for line in raw_diff.splitlines():
        if line.startswith("+++ b/"):
            if current_lines:
                hunks.append(DiffHunk(
                    file_path=current_file,
                    content="\n".join(current_lines),
                ))
                current_lines = []
            current_file = line[6:]
        elif line.startswith("--- "):
            continue
        else:
            current_lines.append(line)

    if current_lines:
        hunks.append(DiffHunk(file_path=current_file, content="\n".join(current_lines)))

    return hunks


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "No issues found."

    grouped: dict[str, list[Finding]] = {}
    for f in findings:
        grouped.setdefault(f.category, []).append(f)

    lines = ["# Code Review Report", ""]
    for category, items in sorted(grouped.items()):
        lines.append(f"## {category.title()} ({len(items)} findings)")
        lines.append("")
        for item in sorted(items, key=lambda x: SEVERITY_ORDER.get(x.severity, 0), reverse=True):
            lines.append(f"- **[{item.severity.upper()}]** {item.description}")
            if item.line_reference:
                lines.append(f"  - Line: {item.line_reference}")
            if item.suggestion:
                lines.append(f"  - Suggestion: {item.suggestion}")
        lines.append("")

    return "\n".join(lines)


def parse_findings_from_text(text: str, category: str) -> list[Finding]:
    """Parse LLM output into Finding objects with fallback strategies."""
    import json

    # Try to extract JSON array
    json_match = re.search(r"\[[\s\S]*?\]", text)
    if json_match:
        try:
            raw = json.loads(json_match.group())
            findings = []
            for item in raw:
                item.setdefault("category", category)
                findings.append(Finding(**item))
            return findings
        except (json.JSONDecodeError, ValueError):
            pass

    # Try individual JSON objects
    json_objects = re.findall(r"\{[^{}]+\}", text)
    if json_objects:
        findings = []
        for obj_str in json_objects:
            try:
                item = json.loads(obj_str)
                item.setdefault("category", category)
                findings.append(Finding(**item))
            except (json.JSONDecodeError, ValueError):
                continue
        if findings:
            return findings

    # Fallback: wrap the entire text as a single finding
    return [Finding(
        category=category,
        severity="medium",
        description=text.strip()[:500],
    )]
