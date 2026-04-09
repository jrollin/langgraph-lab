"""Langfuse tracing integration for LangGraph pipelines.

Provides a helper to create a Langfuse CallbackHandler that traces
all LLM calls, tool executions, and graph steps.

Setup:
  1. Run Langfuse locally: https://langfuse.com/docs/deployment/self-host
     Or use Langfuse Cloud: https://cloud.langfuse.com
  2. Set env vars in .env:
     LANGFUSE_PUBLIC_KEY=pk-lf-...
     LANGFUSE_SECRET_KEY=sk-lf-...
     LANGFUSE_HOST=http://localhost:3000  (or https://cloud.langfuse.com)

Usage:
  from langgraph_demo.tracing import get_tracing_config

  config = get_tracing_config(thread_id="review-1", run_name="security-review")
  result = graph.invoke(input, config)
"""

import os
from typing import Any


def get_langfuse_handler(run_name: str = "langgraph-review"):
    """Create a Langfuse CallbackHandler if credentials are configured.

    Returns None if LANGFUSE_PUBLIC_KEY is not set (tracing disabled).
    """
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return None

    from langfuse.callback import CallbackHandler

    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )


def get_tracing_config(
    thread_id: str = "default",
    run_name: str = "langgraph-review",
) -> dict[str, Any]:
    """Build a LangGraph config dict with optional Langfuse tracing.

    If Langfuse env vars are set, adds the CallbackHandler to callbacks.
    Otherwise returns a plain config (tracing disabled, no error).
    """
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
    }

    handler = get_langfuse_handler(run_name=run_name)
    if handler:
        config["callbacks"] = [handler]

    return config
