# LangGraph Code Review Pipeline

A progressive demo showcasing [LangGraph](https://langchain-ai.github.io/langgraph/) through an automated code review pipeline that analyzes PR diffs using specialized AI agents.

## Architecture

```
Example 1: Simple                Example 2: Multi-Agent              Example 3: Full Pipeline
                                                                     
START → review → END             START → security_review ─┐          START → parse_diff
                                 START → style_review ────┤               ↓
                                 START → perf_review ─────┤          Send → run_reviewer (×3)
                                                          ↓               │ (subgraph with tools)
                                                     aggregator          ↓
                                                          ↓          aggregator
                                                    [severity?]          ↓
                                                     ↓       ↓     [severity?]
                                                   HITL     END      ↓       ↓
                                                     ↓             HITL     END
                                                    END              ↓
                                                                    END
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Ollama](https://ollama.ai) running locally

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Setup

```bash
# Install dependencies
uv sync

# Seed knowledge sources (required for Example 3)
uv run python -m langgraph_demo.data.seed_rules
uv run python -m langgraph_demo.data.seed_knowledge
```

## Running Examples

Each example builds on the previous one, introducing more LangGraph concepts:

### Example 1: Simple Single-Agent Reviewer

Concepts: `StateGraph`, nodes, edges, `ChatOllama`

```bash
uv run python -m langgraph_demo.examples.01_simple_reviewer
```

### Example 2: Multi-Agent Fan-out/Fan-in

Concepts: parallel execution, `Annotated[list, operator.add]`, conditional edges, `interrupt()`, `InMemorySaver`

```bash
uv run python -m langgraph_demo.examples.02_multi_agent
```

### Example 3: Full Pipeline with Tools

Concepts: subgraphs, tool-calling loops, `Send` API, SQLite + ChromaDB RAG tools, checkpointing

```bash
uv run python -m langgraph_demo.examples.03_full_pipeline
```

## Knowledge Sources

### Rules Database (SQLite)

25 code review rules across 3 categories (security, style, performance), each with severity, description, and bad/good code examples.

### Knowledge Base (ChromaDB + RAG)

15 best-practices documents embedded with `nomic-embed-text`, covering OWASP guidelines, PEP 8, performance patterns, and more. Queried via semantic search during reviews.

## LangGraph Concepts Covered

| Concept | Ex.1 | Ex.2 | Ex.3 |
|---------|:----:|:----:|:----:|
| StateGraph / nodes / edges | v | v | v |
| Annotated state (operator.add) | | v | v |
| Conditional edges | | v | v |
| Parallel execution (fan-out) | | v | v |
| Human-in-the-loop (interrupt) | | v | v |
| Checkpointing (InMemorySaver) | | v | v |
| Tool calling (@tool) | | | v |
| Subgraphs | | | v |
| Send API | | | v |
| RAG (ChromaDB) | | | v |
