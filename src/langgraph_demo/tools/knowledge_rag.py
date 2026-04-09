"""ChromaDB RAG tool for semantic search over coding best practices."""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.tools import tool

from langgraph_demo.nodes import get_embeddings

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "code_review_knowledge"


@tool
def search_knowledge_base(query: str, category: str = "") -> str:
    """Search the knowledge base of coding best practices, style guides, and security guidelines.

    Args:
        query: Natural language search query describing the topic to look up.
        category: Optional filter: "security", "style", or "performance".

    Returns:
        Relevant documentation snippets from the knowledge base.
    """
    if not CHROMA_DIR.exists():
        return f"Knowledge base not found at {CHROMA_DIR}. Run: python -m langgraph_demo.data.seed_knowledge"

    embeddings = get_embeddings()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    filter_dict = {"category": category} if category else None
    docs = vectorstore.similarity_search(query, k=3, filter=filter_dict)

    if not docs:
        return "No relevant knowledge found."

    return "\n\n---\n\n".join(
        f"[{doc.metadata.get('source', 'unknown')}] {doc.metadata.get('topic', '')}\n{doc.page_content}"
        for doc in docs
    )
