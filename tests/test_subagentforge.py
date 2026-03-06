"""
Tests for SubAgentForge
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the module importable from anywhere
sys.path.insert(0, str(Path(__file__).parent))
import subagentforge as saf


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect all file I/O to a temp directory for every test."""
    monkeypatch.setattr(saf, "DATA_DIR", tmp_path)
    monkeypatch.setattr(saf, "DB_PATH", tmp_path / "forge.db")
    monkeypatch.setattr(saf, "BRIEFS_DIR", tmp_path / "briefs")
    monkeypatch.setattr(saf, "REPORTS_DIR", tmp_path / "reports")
    saf._init_db()
    yield tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL DETECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestProtocolDetection:
    def test_build_keywords(self):
        assert saf.detect_protocol("Build a new Python tool") == "build"
        assert saf.detect_protocol("Implement the REST API") == "build"
        assert saf.detect_protocol("Create a database schema") == "build"
        assert saf.detect_protocol("Write the README documentation") == "build"
        assert saf.detect_protocol("Refactor the legacy module") == "build"
        assert saf.detect_protocol("Develop the scoring algorithm") == "build"

    def test_hunter_keywords(self):
        assert saf.detect_protocol("Research the Half-Kelly criterion") == "hunter"
        assert saf.detect_protocol("Investigate the memory leak") == "hunter"
        assert saf.detect_protocol("Analyse trading strategies") == "hunter"
        assert saf.detect_protocol("Analyze competitor landscape") == "hunter"
        assert saf.detect_protocol("Plan the Phase 2 architecture") == "hunter"
        assert saf.detect_protocol("Audit Bolt's code quality") == "hunter"
        assert saf.detect_protocol("Design the data pipeline") == "hunter"

    def test_bughunt_keywords(self):
        assert saf.detect_protocol("Test all API endpoints") == "bughunt"
        assert saf.detect_protocol("Debug the safe_scan decorator") == "bughunt"
        assert saf.detect_protocol("Fix the pytest failures") == "bughunt"
        assert saf.detect_protocol("Validate the signal format") == "bughunt"
        assert saf.detect_protocol("Verify the risk engine output") == "bughunt"
        assert saf.detect_protocol("QA the new release") == "bughunt"

    def test_default_fallback_to_build(self):
        assert saf.detect_protocol("Complete the FINAI project") == "build"
        assert saf.detect_protocol("") == "build"

    def test_case_insensitive(self):
        assert saf.detect_protocol("BUILD THE THING") == "build"
        assert saf.detect_protocol("RESEARCH the topic") == "hunter"
        assert saf.detect_protocol("DEBUG this code") == "bughunt"


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN DETECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainDetection:
    def test_explicit_domain_override(self):
        assert saf.detect_domain("do anything", domain="python") == "python"
        assert saf.detect_domain("do anything", domain="finance") == "finance"
        assert saf.detect_domain("do anything", domain="mcp") == "mcp"

    def test_unknown_domain_falls_back_to_general(self):
        assert saf.detect_domain("do anything", domain="nonexistent") == "general"

    def test_domain_from_task_keywords(self):
        assert saf.detect_domain("build a python tool") == "python"
        assert saf.detect_domain("implement mcp server") == "mcp"
        assert saf.detect_domain("analyze crypto flows") == "crypto"

    def test_default_is_general(self):
        assert saf.detect_domain("do something completely unrelated") == "general"

    def test_domain_case_insensitive(self):
        assert saf.detect_domain("anything", domain="PYTHON") == "python"
        assert saf.detect_domain("anything", domain="Finance") == "finance"


# ─────────────────────────────────────────────────────────────────────────────
# BRIEF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

class TestBriefGeneration:
    def test_brief_contains_assignment_id(self):
        brief = saf.generate_brief("saf_test_id", "BOLT", "Build MCP server",
                                   "mcp", "build", "HIGH", "FORGE")
        assert "saf_test_id" in brief

    def test_brief_contains_agent_name(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert "BOLT" in brief

    def test_brief_contains_task(self):
        task = "Build a very specific unique task XYZ123"
        brief = saf.generate_brief("test", "BOLT", task, "python", "build", "NORMAL", "FORGE")
        assert task in brief

    def test_brief_contains_mr_path(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert saf.MR_PATH in brief

    def test_brief_contains_build_protocol_for_build_task(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert saf.BUILD_PROTOCOL_PATH in brief
        assert "BUILD PROTOCOL" in brief.upper()

    def test_brief_contains_hunter_protocol_for_hunter_task(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "hunter", "NORMAL", "FORGE")
        assert saf.HUNTER_PROTOCOL_PATH in brief
        assert "HUNTER" in brief.upper()

    def test_brief_contains_bughunt_protocol(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "bughunt", "NORMAL", "FORGE")
        assert saf.BUG_HUNT_PROTOCOL_PATH in brief
        assert "BUG HUNT" in brief.upper()

    def test_brief_contains_all_quality_gates(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        for gate in saf.QUALITY_GATES:
            assert gate in brief

    def test_brief_contains_domain_context(self):
        brief = saf.generate_brief("test", "BOLT", "task", "finance", "build", "NORMAL", "FORGE")
        assert "FINANCE SPECIALIST" in brief
        assert saf.DOMAIN_CONTEXTS["finance"][:20] in brief

    def test_brief_contains_completion_procedure(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert "COMPLETION PROCEDURE" in brief
        assert "AgentHandoff" in brief

    def test_brief_contains_reset_instruction(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert "Reset" in brief or "reset" in brief or "RESET" in brief

    def test_brief_contains_escalation_path(self):
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert "ESCALATION" in brief.upper() or "BLOCKED" in brief

    def test_brief_includes_deliverables_when_provided(self):
        deliverables = "Unique deliverable requirement ABC789"
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build",
                                   "NORMAL", "FORGE", deliverables=deliverables)
        assert deliverables in brief

    def test_brief_includes_context_when_provided(self):
        context = "Special context note CONTEXT_XYZ"
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build",
                                   "NORMAL", "FORGE", context=context)
        assert context in brief

    def test_brief_includes_acceptance_criteria(self):
        criteria = "Must pass 95% test coverage CRITERIA_123"
        brief = saf.generate_brief("test", "BOLT", "task", "python", "build",
                                   "NORMAL", "FORGE", acceptance_criteria=criteria)
        assert criteria in brief

    def test_brief_returns_string(self):
        result = saf.generate_brief("test", "BOLT", "task", "python", "build", "NORMAL", "FORGE")
        assert isinstance(result, str)
        assert len(result) > 500  # Must be substantive


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabase:
    def test_init_creates_db(self, tmp_path):
        assert saf.DB_PATH.exists()

    def test_gen_id_format(self):
        id1 = saf._gen_id()
        id2 = saf._gen_id()
        assert id1.startswith("saf_")
        assert id2.startswith("saf_")
        assert id1 != id2  # Unique IDs
        assert len(id1) > 15

    def test_multiple_inits_dont_corrupt(self):
        saf._init_db()
        saf._init_db()
        saf._init_db()
        conn = saf._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
        conn.close()
        assert count == 0  # Should not create duplicate rows


# ─────────────────────────────────────────────────────────────────────────────
# FORGE COMMAND (Assignment Creation)
# ─────────────────────────────────────────────────────────────────────────────

class TestForgeCommand:
    def _make_args(self, **kwargs):
        defaults = {
            "agent": "BOLT",
            "task": "Build the test tool",
            "domain": "python",
            "protocol": None,
            "priority": "NORMAL",
            "from_agent": "FORGE",
            "deliverables": None,
            "context": None,
            "files": None,
            "criteria": None,
        }
        defaults.update(kwargs)
        return type("Args", (), defaults)()

    def test_forge_creates_assignment_in_db(self, capsys):
        args = self._make_args()
        assignment_id = saf.cmd_forge(args)
        conn = saf._get_conn()
        row = conn.execute("SELECT id, agent, status FROM assignments WHERE id=?",
                           (assignment_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "BOLT"
        assert row[2] == "briefed"

    def test_forge_saves_brief_file(self, capsys):
        args = self._make_args()
        assignment_id = saf.cmd_forge(args)
        brief_path = saf.BRIEFS_DIR / f"{assignment_id}_BRIEF.md"
        assert brief_path.exists()
        content = brief_path.read_text(encoding="utf-8")
        assert assignment_id in content

    def test_forge_auto_detects_protocol(self, capsys):
        args = self._make_args(task="Research the best approach", protocol=None)
        saf.cmd_forge(args)
        conn = saf._get_conn()
        row = conn.execute("SELECT protocol FROM assignments ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        assert row[0] == "hunter"

    def test_forge_respects_explicit_protocol(self, capsys):
        args = self._make_args(protocol="bughunt")
        saf.cmd_forge(args)
        conn = saf._get_conn()
        row = conn.execute("SELECT protocol FROM assignments ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        assert row[0] == "bughunt"

    def test_forge_auto_detects_domain(self, capsys):
        args = self._make_args(task="Build a crypto scanner", domain=None)
        saf.cmd_forge(args)
        conn = saf._get_conn()
        row = conn.execute("SELECT domain FROM assignments ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        assert row[0] == "crypto"

    def test_forge_prints_assignment_id(self, capsys):
        args = self._make_args()
        assignment_id = saf.cmd_forge(args)
        captured = capsys.readouterr()
        assert assignment_id in captured.out

    def test_forge_agent_uppercased(self, capsys):
        args = self._make_args(agent="bolt")
        saf.cmd_forge(args)
        conn = saf._get_conn()
        row = conn.execute("SELECT agent FROM assignments ORDER BY created_at DESC LIMIT 1").fetchone()
        conn.close()
        assert row[0] == "BOLT"

    def test_forge_multiple_assignments_unique_ids(self, capsys):
        ids = []
        for i in range(5):
            args = self._make_args(task=f"Task number {i}")
            ids.append(saf.cmd_forge(args))
        assert len(set(ids)) == 5  # All unique


# ─────────────────────────────────────────────────────────────────────────────
# QUALITY SCORING
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityScoring:
    def test_all_gates_passed_max_score(self):
        score = saf._score_quality(saf.QUALITY_GATES, "ho_test_id", "x" * 300)
        assert score == 100

    def test_no_gates_low_score(self):
        score = saf._score_quality([], "ho_test_id", "x" * 300)
        assert score <= 20  # No gates = very low

    def test_no_handoff_id_reduces_score(self):
        score_with = saf._score_quality(saf.QUALITY_GATES, "ho_test_id", "x" * 300)
        score_without = saf._score_quality(saf.QUALITY_GATES, "", "x" * 300)
        assert score_without < score_with

    def test_short_description_reduces_score(self):
        score_full = saf._score_quality(saf.QUALITY_GATES, "ho_test_id", "x" * 300)
        score_short = saf._score_quality(saf.QUALITY_GATES, "ho_test_id", "short")
        assert score_short < score_full

    def test_score_never_exceeds_100(self):
        # Even with impossible inputs, score should cap at 100
        score = saf._score_quality(saf.QUALITY_GATES * 10, "ho_valid", "x" * 1000)
        assert score <= 100

    def test_score_never_below_0(self):
        score = saf._score_quality([], "", "")
        assert score >= 0

    def test_partial_gates_intermediate_score(self):
        half_gates = saf.QUALITY_GATES[:3]
        score = saf._score_quality(half_gates, "ho_test_id", "x" * 300)
        assert 20 < score < 80


# ─────────────────────────────────────────────────────────────────────────────
# PICKUP REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

class TestPickupReport:
    def test_report_contains_handoff_id(self):
        report = saf._generate_pickup_report(
            "ho_abc123", "saf_xyz", ["TEST", "DOCS"], 85, "raw details", "notes here"
        )
        assert "ho_abc123" in report

    def test_report_contains_quality_score(self):
        report = saf._generate_pickup_report(
            "ho_abc123", "saf_xyz", ["TEST", "DOCS"], 85, "raw details", None
        )
        assert "85" in report

    def test_report_shows_passed_gates_checked(self):
        report = saf._generate_pickup_report(
            "ho_abc123", "saf_xyz", ["TEST", "DOCS"], 80, "raw", None
        )
        assert "[x] TEST" in report
        assert "[x] DOCS" in report

    def test_report_shows_failed_gates_unchecked(self):
        report = saf._generate_pickup_report(
            "ho_abc123", "saf_xyz", ["TEST"], 50, "raw", None
        )
        assert "[ ] DOCS" in report
        assert "[ ] EXAMPLES" in report

    def test_report_all_gates_present(self):
        report = saf._generate_pickup_report(
            "ho_abc123", None, [], 0, "", None
        )
        for gate in saf.QUALITY_GATES:
            assert gate in report


# ─────────────────────────────────────────────────────────────────────────────
# STATUS COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class TestStatusCommand:
    def _make_forge_args(self, agent="BOLT", task="Test task"):
        return type("Args", (), {
            "agent": agent, "task": task, "domain": "python",
            "protocol": None, "priority": "NORMAL", "from_agent": "FORGE",
            "deliverables": None, "context": None, "files": None, "criteria": None,
        })()

    def test_status_shows_all_assignments(self, capsys):
        saf.cmd_forge(self._make_forge_args(task="Task 1"))
        saf.cmd_forge(self._make_forge_args(task="Task 2"))
        args = type("Args", (), {"id": None, "agent": None})()
        saf.cmd_status(args)
        captured = capsys.readouterr()
        assert "Task 1" in captured.out or "Task" in captured.out

    def test_status_filters_by_agent(self, capsys):
        saf.cmd_forge(self._make_forge_args(agent="BOLT", task="Bolt Task"))
        saf.cmd_forge(self._make_forge_args(agent="ATLAS", task="Atlas Task"))
        args = type("Args", (), {"id": None, "agent": "BOLT"})()
        saf.cmd_status(args)
        captured = capsys.readouterr()
        assert "BOLT" in captured.out

    def test_status_no_assignments_shows_message(self, capsys):
        args = type("Args", (), {"id": None, "agent": None})()
        saf.cmd_status(args)
        captured = capsys.readouterr()
        assert "No assignments" in captured.out

    def test_status_by_id_shows_details(self, capsys):
        assignment_id = saf.cmd_forge(self._make_forge_args())
        args = type("Args", (), {"id": assignment_id, "agent": None})()
        saf.cmd_status(args)
        captured = capsys.readouterr()
        assert assignment_id in captured.out


# ─────────────────────────────────────────────────────────────────────────────
# BRIEF COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class TestBriefCommand:
    def _make_forge_args(self):
        return type("Args", (), {
            "agent": "BOLT", "task": "Build the thing", "domain": "python",
            "protocol": None, "priority": "NORMAL", "from_agent": "FORGE",
            "deliverables": None, "context": None, "files": None, "criteria": None,
        })()

    def test_brief_prints_content(self, capsys):
        assignment_id = saf.cmd_forge(self._make_forge_args())
        args = type("Args", (), {"id": assignment_id})()
        saf.cmd_brief(args)
        captured = capsys.readouterr()
        assert assignment_id in captured.out
        assert "MANDATORY" in captured.out

    def test_brief_unknown_id_exits(self, capsys):
        args = type("Args", (), {"id": "saf_nonexistent"})()
        with pytest.raises(SystemExit):
            saf.cmd_brief(args)


# ─────────────────────────────────────────────────────────────────────────────
# DOMAINS & PROTOCOLS COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

class TestInfoCommands:
    def test_domains_lists_all_domains(self, capsys):
        saf.cmd_domains(type("Args", (), {})())
        captured = capsys.readouterr()
        for domain in saf.DOMAIN_CONTEXTS:
            assert domain in captured.out

    def test_protocols_shows_all_three(self, capsys):
        saf.cmd_protocols(type("Args", (), {})())
        captured = capsys.readouterr()
        assert "hunter" in captured.out
        assert "build" in captured.out
        assert "bughunt" in captured.out

    def test_reset_message_contains_agent_name(self, capsys):
        saf.cmd_reset(type("Args", (), {"agent": "BOLT"})())
        captured = capsys.readouterr()
        assert "BOLT" in captured.out
        assert "reset" in captured.out.lower() or "standard" in captured.out.lower()


# ─────────────────────────────────────────────────────────────────────────────
# STATS COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class TestStatsCommand:
    def test_stats_on_empty_db(self, capsys):
        saf.cmd_stats(type("Args", (), {})())
        captured = capsys.readouterr()
        assert "0" in captured.out  # Total = 0

    def test_stats_after_assignments(self, capsys):
        for _ in range(3):
            saf.cmd_forge(type("Args", (), {
                "agent": "BOLT", "task": "Build something", "domain": "python",
                "protocol": None, "priority": "NORMAL", "from_agent": "FORGE",
                "deliverables": None, "context": None, "files": None, "criteria": None,
            })())
        saf.cmd_stats(type("Args", (), {})())
        captured = capsys.readouterr()
        assert "3" in captured.out


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVATE COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class TestActivateCommand:
    def test_activate_updates_status(self, capsys):
        assignment_id = saf.cmd_forge(type("Args", (), {
            "agent": "BOLT", "task": "Build something", "domain": "python",
            "protocol": None, "priority": "NORMAL", "from_agent": "FORGE",
            "deliverables": None, "context": None, "files": None, "criteria": None,
        })())
        saf.cmd_activate(type("Args", (), {"id": assignment_id})())
        conn = saf._get_conn()
        row = conn.execute("SELECT status FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        conn.close()
        assert row[0] == "active"

    def test_activate_unknown_id_exits(self, capsys):
        with pytest.raises(SystemExit):
            saf.cmd_activate(type("Args", (), {"id": "saf_nonexistent"})())


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

class TestCLIEntryPoint:
    def test_build_parser_returns_parser(self):
        parser = saf.build_parser()
        assert parser is not None

    def test_main_no_args_exits_zero(self, capsys):
        with patch("sys.argv", ["forge"]):
            with pytest.raises(SystemExit) as exc:
                saf.main()
        assert exc.value.code == 0

    def test_main_version_exits(self, capsys):
        with patch("sys.argv", ["forge", "--version"]):
            with pytest.raises(SystemExit):
                saf.main()

    def test_main_domains(self, capsys):
        with patch("sys.argv", ["forge", "domains"]):
            saf.main()
        captured = capsys.readouterr()
        assert "python" in captured.out
        assert "finance" in captured.out

    def test_main_protocols(self, capsys):
        with patch("sys.argv", ["forge", "protocols"]):
            saf.main()
        captured = capsys.readouterr()
        assert "hunter" in captured.out
        assert "build" in captured.out

    def test_main_stats(self, capsys):
        with patch("sys.argv", ["forge", "stats"]):
            saf.main()
        captured = capsys.readouterr()
        assert "STATISTICS" in captured.out

    def test_main_forge(self, capsys):
        with patch("sys.argv", [
            "forge", "forge",
            "--agent", "BOLT",
            "--task", "Build the CLI test tool",
            "--domain", "python",
        ]):
            saf.main()
        captured = capsys.readouterr()
        assert "saf_" in captured.out

    def test_main_reset(self, capsys):
        with patch("sys.argv", ["forge", "reset", "--agent", "ATLAS"]):
            saf.main()
        captured = capsys.readouterr()
        assert "ATLAS" in captured.out


# ─────────────────────────────────────────────────────────────────────────────
# END-TO-END WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndWorkflow:
    def test_full_lifecycle(self, capsys):
        """Forge → activate → pickup → verify completed status."""
        # 1. Create assignment
        forge_args = type("Args", (), {
            "agent": "BOLT",
            "task": "Build finai-sec-scanner MCP server",
            "domain": "mcp",
            "protocol": "build",
            "priority": "HIGH",
            "from_agent": "FORGE",
            "deliverables": "All 6 MCP tools, README, pytest 80%+",
            "context": "Part of FINAI Phase 1",
            "files": r"D:\BEACON_HQ\specs\SPEC_SEC.md",
            "criteria": "All tests pass, 80%+ coverage",
        })()
        assignment_id = saf.cmd_forge(forge_args)
        assert assignment_id.startswith("saf_")

        # 2. Activate
        saf.cmd_activate(type("Args", (), {"id": assignment_id})())
        conn = saf._get_conn()
        status = conn.execute("SELECT status FROM assignments WHERE id=?",
                              (assignment_id,)).fetchone()[0]
        conn.close()
        assert status == "active"

        # 3. Pickup (simulate subagent filed handoff)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Task completed successfully\nDetails here.")
            pickup_args = type("Args", (), {
                "handoff_id": "ho_20260305_190000_abc12345",
                "assignment_id": assignment_id,
                "gates": ["TEST", "DOCS", "EXAMPLES", "ERRORS", "QUALITY"],
                "notes": "Build complete, all tests pass",
            })()
            saf.cmd_pickup(pickup_args)

        conn = saf._get_conn()
        row = conn.execute("SELECT status, quality_score, handoff_id FROM assignments WHERE id=?",
                           (assignment_id,)).fetchone()
        conn.close()
        assert row[0] == "completed"
        assert row[1] is not None
        assert row[2] == "ho_20260305_190000_abc12345"

    def test_pickup_without_assignment_link(self, capsys):
        """Pickup should work even when not linked to a known assignment_id."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Handoff details here.")
            pickup_args = type("Args", (), {
                "handoff_id": "ho_20260305_190000_aabbccdd",
                "assignment_id": None,
                "gates": ["TEST"],
                "notes": None,
            })()
            saf.cmd_pickup(pickup_args)
        captured = capsys.readouterr()
        assert "ho_20260305_190000_aabbccdd" in captured.out

    def test_brief_roundtrip(self, capsys):
        """Forge creates brief → brief is readable → contains all expected sections."""
        forge_args = type("Args", (), {
            "agent": "ATLAS",
            "task": "Research Hurst exponent calculation methods",
            "domain": "finance",
            "protocol": None,  # Should auto-detect to hunter
            "priority": "NORMAL",
            "from_agent": "FORGE",
            "deliverables": "Research report with implementation recommendations",
            "context": "For use in finai-risk-engine regime detection",
            "files": None,
            "criteria": "Must include R/S analysis pseudocode",
        })()
        assignment_id = saf.cmd_forge(forge_args)

        # Read the brief back
        brief_args = type("Args", (), {"id": assignment_id})()
        saf.cmd_brief(brief_args)
        captured = capsys.readouterr()
        brief_output = captured.out

        # Verify all critical sections present
        assert "MANDATORY REQUIREMENTS" in brief_output
        assert "FINANCE SPECIALIST" in brief_output
        assert "HUNTER" in brief_output.upper()
        assert "QUALITY GATES" in brief_output
        assert "COMPLETION PROCEDURE" in brief_output
        assert "Research Hurst exponent" in brief_output
        assert "For use in finai-risk-engine" in brief_output  # context included
