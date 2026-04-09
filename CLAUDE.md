# LangGraph Code Review Pipeline

## Quick Reference

- `uv sync` — install dependencies
- `uv run python -m langgraph_demo.data.seed_rules` — seed SQLite rules DB
- `uv run python -m langgraph_demo.data.seed_knowledge` — seed ChromaDB knowledge base
- `uv run python -m langgraph_demo.examples.01_simple_reviewer` — Example 1
- `uv run python -m langgraph_demo.examples.02_multi_agent` — Example 2
- `uv run python -m langgraph_demo.examples.03_full_pipeline` — Example 3
- `uv run python -m langgraph_demo.examples.04_git_review` — Example 4 (real git diff)
- `uv run langgraph dev` — launch LangGraph Studio

## Prerequisites

- [uv](https://docs.astral.sh/uv/), Python 3.13 (pinned via `.python-version`)
- Ollama running locally with `llama3.1:8b` and `nomic-embed-text` pulled

## Project Docs

- [product.md](product.md) — product overview
- [tech.md](tech.md) — technology stack
- [structure.md](structure.md) — file organization and conventions
