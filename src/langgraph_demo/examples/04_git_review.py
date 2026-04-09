"""Example 4: Review real git changes from a local repository.

Demonstrates:
- Real git diff as input (not sample diffs)
- Git tools (@tool) for fetching diffs, logs, and changed files
- Full pipeline reuse with real-world input
- Interactive: pass a repo path and git ref as arguments

Run:
  # Review uncommitted changes in current repo
  uv run python -m langgraph_demo.examples.04_git_review

  # Review against a specific ref
  uv run python -m langgraph_demo.examples.04_git_review --ref main

  # Review a different repo
  uv run python -m langgraph_demo.examples.04_git_review --repo /path/to/repo --ref HEAD~3
"""

import argparse
import operator
from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, Send, interrupt
from typing_extensions import TypedDict

from langgraph_demo.nodes import (
    compute_max_severity,
    format_report,
    get_llm,
    parse_findings_from_text,
)
from langgraph_demo.state import Finding
from langgraph_demo.tools.git_diff import git_changed_files, git_diff, git_log
from langgraph_demo.tools.knowledge_rag import search_knowledge_base
from langgraph_demo.tools.rules_db import query_rules_db

# ---------------------------------------------------------------------------
# Reviewer subgraph with tools (git + rules DB + RAG)
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 3

ALL_TOOLS = [query_rules_db, search_knowledge_base, git_diff, git_changed_files, git_log]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


class ReviewerSubgraphState(TypedDict):
    messages: Annotated[list, add_messages]
    findings: list[Finding]
    iterations: int
    category: str


def _make_reviewer_subgraph(system_prompt: str, category: str):
    def llm_call(state: ReviewerSubgraphState) -> dict:
        llm = get_llm()
        llm_with_tools = llm.bind_tools(ALL_TOOLS)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response], "iterations": state["iterations"] + 1}

    def tool_executor(state: ReviewerSubgraphState) -> dict:
        last = state["messages"][-1]
        results = []
        for tc in last.tool_calls:
            tool_fn = TOOLS_BY_NAME.get(tc["name"])
            if tool_fn:
                output = tool_fn.invoke(tc["args"])
            else:
                output = f"Unknown tool: {tc['name']}"
            results.append(ToolMessage(content=str(output), tool_call_id=tc["id"]))
        return {"messages": results}

    def extract_findings(state: ReviewerSubgraphState) -> dict:
        last_content = state["messages"][-1].content if state["messages"] else ""
        findings = parse_findings_from_text(last_content, category)
        return {"findings": findings}

    def should_continue(state: ReviewerSubgraphState) -> Literal["tool_executor", "extract_findings"]:
        if state["iterations"] >= MAX_TOOL_ITERATIONS:
            return "extract_findings"
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tool_executor"
        return "extract_findings"

    sub = StateGraph(ReviewerSubgraphState)
    sub.add_node("llm_call", llm_call)
    sub.add_node("tool_executor", tool_executor)
    sub.add_node("extract_findings", extract_findings)
    sub.add_edge(START, "llm_call")
    sub.add_conditional_edges("llm_call", should_continue, ["tool_executor", "extract_findings"])
    sub.add_edge("tool_executor", "llm_call")
    sub.add_edge("extract_findings", END)
    return sub.compile()


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SECURITY_PROMPT = """\
You are a security-focused code reviewer. You have access to tools:
- query_rules_db: look up known security rules and patterns
- search_knowledge_base: search best practices documentation
- git_diff: get the actual diff from a git repository
- git_changed_files: list changed files
- git_log: see recent commit history for context

Review the provided diff for security vulnerabilities.
Respond with a JSON array of findings: [{"severity", "description", "line_reference", "suggestion"}].
If no issues, return: []"""

STYLE_PROMPT = """\
You are a style-focused code reviewer. You have access to tools:
- query_rules_db: look up known style rules and patterns
- search_knowledge_base: search best practices documentation
- git_diff: get the actual diff from a git repository
- git_changed_files: list changed files

Review the provided diff for style issues (PEP 8, naming, complexity, docstrings).
Respond with a JSON array of findings: [{"severity", "description", "line_reference", "suggestion"}].
If no issues, return: []"""

PERFORMANCE_PROMPT = """\
You are a performance-focused code reviewer. You have access to tools:
- query_rules_db: look up known performance rules and patterns
- search_knowledge_base: search best practices documentation
- git_diff: get the actual diff from a git repository
- git_changed_files: list changed files

Review the provided diff for performance issues (N+1 queries, memory, algorithmic complexity).
Respond with a JSON array of findings: [{"severity", "description", "line_reference", "suggestion"}].
If no issues, return: []"""

security_subgraph = _make_reviewer_subgraph(SECURITY_PROMPT, "security")
style_subgraph = _make_reviewer_subgraph(STYLE_PROMPT, "style")
performance_subgraph = _make_reviewer_subgraph(PERFORMANCE_PROMPT, "performance")

SUBGRAPHS = {
    "security": (security_subgraph, SECURITY_PROMPT),
    "style": (style_subgraph, STYLE_PROMPT),
    "performance": (performance_subgraph, PERFORMANCE_PROMPT),
}

# ---------------------------------------------------------------------------
# Pipeline state and nodes
# ---------------------------------------------------------------------------


class ReviewerInput(TypedDict):
    code_diff: str
    reviewer_type: str


class GitReviewState(TypedDict):
    repo_path: str
    git_ref: str
    code_diff: str
    changed_files: str
    findings: Annotated[list[Finding], operator.add]
    max_severity: str
    final_report: str
    human_approved: bool


def fetch_diff(state: GitReviewState) -> dict:
    diff = git_diff.invoke({"ref": state["git_ref"], "path": state["repo_path"]})
    files = git_changed_files.invoke({"ref": state["git_ref"], "path": state["repo_path"]})
    return {"code_diff": diff, "changed_files": files}


def dispatch_reviewers(state: GitReviewState) -> list[Send]:
    if state["code_diff"].startswith("No changes found"):
        return []
    return [
        Send("run_reviewer", {"code_diff": state["code_diff"], "reviewer_type": "security"}),
        Send("run_reviewer", {"code_diff": state["code_diff"], "reviewer_type": "style"}),
        Send("run_reviewer", {"code_diff": state["code_diff"], "reviewer_type": "performance"}),
    ]


def run_reviewer(state: ReviewerInput) -> dict:
    reviewer_type = state["reviewer_type"]
    subgraph, system_prompt = SUBGRAPHS[reviewer_type]
    sub_input: ReviewerSubgraphState = {
        "messages": [
            ("system", system_prompt),
            ("human", f"Review this diff:\n\n```diff\n{state['code_diff']}\n```"),
        ],
        "findings": [],
        "iterations": 0,
        "category": reviewer_type,
    }
    result = subgraph.invoke(sub_input)
    return {"findings": result.get("findings", [])}


def aggregator(state: GitReviewState) -> dict:
    severity = compute_max_severity(state["findings"])
    report = format_report(state["findings"])

    header = f"# Git Review: `{state['git_ref'] or 'working tree'}`\n\n"
    header += f"**Changed files:**\n```\n{state['changed_files']}\n```\n\n"
    return {"max_severity": severity, "final_report": header + report}


def human_approval(state: GitReviewState) -> dict:
    decision = interrupt({
        "message": "High/critical severity findings detected. Review the report and decide.",
        "report_preview": state["final_report"][:500],
        "options": ["approve", "reject"],
    })
    return {"human_approved": decision == "approve"}


def route_by_severity(state: GitReviewState) -> Literal["human_approval", "__end__"]:
    if state["max_severity"] in ("high", "critical"):
        return "human_approval"
    return END


def route_after_fetch(state: GitReviewState) -> Literal["run_reviewer", "__end__"]:
    if state["code_diff"].startswith("No changes found"):
        return END
    return "run_reviewer"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

builder = StateGraph(GitReviewState)

builder.add_node("fetch_diff", fetch_diff)
builder.add_node("run_reviewer", run_reviewer)
builder.add_node("aggregator", aggregator)
builder.add_node("human_approval", human_approval)

builder.add_edge(START, "fetch_diff")
builder.add_conditional_edges("fetch_diff", dispatch_reviewers, ["run_reviewer"])
builder.add_edge("run_reviewer", "aggregator")
builder.add_conditional_edges("aggregator", route_by_severity, ["human_approval", END])
builder.add_edge("human_approval", END)

graph = builder.compile()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Review real git changes")
    parser.add_argument("--repo", default=".", help="Path to git repository (default: current dir)")
    parser.add_argument("--ref", default="HEAD", help="Git ref to diff against (default: HEAD)")
    args = parser.parse_args()

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[("langgraph_demo.state", "Finding")],
    )
    memory = InMemorySaver(serde=serde)
    standalone_graph = builder.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": "git-review-1"}}

    print(f"=== Git Code Review: {args.ref} in {args.repo} ===\n")

    result = standalone_graph.invoke(
        {
            "repo_path": args.repo,
            "git_ref": args.ref,
            "code_diff": "",
            "changed_files": "",
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        },
        config,
    )

    state = standalone_graph.get_state(config)
    if state.next:
        print("--- Interrupted: human approval required ---\n")
        print(result.get("final_report", ""))
        print("\nResuming with approval...\n")
        result = standalone_graph.invoke(Command(resume="approve"), config)

    print(result.get("final_report", "No changes to review."))
    if result.get("findings"):
        print(f"\nTotal findings: {len(result['findings'])}")
        print(f"Max severity: {result['max_severity']}")
