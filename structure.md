# Project Structure

```
src/langgraph_demo/
├── state.py                 # All state TypedDicts + Finding/DiffHunk models
├── nodes.py                 # Shared: get_llm(), get_embeddings(), parse_diff(),
│                            #   compute_max_severity(), format_report(), parse_findings_from_text()
├── examples/
│   ├── 01_simple_reviewer.py   # Example 1: START → review → END
│   ├── 02_multi_agent.py       # Example 2: fan-out/fan-in + HITL
│   └── 03_full_pipeline.py     # Example 3: subgraphs + tools + Send API
├── agents/
│   ├── security_reviewer.py    # OWASP-focused prompts + review_security()
│   ├── style_reviewer.py       # PEP 8-focused prompts + review_style()
│   └── performance_reviewer.py # N+1/complexity-focused prompts + review_performance()
├── tools/
│   ├── rules_db.py             # @tool query_rules_db() — SQLite
│   └── knowledge_rag.py        # @tool search_knowledge_base() — ChromaDB
└── data/
    ├── seed_rules.py           # Seed SQLite with 25 review rules
    ├── seed_knowledge.py       # Seed ChromaDB with 15 best-practices docs
    ├── rules.db                # (generated) SQLite database
    ├── chroma_db/              # (generated) ChromaDB persistence
    └── sample_diffs/           # 3 realistic Python .diff files
        ├── security_issues.diff
        ├── style_issues.diff
        └── mixed_issues.diff
```

## Key Patterns

- **State**: all state types live in `state.py`, using `Annotated[list[Finding], operator.add]` for parallel aggregation
- **LLM output parsing**: `parse_findings_from_text()` in `nodes.py` handles JSON extraction with regex fallback for unreliable local models
- **Subgraphs**: Example 3 builds per-reviewer subgraphs with tool-calling loops (max 3 iterations)
- **Tools**: LangChain `@tool` functions wrapping SQLite queries and ChromaDB similarity search
