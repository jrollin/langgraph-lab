import operator
from typing import Annotated

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Finding(BaseModel):
    category: str = Field(description="security | style | performance")
    severity: str = Field(description="low | medium | high | critical")
    description: str
    line_reference: str = ""
    suggestion: str = ""


class DiffHunk(BaseModel):
    file_path: str
    content: str
    language: str = "python"


# Example 1
class SimpleReviewState(TypedDict):
    code_diff: str
    review: str


# Example 2
class MultiAgentState(TypedDict):
    code_diff: str
    findings: Annotated[list[Finding], operator.add]
    max_severity: str
    final_report: str
    human_approved: bool


# Example 3
class FullPipelineState(TypedDict):
    raw_diff: str
    hunks: list[DiffHunk]
    findings: Annotated[list[Finding], operator.add]
    max_severity: str
    final_report: str
    human_approved: bool
