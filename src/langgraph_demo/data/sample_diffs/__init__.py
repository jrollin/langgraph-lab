from pathlib import Path

_DIR = Path(__file__).parent

SECURITY_DIFF = (_DIR / "security_issues.diff").read_text()
STYLE_DIFF = (_DIR / "style_issues.diff").read_text()
MIXED_DIFF = (_DIR / "mixed_issues.diff").read_text()
