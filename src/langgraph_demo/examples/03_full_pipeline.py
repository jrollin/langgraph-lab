"""Example 3: Full code review pipeline with tools, subgraphs, and Send API.

Demonstrates:
- Diff parsing as a preprocessing node
- Tool-calling subgraphs (LLM → tool → LLM loop with max iterations)
- Send API for dynamic fan-out
- SQLite rules DB + ChromaDB RAG as tools
- Conditional routing based on severity
- Human-in-the-loop with interrupt()
- Checkpointing with InMemorySaver

Run: uv run python -m langgraph_demo.examples.03_full_pipeline
"""

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
    parse_diff,
    parse_findings_from_text,
)
from langgraph_demo.state import DiffHunk, Finding, FullPipelineState
from langgraph_demo.tools.knowledge_rag import search_knowledge_base
from langgraph_demo.tools.rules_db import query_rules_db

# ---------------------------------------------------------------------------
# Reviewer subgraph with tool-calling loop
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 3

ALL_TOOLS = [query_rules_db, search_knowledge_base]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


class ReviewerSubgraphState(TypedDict):
    messages: Annotated[list, add_messages]
    findings: list[Finding]
    iterations: int
    category: str


def _make_reviewer_subgraph(system_prompt: str, category: str):
    """Build a compiled subgraph for a single reviewer with tool-calling."""

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
# System prompts for each reviewer
# ---------------------------------------------------------------------------

SECURITY_PROMPT = """\
You are a security-focused code reviewer. You have access to tools:
- query_rules_db: look up known security rules and patterns
- search_knowledge_base: search best practices documentation

FIRST, use query_rules_db with category="security" to load relevant rules.
THEN, use search_knowledge_base to find related best practices.
FINALLY, analyze the code diff using the rules and knowledge you retrieved.

Respond with a JSON array of findings. Each finding: {"severity", "description", "line_reference", "suggestion"}.
If no issues, return: []"""

STYLE_PROMPT = """\
You are a style-focused code reviewer. You have access to tools:
- query_rules_db: look up known style rules and patterns
- search_knowledge_base: search best practices documentation

FIRST, use query_rules_db with category="style" to load relevant rules.
THEN, use search_knowledge_base to find related best practices.
FINALLY, analyze the code diff using the rules and knowledge you retrieved.

Respond with a JSON array of findings. Each finding: {"severity", "description", "line_reference", "suggestion"}.
If no issues, return: []"""

PERFORMANCE_PROMPT = """\
You are a performance-focused code reviewer. You have access to tools:
- query_rules_db: look up known performance rules and patterns
- search_knowledge_base: search best practices documentation

FIRST, use query_rules_db with category="performance" to load relevant rules.
THEN, use search_knowledge_base to find related best practices.
FINALLY, analyze the code diff using the rules and knowledge you retrieved.

Respond with a JSON array of findings. Each finding: {"severity", "description", "line_reference", "suggestion"}.
If no issues, return: []"""

# Pre-compile subgraphs
security_subgraph = _make_reviewer_subgraph(SECURITY_PROMPT, "security")
style_subgraph = _make_reviewer_subgraph(STYLE_PROMPT, "style")
performance_subgraph = _make_reviewer_subgraph(PERFORMANCE_PROMPT, "performance")

SUBGRAPHS = {
    "security": (security_subgraph, SECURITY_PROMPT),
    "style": (style_subgraph, STYLE_PROMPT),
    "performance": (performance_subgraph, PERFORMANCE_PROMPT),
}

# ---------------------------------------------------------------------------
# Pipeline state with reviewer dispatch
# ---------------------------------------------------------------------------


class ReviewerInput(TypedDict):
    code_diff: str
    reviewer_type: str


class PipelineState(TypedDict):
    raw_diff: str
    hunks: list[DiffHunk]
    findings: Annotated[list[Finding], operator.add]
    max_severity: str
    final_report: str
    human_approved: bool


def parse_diff_node(state: PipelineState) -> dict:
    hunks = parse_diff(state["raw_diff"])
    return {"hunks": hunks}


def dispatch_reviewers(state: PipelineState) -> list[Send]:
    return [
        Send("run_reviewer", {"code_diff": state["raw_diff"], "reviewer_type": "security"}),
        Send("run_reviewer", {"code_diff": state["raw_diff"], "reviewer_type": "style"}),
        Send("run_reviewer", {"code_diff": state["raw_diff"], "reviewer_type": "performance"}),
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


def aggregator(state: PipelineState) -> dict:
    severity = compute_max_severity(state["findings"])
    report = format_report(state["findings"])
    return {"max_severity": severity, "final_report": report}


def human_approval(state: PipelineState) -> dict:
    decision = interrupt({
        "message": "High/critical severity findings detected. Review the report and decide.",
        "report_preview": state["final_report"][:500],
        "options": ["approve", "reject"],
    })
    return {"human_approved": decision == "approve"}


def route_by_severity(state: PipelineState) -> Literal["human_approval", "__end__"]:
    if state["max_severity"] in ("high", "critical"):
        return "human_approval"
    return END


# ---------------------------------------------------------------------------
# Build the pipeline graph
# ---------------------------------------------------------------------------

builder = StateGraph(PipelineState)

builder.add_node("parse_diff", parse_diff_node)
builder.add_node("run_reviewer", run_reviewer)
builder.add_node("aggregator", aggregator)
builder.add_node("human_approval", human_approval)

builder.add_edge(START, "parse_diff")
builder.add_conditional_edges("parse_diff", dispatch_reviewers, ["run_reviewer"])
builder.add_edge("run_reviewer", "aggregator")
builder.add_conditional_edges("aggregator", route_by_severity, ["human_approval", END])
builder.add_edge("human_approval", END)

serde = JsonPlusSerializer(
    allowed_msgpack_modules=[("langgraph_demo.state", "Finding")],
)
memory = InMemorySaver(serde=serde)
graph = builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from langgraph_demo.data.sample_diffs import MIXED_DIFF

    config = {"configurable": {"thread_id": "pipeline-1"}}

    print("=== Full Code Review Pipeline ===")
    print("Using tools: SQLite rules DB + ChromaDB knowledge base\n")

    result = graph.invoke(
        {
            "raw_diff": MIXED_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        },
        config,
    )

    # Check for interrupt
    state = graph.get_state(config)
    if state.next:
        print("--- Interrupted: human approval required ---\n")
        print(result.get("final_report", ""))
        print("\nResuming with approval...\n")
        result = graph.invoke(Command(resume="approve"), config)

    print("\n=== Final Report ===\n")
    print(result.get("final_report", "No report generated"))
    print(f"\nMax severity: {result.get('max_severity', 'unknown')}")
    print(f"Human approved: {result.get('human_approved', 'N/A')}")
    print(f"Total findings: {len(result.get('findings', []))}")
