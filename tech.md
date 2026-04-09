# Technology Stack

## Runtime

- **Python 3.13** (pinned via `.python-version`)
- **uv** for dependency management

## Core Dependencies

| Package | Purpose |
|---------|---------|
| langgraph | Graph-based agent orchestration |
| langchain | LLM abstractions, tools, messages |
| langchain-ollama | ChatOllama + OllamaEmbeddings |
| langchain-chroma | ChromaDB vector store wrapper |
| chromadb | Vector database for RAG |
| pydantic | State/finding model validation |

## Infrastructure

- **Ollama** (local) — LLM inference (`llama3.1:8b`) and embeddings (`nomic-embed-text`)
- **SQLite** — rules database (25 code review rules)
- **ChromaDB** — vector store for best-practices knowledge base (15 documents)

## Constraints

- Fully offline — no external API calls required
- All models run locally via Ollama
