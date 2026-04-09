# Product Overview

## Purpose

A progressive learning demo showcasing [LangGraph](https://langchain-ai.github.io/langgraph/) capabilities through a **code review pipeline** that analyzes PR diffs using specialized AI agents.

## Target Users

Developers learning LangGraph who want to understand its core concepts through a practical, real-world example.

## Key Features

1. **Single-agent reviewer** (Example 1) — minimal StateGraph: `START → review → END`
2. **Multi-agent fan-out/fan-in** (Example 2) — 3 parallel reviewers, aggregation, conditional routing, human-in-the-loop
3. **Full pipeline with tools** (Example 3) — subgraphs with tool-calling loops (SQLite + ChromaDB RAG), Send API, checkpointing

## LangGraph Concepts Demonstrated

See the full coverage matrix in [README.md](README.md#langgraph-concepts-covered).
