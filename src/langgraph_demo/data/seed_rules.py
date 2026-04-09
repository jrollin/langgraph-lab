"""Seed the SQLite rules database with code review rules.

Run: uv run python -m langgraph_demo.data.seed_rules
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "rules.db"

SCHEMA = """\
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    severity_rank INTEGER NOT NULL,
    rule_name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    bad_example TEXT NOT NULL,
    good_example TEXT NOT NULL
)
"""

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

RULES = [
    # --- Security ---
    {
        "category": "security",
        "severity": "critical",
        "rule_name": "sql_injection",
        "description": "SQL injection via string formatting or concatenation. User input is interpolated directly into SQL queries.",
        "bad_example": 'query = f"SELECT * FROM users WHERE id = {user_id}"\ncursor.execute(query)',
        "good_example": 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
    },
    {
        "category": "security",
        "severity": "critical",
        "rule_name": "hardcoded_secrets",
        "description": "Hardcoded API keys, passwords, or tokens in source code.",
        "bad_example": 'API_KEY = "sk-proj-abc123def456"',
        "good_example": 'API_KEY = os.environ["API_KEY"]',
    },
    {
        "category": "security",
        "severity": "critical",
        "rule_name": "eval_exec_injection",
        "description": "Using eval() or exec() on user-supplied input enables arbitrary code execution.",
        "bad_example": 'result = eval(request.form["expression"])',
        "good_example": 'import ast\nresult = ast.literal_eval(expression)',
    },
    {
        "category": "security",
        "severity": "high",
        "rule_name": "unsafe_deserialization",
        "description": "Using pickle.loads or yaml.unsafe_load on untrusted data enables arbitrary code execution.",
        "bad_example": "config = pickle.loads(user_data)",
        "good_example": 'config = json.loads(user_data)  # Use safe formats',
    },
    {
        "category": "security",
        "severity": "high",
        "rule_name": "missing_input_validation",
        "description": "User input is used without validation or sanitization.",
        "bad_example": 'user_id = request.args["id"]\nUser.query.get(user_id)',
        "good_example": 'user_id = int(request.args["id"])  # Validate type',
    },
    {
        "category": "security",
        "severity": "medium",
        "rule_name": "insecure_random",
        "description": "Using random module for security-sensitive operations instead of secrets module.",
        "bad_example": "token = ''.join(random.choices(string.ascii_letters, k=32))",
        "good_example": "token = secrets.token_urlsafe(32)",
    },
    {
        "category": "security",
        "severity": "medium",
        "rule_name": "open_redirect",
        "description": "Redirecting to a user-supplied URL without validation.",
        "bad_example": 'return redirect(request.args["next"])',
        "good_example": 'url = request.args["next"]\nif url_is_safe(url):\n    return redirect(url)',
    },
    {
        "category": "security",
        "severity": "medium",
        "rule_name": "debug_mode_production",
        "description": "Running with debug mode enabled in production exposes stack traces and internals.",
        "bad_example": "app.run(debug=True)",
        "good_example": 'app.run(debug=os.getenv("FLASK_DEBUG", "false") == "true")',
    },
    {
        "category": "security",
        "severity": "low",
        "rule_name": "verbose_error_messages",
        "description": "Exposing internal error details to end users.",
        "bad_example": 'return jsonify({"error": str(e), "traceback": traceback.format_exc()})',
        "good_example": 'logger.exception("Internal error")\nreturn jsonify({"error": "Internal server error"}), 500',
    },
    {
        "category": "security",
        "severity": "medium",
        "rule_name": "missing_csrf_protection",
        "description": "State-changing endpoints without CSRF token validation.",
        "bad_example": '@app.route("/transfer", methods=["POST"])\ndef transfer():\n    # No CSRF check',
        "good_example": "from flask_wtf.csrf import CSRFProtect\ncsrf = CSRFProtect(app)",
    },
    # --- Style ---
    {
        "category": "style",
        "severity": "low",
        "rule_name": "missing_docstrings",
        "description": "Public functions and classes missing docstrings.",
        "bad_example": "def process_order(user_id, items):\n    total = sum(i.price for i in items)",
        "good_example": 'def process_order(user_id, items):\n    """Process an order and return the total."""\n    total = sum(i.price for i in items)',
    },
    {
        "category": "style",
        "severity": "medium",
        "rule_name": "function_too_long",
        "description": "Functions exceeding 50 lines. Break into smaller, focused functions.",
        "bad_example": "def do_everything():\n    # 80 lines of mixed concerns",
        "good_example": "def validate_input():\n    ...\ndef process():\n    ...\ndef format_output():\n    ...",
    },
    {
        "category": "style",
        "severity": "low",
        "rule_name": "inconsistent_naming",
        "description": "Mixing camelCase and snake_case in Python code. PEP 8 requires snake_case for functions and variables.",
        "bad_example": "def getUserById(userId):\n    ...",
        "good_example": "def get_user_by_id(user_id):\n    ...",
    },
    {
        "category": "style",
        "severity": "medium",
        "rule_name": "bare_except",
        "description": "Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt.",
        "bad_example": "try:\n    ...\nexcept:\n    pass",
        "good_example": "try:\n    ...\nexcept (ValueError, TypeError) as e:\n    logger.error(e)",
    },
    {
        "category": "style",
        "severity": "low",
        "rule_name": "unused_imports",
        "description": "Imported modules that are never used in the file.",
        "bad_example": "import os\nimport sys\nimport re\n\ndef hello():\n    return 'hello'",
        "good_example": "def hello():\n    return 'hello'",
    },
    {
        "category": "style",
        "severity": "low",
        "rule_name": "magic_numbers",
        "description": "Numeric literals without explanation. Use named constants.",
        "bad_example": "if total > 1000:\n    send_alert()",
        "good_example": "ALERT_THRESHOLD = 1000\nif total > ALERT_THRESHOLD:\n    send_alert()",
    },
    {
        "category": "style",
        "severity": "low",
        "rule_name": "none_comparison",
        "description": "Comparing to None using == instead of is/is not.",
        "bad_example": "if result == None:\n    return default",
        "good_example": "if result is None:\n    return default",
    },
    {
        "category": "style",
        "severity": "low",
        "rule_name": "missing_type_hints",
        "description": "Function parameters and return types without type annotations.",
        "bad_example": "def calculate(a, b):\n    return a + b",
        "good_example": "def calculate(a: float, b: float) -> float:\n    return a + b",
    },
    # --- Performance ---
    {
        "category": "performance",
        "severity": "high",
        "rule_name": "n_plus_1_query",
        "description": "Database query executed inside a loop. Each iteration triggers a separate query.",
        "bad_example": "for uid in user_ids:\n    user = session.query(User).get(uid)\n    events = session.query(Event).filter_by(user_id=uid).all()",
        "good_example": "users = session.query(User).filter(User.id.in_(user_ids)).all()\nevents = session.query(Event).filter(Event.user_id.in_(user_ids)).all()",
    },
    {
        "category": "performance",
        "severity": "medium",
        "rule_name": "string_concat_in_loop",
        "description": "String concatenation with += in a loop creates a new string each iteration. O(n^2) complexity.",
        "bad_example": 'result = ""\nfor item in items:\n    result = result + str(item)',
        "good_example": 'result = "".join(str(item) for item in items)',
    },
    {
        "category": "performance",
        "severity": "medium",
        "rule_name": "unbounded_query",
        "description": "Query without LIMIT clause can return millions of rows and exhaust memory.",
        "bad_example": "users = session.query(User).all()",
        "good_example": "users = session.query(User).limit(100).all()",
    },
    {
        "category": "performance",
        "severity": "medium",
        "rule_name": "repeated_computation_in_loop",
        "description": "Expensive computation repeated in every loop iteration that could be hoisted.",
        "bad_example": "for item in items:\n    config = load_config()  # called every iteration\n    process(item, config)",
        "good_example": "config = load_config()\nfor item in items:\n    process(item, config)",
    },
    {
        "category": "performance",
        "severity": "medium",
        "rule_name": "full_file_in_memory",
        "description": "Reading entire large files into memory instead of streaming.",
        "bad_example": "data = open('huge.csv').read()\nfor line in data.split('\\n'):\n    ...",
        "good_example": "with open('huge.csv') as f:\n    for line in f:\n        ...",
    },
    {
        "category": "performance",
        "severity": "low",
        "rule_name": "missing_db_index_hint",
        "description": "Filtering on a column that likely lacks a database index.",
        "bad_example": "session.query(Event).filter_by(timestamp=ts).all()  # timestamp may not be indexed",
        "good_example": "# Ensure index exists: CREATE INDEX idx_event_ts ON events(timestamp)",
    },
    {
        "category": "performance",
        "severity": "high",
        "rule_name": "sync_io_in_async",
        "description": "Synchronous I/O call inside async function blocks the event loop.",
        "bad_example": "async def fetch():\n    data = requests.get(url)  # blocks event loop",
        "good_example": "async def fetch():\n    async with httpx.AsyncClient() as client:\n        data = await client.get(url)",
    },
]


def seed():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(SCHEMA)

    for rule in RULES:
        conn.execute(
            """INSERT OR IGNORE INTO rules
            (category, severity, severity_rank, rule_name, description, bad_example, good_example)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                rule["category"],
                rule["severity"],
                SEVERITY_RANK[rule["severity"]],
                rule["rule_name"],
                rule["description"],
                rule["bad_example"],
                rule["good_example"],
            ),
        )

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    conn.close()
    print(f"Seeded {count} rules into {DB_PATH}")


if __name__ == "__main__":
    seed()
