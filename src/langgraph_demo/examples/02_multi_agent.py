"""Example 2: Multi-agent fan-out/fan-in code reviewer.

Demonstrates:
- Parallel execution (fan-out from START to 3 reviewers)
- Automatic state aggregation with Annotated[list, operator.add]
- Aggregator node computing max severity and formatting report
- Conditional edges based on severity
- Human-in-the-loop with interrupt() and Command(resume=...)
- InMemorySaver checkpointer

Run: uv run python -m langgraph_demo.examples.02_multi_agent
"""

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from langgraph_demo.agents.performance_reviewer import review_performance
from langgraph_demo.agents.security_reviewer import review_security
from langgraph_demo.agents.style_reviewer import review_style
from langgraph_demo.nodes import compute_max_severity, format_report
from langgraph_demo.state import MultiAgentState


def aggregator(state: MultiAgentState) -> dict:
    severity = compute_max_severity(state["findings"])
    report = format_report(state["findings"])
    return {"max_severity": severity, "final_report": report}


def human_approval(state: MultiAgentState) -> dict:
    decision = interrupt({
        "message": "High/critical severity findings detected. Review the report and decide.",
        "report_preview": state["final_report"][:500],
        "options": ["approve", "reject"],
    })
    return {"human_approved": decision == "approve"}


def route_by_severity(state: MultiAgentState) -> Literal["human_approval", "__end__"]:
    if state["max_severity"] in ("high", "critical"):
        return "human_approval"
    return END


# Build graph
builder = StateGraph(MultiAgentState)

# Nodes
builder.add_node("security_review", review_security)
builder.add_node("style_review", review_style)
builder.add_node("performance_review", review_performance)
builder.add_node("aggregator", aggregator)
builder.add_node("human_approval", human_approval)

# Fan-out: START → 3 reviewers in parallel
builder.add_edge(START, "security_review")
builder.add_edge(START, "style_review")
builder.add_edge(START, "performance_review")

# Fan-in: all reviewers → aggregator
builder.add_edge("security_review", "aggregator")
builder.add_edge("style_review", "aggregator")
builder.add_edge("performance_review", "aggregator")

# Conditional routing after aggregation
builder.add_conditional_edges("aggregator", route_by_severity, ["human_approval", END])
builder.add_edge("human_approval", END)

# Compile without checkpointer (Studio provides its own persistence).
# When running standalone, we add InMemorySaver in __main__.
graph = builder.compile()


if __name__ == "__main__":
    from langgraph_demo.data.sample_diffs import SECURITY_DIFF

    # Recompile with checkpointer for standalone execution (required for interrupt)
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[("langgraph_demo.state", "Finding")],
    )
    memory = InMemorySaver(serde=serde)
    standalone_graph = builder.compile(checkpointer=memory)

    from langgraph_demo.tracing import get_tracing_config

    config = get_tracing_config(thread_id="review-1", run_name="multi-agent-review")

    print("=== Multi-Agent Code Review ===\n")
    print("Running 3 parallel reviewers (security, style, performance)...\n")

    result = standalone_graph.invoke(
        {
            "code_diff": SECURITY_DIFF,
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        },
        config,
    )

    # Check if we were interrupted (high/critical severity)
    state = standalone_graph.get_state(config)
    if state.next:
        print("--- Interrupted: human approval required ---\n")
        print(result.get("final_report", ""))
        print("\nResuming with approval...\n")
        result = standalone_graph.invoke(Command(resume="approve"), config)

    print("\n=== Final Report ===\n")
    print(result.get("final_report", "No report generated"))
    print(f"\nMax severity: {result.get('max_severity', 'unknown')}")
    print(f"Human approved: {result.get('human_approved', 'N/A')}")
