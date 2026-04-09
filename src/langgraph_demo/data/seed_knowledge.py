"""Seed the ChromaDB vector store with coding best practices.

Run: uv run python -m langgraph_demo.data.seed_knowledge
"""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from langgraph_demo.nodes import get_embeddings

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "code_review_knowledge"

DOCUMENTS = [
    # --- Security ---
    Document(
        page_content=(
            "SQL Injection Prevention\n\n"
            "SQL injection is one of the most dangerous web vulnerabilities. "
            "It occurs when user input is directly interpolated into SQL queries. "
            "Always use parameterized queries or prepared statements. "
            "In Python, use placeholders: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)). "
            "For ORMs like SQLAlchemy, use the query builder: session.query(User).filter_by(id=user_id). "
            "Never use f-strings, format(), or % formatting to build SQL queries. "
            "Apply input validation as a defense-in-depth measure — validate types, ranges, and formats."
        ),
        metadata={"category": "security", "source": "owasp-injection", "topic": "sql_injection"},
    ),
    Document(
        page_content=(
            "Secrets Management Best Practices\n\n"
            "Never hardcode secrets (API keys, passwords, tokens) in source code. "
            "Use environment variables: os.environ['API_KEY']. "
            "For complex setups, use a secrets manager (AWS Secrets Manager, HashiCorp Vault). "
            "Add patterns to .gitignore: .env, *.pem, credentials.json. "
            "Use tools like detect-secrets or trufflehog in CI/CD pipelines. "
            "Rotate secrets regularly and use short-lived tokens when possible."
        ),
        metadata={"category": "security", "source": "secrets-management", "topic": "hardcoded_secrets"},
    ),
    Document(
        page_content=(
            "Unsafe Deserialization\n\n"
            "Python's pickle module can execute arbitrary code during deserialization. "
            "Never use pickle.loads() on untrusted data — this is equivalent to eval(). "
            "yaml.load() without Loader parameter is also unsafe. "
            "Safe alternatives: json for data exchange, yaml.safe_load() for YAML, "
            "msgpack for binary serialization, protobuf for structured data. "
            "If pickle is required for trusted internal use, sign the data with hmac."
        ),
        metadata={"category": "security", "source": "deserialization", "topic": "unsafe_deserialization"},
    ),
    Document(
        page_content=(
            "Input Validation Patterns\n\n"
            "Validate all external input at system boundaries. "
            "Use Pydantic models for request validation in FastAPI/Flask. "
            "Validate types (int, str), ranges (0 < age < 150), formats (email regex), "
            "and length (max 255 chars for names). "
            "Sanitize HTML input with bleach or markupsafe to prevent XSS. "
            "For file uploads, validate MIME types, file size, and use a whitelist of extensions."
        ),
        metadata={"category": "security", "source": "input-validation", "topic": "validation"},
    ),
    # --- Style ---
    Document(
        page_content=(
            "PEP 8 Key Guidelines\n\n"
            "Use snake_case for functions, methods, variables, and modules. "
            "Use PascalCase for class names. Use UPPER_SNAKE_CASE for constants. "
            "Indent with 4 spaces (never tabs). Maximum line length: 79 chars (99 for code). "
            "Two blank lines before top-level definitions, one before methods. "
            "Imports: standard library first, then third-party, then local — separated by blank lines. "
            "Use absolute imports. Avoid wildcard imports (from module import *)."
        ),
        metadata={"category": "style", "source": "pep8", "topic": "naming_conventions"},
    ),
    Document(
        page_content=(
            "Python Docstring Conventions (Google Style)\n\n"
            "Every public function, class, and module should have a docstring. "
            "First line: brief summary ending with a period. "
            "Args section: list each parameter with type and description. "
            "Returns section: describe the return value and type. "
            "Raises section: list exceptions that may be raised. "
            "Example:\n"
            '  def fetch_user(user_id: int) -> User:\n'
            '      """Fetch a user by ID.\n\n'
            '      Args:\n'
            '          user_id: The unique identifier of the user.\n\n'
            '      Returns:\n'
            '          The User object if found.\n\n'
            '      Raises:\n'
            '          NotFoundError: If no user matches the given ID.\n'
            '      """'
        ),
        metadata={"category": "style", "source": "docstrings", "topic": "documentation"},
    ),
    Document(
        page_content=(
            "Exception Handling Patterns\n\n"
            "Never use bare except: clauses — they catch SystemExit and KeyboardInterrupt. "
            "Catch specific exceptions: except (ValueError, TypeError) as e. "
            "Use except Exception as e if you truly need a broad catch, but log the error. "
            "Don't silently swallow exceptions with pass — at minimum log them. "
            "Use try/except only around the specific code that may fail, not entire functions. "
            "Re-raise with 'raise' (not 'raise e') to preserve the traceback. "
            "Use contextlib.suppress() for expected exceptions that should be ignored."
        ),
        metadata={"category": "style", "source": "exception-patterns", "topic": "error_handling"},
    ),
    Document(
        page_content=(
            "Type Hints Best Practices\n\n"
            "Add type hints to all public function signatures. "
            "Use built-in generics (list[int], dict[str, Any]) on Python 3.9+. "
            "Use Optional[X] or X | None for nullable types. "
            "Use TypedDict for structured dictionaries. "
            "Use Protocol for structural subtyping (duck typing with types). "
            "Run mypy or pyright in CI to catch type errors. "
            "Don't over-annotate local variables — let type inference work."
        ),
        metadata={"category": "style", "source": "type-hints", "topic": "type_annotations"},
    ),
    Document(
        page_content=(
            "Clean Code Principles for Python\n\n"
            "Functions should do one thing and be under 20-30 lines. "
            "If a function has more than 5 parameters, consider a config object or dataclass. "
            "Use meaningful variable names — 'user' not 'u', 'order_total' not 'x'. "
            "Replace magic numbers with named constants: TIMEOUT_SECONDS = 30. "
            "Prefer list comprehensions over map/filter for simple transformations. "
            "Use early returns to reduce nesting. "
            "Don't repeat yourself — extract shared logic into helper functions."
        ),
        metadata={"category": "style", "source": "clean-code", "topic": "code_quality"},
    ),
    # --- Performance ---
    Document(
        page_content=(
            "N+1 Query Problem\n\n"
            "The N+1 query problem occurs when code executes one query to get N items, "
            "then N more queries to get related data for each item. "
            "Example: for user in users: orders = db.query(Order).filter_by(user_id=user.id).all(). "
            "This generates N+1 database roundtrips. "
            "Solutions: use JOINs (db.query(User).join(Order)), "
            "use IN clause (db.query(Order).filter(Order.user_id.in_(user_ids))), "
            "use eager loading (joinedload, subqueryload in SQLAlchemy), "
            "or use batch loading (DataLoader pattern). "
            "Always check query counts during development with tools like SQLAlchemy echo=True."
        ),
        metadata={"category": "performance", "source": "n-plus-1", "topic": "database_queries"},
    ),
    Document(
        page_content=(
            "String Handling Performance\n\n"
            "String concatenation with += in a loop creates a new string object each time: O(n^2). "
            "Use str.join() instead: ''.join(parts). "
            "For building strings incrementally, use a list and join at the end. "
            "Use f-strings for formatting (fastest method): f'{name}: {value}'. "
            "For very large strings, consider io.StringIO as a buffer. "
            "Avoid repeated string slicing on large strings."
        ),
        metadata={"category": "performance", "source": "string-performance", "topic": "string_handling"},
    ),
    Document(
        page_content=(
            "Database Query Optimization\n\n"
            "Always add LIMIT to queries that could return large result sets. "
            "Use COUNT queries instead of len(query.all()) to count rows. "
            "Add database indexes on columns used in WHERE, JOIN, and ORDER BY clauses. "
            "Use SELECT only the columns you need, not SELECT *. "
            "Use EXPLAIN ANALYZE to understand query execution plans. "
            "Batch inserts/updates with executemany() or bulk operations. "
            "Consider connection pooling for high-throughput applications."
        ),
        metadata={"category": "performance", "source": "db-optimization", "topic": "database_queries"},
    ),
    Document(
        page_content=(
            "Memory Management in Python\n\n"
            "Process large files line-by-line, not by reading the entire file: "
            "use 'for line in file' instead of file.read(). "
            "Use generators (yield) for processing large sequences without loading all into memory. "
            "Use itertools for memory-efficient iteration patterns. "
            "Be cautious with list comprehensions on very large datasets — use generator expressions. "
            "Delete large objects explicitly with del and call gc.collect() if needed. "
            "Use __slots__ on classes with many instances to reduce per-instance memory."
        ),
        metadata={"category": "performance", "source": "memory-management", "topic": "memory"},
    ),
    Document(
        page_content=(
            "Async/Await Best Practices\n\n"
            "Never call synchronous I/O (requests.get, time.sleep, file I/O) inside async functions — "
            "it blocks the entire event loop. "
            "Use httpx.AsyncClient or aiohttp for async HTTP calls. "
            "Use asyncio.sleep() instead of time.sleep(). "
            "Use aiofiles for async file I/O. "
            "For CPU-bound work in async context, use asyncio.to_thread() or ProcessPoolExecutor. "
            "Use asyncio.gather() to run multiple coroutines concurrently. "
            "Set timeouts on all external calls with asyncio.wait_for()."
        ),
        metadata={"category": "performance", "source": "async-patterns", "topic": "async"},
    ),
    Document(
        page_content=(
            "Caching Strategies\n\n"
            "Use functools.lru_cache for memoizing pure function results. "
            "Use functools.cache (Python 3.9+) for unbounded caches. "
            "For web applications, use Redis or Memcached for shared caches. "
            "Cache expensive computations, not cheap ones — profile first. "
            "Set appropriate TTLs to avoid stale data. "
            "Use cache-aside pattern: check cache → miss → compute → store → return. "
            "Invalidate caches on data mutation to maintain consistency."
        ),
        metadata={"category": "performance", "source": "caching", "topic": "caching"},
    ),
]


def seed():
    embeddings = get_embeddings()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    existing = vectorstore._collection.count()
    if existing > 0:
        print(f"Collection '{COLLECTION_NAME}' already has {existing} documents. Skipping seed.")
        return

    vectorstore.add_documents(DOCUMENTS)
    print(f"Seeded {len(DOCUMENTS)} documents into ChromaDB at {CHROMA_DIR}")


if __name__ == "__main__":
    seed()
