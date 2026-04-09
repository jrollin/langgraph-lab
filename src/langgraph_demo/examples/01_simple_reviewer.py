"""Example 1: Simple single-agent code reviewer.

Demonstrates:
- StateGraph with TypedDict
- Adding nodes and edges
- START → review → END flow
- ChatOllama invocation

Run: uv run python -m langgraph_demo.examples.01_simple_reviewer
"""

from langgraph.graph import END, START, StateGraph

from langgraph_demo.nodes import get_llm
from langgraph_demo.state import SimpleReviewState

SYSTEM_PROMPT = (
    "You are an expert code reviewer. "
    "Analyze the given diff for bugs, security issues, style problems, "
    "and performance concerns. Be specific about line references."
)


def review(state: SimpleReviewState) -> dict:
    llm = get_llm()
    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"Review this diff:\n\n```diff\n{state['code_diff']}\n```"),
    ])
    return {"review": response.content}


# Build graph
builder = StateGraph(SimpleReviewState)
builder.add_node("review", review)
builder.add_edge(START, "review")
builder.add_edge("review", END)

graph = builder.compile()


if __name__ == "__main__":
    from langgraph_demo.data.sample_diffs import MIXED_DIFF

    print("=== Simple Code Reviewer ===\n")
    result = graph.invoke({"code_diff": MIXED_DIFF})
    print(result["review"])
