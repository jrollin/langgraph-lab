"""Unit tests for Example 3: Full pipeline with streaming.

All LLM calls are mocked — no Ollama required.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END

from langgraph_demo.state import Finding

_mod = importlib.import_module("langgraph_demo.examples.03_full_pipeline")
PipelineState = _mod.PipelineState
aggregator = _mod.aggregator
builder = _mod.builder
dispatch_reviewers = _mod.dispatch_reviewers
graph = _mod.graph
parse_diff_node = _mod.parse_diff_node
route_by_severity = _mod.route_by_severity
run_reviewer = _mod.run_reviewer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
--- a/app.py
+++ b/app.py
@@ -1,3 +1,5 @@
+import os
+password = os.getenv("DB_PASS")
 def hello():
     return "world"
"""


def _make_finding(category: str = "security", severity: str = "high") -> Finding:
    return Finding(
        category=category,
        severity=severity,
        description="test finding",
        line_reference="L1",
        suggestion="fix it",
    )


def _fake_llm_response(findings_json: str = "[]") -> AIMessage:
    return AIMessage(content=findings_json)


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------


class TestGraphStructure:
    def test_graph_has_expected_nodes(self):
        node_names = set(graph.get_graph().nodes.keys())
        assert {"parse_diff", "run_reviewer", "aggregator", "human_approval"}.issubset(
            node_names
        )

    def test_graph_starts_with_parse_diff(self):
        g = graph.get_graph()
        start_edges = [e.target for e in g.edges if e.source == "__start__"]
        assert "parse_diff" == start_edges[0]

    def test_graph_compiles(self):
        assert graph is not None


# ---------------------------------------------------------------------------
# Node logic (no LLM needed)
# ---------------------------------------------------------------------------


class TestParseDiffNode:
    def test_returns_hunks(self):
        state: PipelineState = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }
        result = parse_diff_node(state)
        assert len(result["hunks"]) == 1
        assert result["hunks"][0].file_path == "app.py"

    def test_empty_diff_returns_no_hunks(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }
        result = parse_diff_node(state)
        assert result["hunks"] == []


class TestDispatchReviewers:
    def test_sends_three_reviewers(self):
        state: PipelineState = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }
        sends = dispatch_reviewers(state)
        assert len(sends) == 3
        reviewer_types = {s.arg["reviewer_type"] for s in sends}
        assert reviewer_types == {"security", "style", "performance"}


class TestAggregator:
    def test_computes_severity_and_report(self):
        findings = [
            _make_finding("security", "high"),
            _make_finding("style", "low"),
        ]
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": findings,
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }
        result = aggregator(state)
        assert result["max_severity"] == "high"
        assert "Code Review Report" in result["final_report"]

    def test_no_findings(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }
        result = aggregator(state)
        assert result["max_severity"] == "low"
        assert "No issues found" in result["final_report"]


class TestRouteBySeverity:
    def test_high_severity_routes_to_human(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "high",
            "final_report": "",
            "human_approved": False,
        }
        assert route_by_severity(state) == "human_approval"

    def test_critical_routes_to_human(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "critical",
            "final_report": "",
            "human_approved": False,
        }
        assert route_by_severity(state) == "human_approval"

    def test_low_severity_routes_to_end(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "low",
            "final_report": "",
            "human_approved": False,
        }
        assert route_by_severity(state) == END

    def test_medium_severity_routes_to_end(self):
        state: PipelineState = {
            "raw_diff": "",
            "hunks": [],
            "findings": [],
            "max_severity": "medium",
            "final_report": "",
            "human_approved": False,
        }
        assert route_by_severity(state) == END


# ---------------------------------------------------------------------------
# run_reviewer with mocked LLM
# ---------------------------------------------------------------------------


class TestRunReviewer:
    @patch.object(_mod, "get_llm")
    def test_returns_findings_from_llm(self, mock_get_llm):
        findings_json = '[{"severity": "high", "description": "SQL injection risk", "line_reference": "L5", "suggestion": "use parameterized queries"}]'
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response(findings_json)
        mock_get_llm.return_value = mock_llm

        result = run_reviewer({"code_diff": SAMPLE_DIFF, "reviewer_type": "security"})
        assert len(result["findings"]) == 1
        assert result["findings"][0].severity == "high"

    @patch.object(_mod, "get_llm")
    def test_empty_findings(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response("[]")
        mock_get_llm.return_value = mock_llm

        result = run_reviewer({"code_diff": SAMPLE_DIFF, "reviewer_type": "style"})
        assert result["findings"] == []


# ---------------------------------------------------------------------------
# Streaming integration (full graph with mocked LLM)
# ---------------------------------------------------------------------------


class TestStreaming:
    @patch.object(_mod, "get_llm")
    def test_stream_yields_all_nodes(self, mock_get_llm):
        findings_json = '[{"severity": "low", "description": "minor style issue"}]'
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response(findings_json)
        mock_get_llm.return_value = mock_llm

        initial_state = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }

        visited_nodes = []
        for update in graph.stream(initial_state, stream_mode="updates"):
            for node_name in update:
                visited_nodes.append(node_name)

        assert "parse_diff" in visited_nodes
        assert "run_reviewer" in visited_nodes
        assert "aggregator" in visited_nodes

    @patch.object(_mod, "get_llm")
    def test_stream_updates_mode_returns_dicts(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response("[]")
        mock_get_llm.return_value = mock_llm

        initial_state = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }

        updates = list(graph.stream(initial_state, stream_mode="updates"))
        assert len(updates) > 0
        for update in updates:
            assert isinstance(update, dict)

    @patch.object(_mod, "get_llm")
    def test_stream_aggregator_has_severity(self, mock_get_llm):
        findings_json = '[{"severity": "medium", "description": "potential issue"}]'
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response(findings_json)
        mock_get_llm.return_value = mock_llm

        initial_state = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }

        for update in graph.stream(initial_state, stream_mode="updates"):
            if "aggregator" in update:
                agg = update["aggregator"]
                assert "max_severity" in agg
                assert "final_report" in agg

    @patch.object(_mod, "get_llm")
    def test_low_severity_skips_human_approval(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _fake_llm_response("[]")
        mock_get_llm.return_value = mock_llm

        initial_state = {
            "raw_diff": SAMPLE_DIFF,
            "hunks": [],
            "findings": [],
            "max_severity": "",
            "final_report": "",
            "human_approved": False,
        }

        visited_nodes = []
        for update in graph.stream(initial_state, stream_mode="updates"):
            for node_name in update:
                visited_nodes.append(node_name)

        assert "human_approval" not in visited_nodes
