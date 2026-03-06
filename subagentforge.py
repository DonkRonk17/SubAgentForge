#!/usr/bin/env python3
"""
SubAgentForge - Expert Subagent Deployment & Lifecycle Manager
==============================================================

Transforms any AI subagent into a domain-specific expert for a single task.
Enforces 01_MR.md mandatory requirements, embeds the correct protocol
(Hunter / Build / Bug Hunt), and issues a verified AgentHandoff upon
task completion. The subagent then resets to standard operating procedures,
ready for the next assignment.

Architecture:
  Primary Agent  --forge-->  SubAgent (expert mode)
                              └- reads BRIEF.md
                              └- follows correct protocol
                              └- runs quality gates
                              └- files AgentHandoff
                 <--pickup--  Primary Agent picks up HO ID
                              └- reads completion report
                              └- verifies quality gates passed
                              └- continues orchestration

Author: ATLAS (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0
Date: March 2026
License: MIT
"""

import argparse
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

VERSION = "1.0.0"
DATA_DIR = Path.home() / ".subagentforge"
DB_PATH = DATA_DIR / "forge.db"
BRIEFS_DIR = DATA_DIR / "briefs"
REPORTS_DIR = DATA_DIR / "reports"

MR_PATH = r"D:\BEACON_HQ\01_MR.md"
HUNTER_PROTOCOL_PATH = r"D:\BEACON_HQ\00_The_Hunters_Protocol.md"
BUILD_PROTOCOL_PATH = r"D:\BEACON_HQ\00_BUILD_PROTOCOL_V1.md"
BUG_HUNT_PROTOCOL_PATH = r"D:\BEACON_HQ\00_Bug Hunt Protocol.md"
AGENTHANDOFF_PATH = r"C:\Users\logan\OneDrive\Documents\AutoProjects\AgentHandoff\agenthandoff.py"

# Task → Protocol mapping (order matters — more specific before general)
PROTOCOL_MAP = {
    # Bug Hunt protocol keywords first (some contain "build" substring, e.g. "rebuild")
    "debug": "bughunt",
    "test": "bughunt",
    "fix": "bughunt",
    "validate": "bughunt",
    "verify": "bughunt",
    "qa": "bughunt",
    # Hunter protocol keywords
    "research": "hunter",
    "investigate": "hunter",
    "analyse": "hunter",
    "analyze": "hunter",
    "plan": "hunter",
    "audit": "hunter",
    "design": "hunter",
    # Build protocol keywords
    "build": "build",
    "create": "build",
    "implement": "build",
    "code": "build",
    "develop": "build",
    "write": "build",
    "refactor": "build",
}

# Expertise domain → system context map
DOMAIN_CONTEXTS = {
    "python": "Python 3.12, async/await, pydantic v2, pytest, loguru, httpx",
    "mcp": "Model Context Protocol (MCP), FastMCP, tool signatures, JSON-RPC",
    "finance": "quantitative finance, Half-Kelly criterion, circuit breakers, signal confluence",
    "sec": "SEC EDGAR, 8-K, Form 4, 13D/G filings, EdgarTools library",
    "crypto": "on-chain analytics, DeFiLlama, DexScreener, whale tracking, token unlocks",
    "social": "PRAW Reddit API, pytrends Google Trends, mention velocity, sentiment scoring",
    "risk": "risk management, position sizing, portfolio theory, Hurst exponent, VIX regimes",
    "trading": "algorithmic trading, Alpaca API, paper trading, order management, stop-loss",
    "ai": "LLM orchestration, prompt engineering, multi-agent systems, RAG",
    "devops": "Docker, CI/CD, pytest coverage, deployment, monitoring",
    "data": "pandas, SQLite, data pipelines, ETL, schema design",
    "general": "full-stack development, system design, software engineering best practices",
}

QUALITY_GATES = [
    "TEST",       # Code/output executes without errors
    "DOCS",       # Clear instructions, README, comments
    "EXAMPLES",   # Working examples with expected output
    "ERRORS",     # Edge cases covered, graceful failures
    "QUALITY",    # Clean, organized, professional
    "BRANDING",   # Consistent Team Brain style
]

KNOWN_AGENTS = [
    "FORGE", "ATLAS", "CLIO", "NEXUS", "BOLT", "IRIS",
    "PORTER", "OPUS", "LAIA", "GEMINI", "GPT5", "ANY",
]

# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------

def _init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            task TEXT NOT NULL,
            domain TEXT NOT NULL,
            protocol TEXT NOT NULL,
            priority TEXT NOT NULL,
            from_agent TEXT,
            status TEXT NOT NULL DEFAULT 'briefed',
            brief_path TEXT,
            handoff_id TEXT,
            report_path TEXT,
            quality_score INTEGER,
            gates_passed TEXT,
            created_at TEXT NOT NULL,
            activated_at TEXT,
            completed_at TEXT,
            notes TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent ON assignments(agent);
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON assignments(status);
    """)
    conn.commit()
    conn.close()


def _get_conn():
    _init_db()
    return sqlite3.connect(DB_PATH)


def _hr(char="-", width=60) -> str:
    """Return a horizontal rule safe for Windows terminals."""
    return char * width


def _gen_id() -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    uid = str(uuid.uuid4())[:8]
    return f"saf_{ts}_{uid}"


# -----------------------------------------------------------------------------
# PROTOCOL DETECTION
# -----------------------------------------------------------------------------

def detect_protocol(task: str) -> str:
    """Detect which protocol to apply based on task keywords (case-insensitive)."""
    task_lower = task.lower()
    for keyword, protocol in PROTOCOL_MAP.items():
        if keyword.lower() in task_lower:
            return protocol
    return "build"  # default to build protocol


def detect_domain(task: str, domain: Optional[str] = None) -> str:
    """Detect expertise domain from task or explicit override."""
    if domain and domain.lower() in DOMAIN_CONTEXTS:
        return domain.lower()
    task_lower = task.lower()
    for d in DOMAIN_CONTEXTS:
        if d in task_lower:
            return d
    return "general"


# -----------------------------------------------------------------------------
# BRIEF GENERATION
# -----------------------------------------------------------------------------

def generate_brief(
    assignment_id: str,
    agent: str,
    task: str,
    domain: str,
    protocol: str,
    priority: str,
    from_agent: str,
    deliverables: Optional[str] = None,
    context: Optional[str] = None,
    files: Optional[str] = None,
    acceptance_criteria: Optional[str] = None,
) -> str:
    """Generate the expert BRIEF.md that programs the subagent."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    domain_ctx = DOMAIN_CONTEXTS.get(domain, DOMAIN_CONTEXTS["general"])

    protocol_instructions = {
        "hunter": f"""## MANDATORY PROTOCOL: HUNTER'S PROTOCOL
Read and follow completely: `{HUNTER_PROTOCOL_PATH}`

You are required to execute the full Hunter's Protocol for this task:
- PHASE 0: Frame the question — what exactly are you hunting for?
- PHASE 1: Surface scan — broad sweep of available information
- PHASE 2: Deep dive — extract root causes, not symptoms
- PHASE 3: Cross-reference — verify every finding against source material
- PHASE 4: Synthesis — produce structured, actionable insights
- PHASE 5: Verify — confirm conclusions hold under scrutiny

DO NOT skip any phase. DO NOT present symptoms as root causes.
""",
        "build": f"""## MANDATORY PROTOCOL: BUILD PROTOCOL V1
Read and follow completely: `{BUILD_PROTOCOL_PATH}`

You are required to execute the full Build Protocol for this task:
- PHASE 0: Existing solutions recon — search before building
- PHASE 1: Tool inventory — identify every tool available
- PHASE 2: Architecture design — plan before coding
- PHASE 3: Implementation — build with all tools, document as you go
- PHASE 4: Testing — pytest, minimum 80% coverage (90% for safety-critical)
- PHASE 5: Documentation — README, examples, edge cases
- PHASE 6: Integration — sync to Memory Core if team-relevant

DO NOT skip any phase. DO NOT deliver untested code.
""",
        "bughunt": f"""## MANDATORY PROTOCOL: BUG HUNT PROTOCOL
Read and follow completely: `{BUG_HUNT_PROTOCOL_PATH}`

You are required to execute the full Bug Hunt Protocol for this task:
- PHASE 0: Reproduce the bug — confirm you can trigger it reliably
- PHASE 1: Isolate — narrow to smallest reproducible case
- PHASE 2: Root cause analysis — find WHY, not just WHAT
- PHASE 3: Fix — implement the correct solution
- PHASE 4: Verify fix — confirm bug is resolved, no regressions
- PHASE 5: Test coverage — ensure the bug cannot recur undetected
- PHASE 6: Document — explain what happened and why

DO NOT mark bugs as fixed until verified. DO NOT fix symptoms.
""",
    }

    gates_checklist = "\n".join(
        f"- [ ] **{g}** — {'Code/output executes without errors (100%)' if g=='TEST' else 'Clear instructions, README, comments (Complete)' if g=='DOCS' else 'Working examples with expected output (Provided)' if g=='EXAMPLES' else 'Edge cases covered, graceful failures (Robust)' if g=='ERRORS' else 'Clean, organized, professional (Standards met)' if g=='QUALITY' else 'Consistent Team Brain style (Applied)'}"
        for g in QUALITY_GATES
    )

    deliverables_section = f"""## DELIVERABLES REQUIRED
{deliverables}
""" if deliverables else """## DELIVERABLES REQUIRED
_(Define exactly what outputs are expected. Do not consider the task complete until all deliverables exist.)_
"""

    criteria_section = f"""## ACCEPTANCE CRITERIA
{acceptance_criteria}
""" if acceptance_criteria else ""

    context_section = f"""## CONTEXT & BACKGROUND
{context}
""" if context else ""

    files_section = f"""## KEY FILES & PATHS
{files}
""" if files else ""

    brief = f"""# SUBAGENT EXPERT BRIEF
## Assignment ID: {assignment_id}
## Agent: {agent}
## Assigned By: {from_agent}
## Date: {now}
## Priority: {priority}

---

## ⚠️ MANDATORY REQUIREMENTS — READ FIRST
Read completely before doing anything: `{MR_PATH}`

This is not optional. All tasks require 100% adherence to:
- Follow instructions 100%
- Use subagents for appropriate sub-tasks
- Research before acting
- Plan and phase all tasks
- Complete ALL phases and ALL tasks to 100%
- Apply the correct protocol (specified below)

---

## YOUR EXPERT IDENTITY FOR THIS ASSIGNMENT

You are operating as a **{domain.upper()} SPECIALIST** for this task.

Your expertise domain context:
> {domain_ctx}

You are NOT a general-purpose assistant for this assignment.
You are a focused expert. Every decision, every line of output,
every recommendation must come from the perspective of someone
with deep expertise in: **{domain}**.

Think like an expert. Research like an expert. Deliver like an expert.

---

## ASSIGNMENT

**Task:** {task}

**Priority:** {priority}

{context_section}
{files_section}
{deliverables_section}
{criteria_section}

---

{protocol_instructions.get(protocol, protocol_instructions["build"])}

---

## MANDATORY QUALITY GATES

Before filing your AgentHandoff, ALL 6 gates must pass:

{gates_checklist}

**DO NOT file the handoff until every gate has a checkmark.**
Self-verify each gate. If you are uncertain whether a gate passes, it does not pass.

---

## SUBAGENT OPERATING RULES

1. **Work autonomously.** Do not stop for unnecessary confirmations.
2. **Only pause** for Level 3 decisions: major architectural changes, budget decisions, genuinely unclear requirements that block all progress.
3. **Recovery over failure.** If something breaks, fix it. Document what happened.
4. **Document as you go.** Do not defer documentation to the end.
5. **Use subagents** for parallelizable sub-tasks when appropriate.
6. **Verify before reporting.** Do not claim completion without proof.

---

## COMPLETION PROCEDURE (MANDATORY — DO NOT SKIP)

When ALL quality gates pass and ALL deliverables exist:

### Step 1 — Self-verification checklist
Answer each question honestly:
- [ ] Have I completed 100% of the assigned task?
- [ ] Did I follow the mandatory protocol from beginning to end?
- [ ] Do all deliverables exist and work as specified?
- [ ] Have all 6 quality gates passed?
- [ ] Is my documentation clear enough for a stranger to understand?

### Step 2 — File your AgentHandoff
Run this command exactly:
```
python "{AGENTHANDOFF_PATH}" create \\
  --to {from_agent} \\
  --task "COMPLETE: {task[:80]}" \\
  --description "[Write a 2-3 sentence summary: what you built/found, key decisions made, any caveats or follow-up items for the primary agent]" \\
  --priority {priority} \\
  --files "[comma-separated list of key output files]"
```

Record the handoff ID that is printed (format: `ho_YYYYMMDD_HHMMSS_xxxxxxxx`).

### Step 3 — Report back to primary agent
After filing the handoff, send this message to {from_agent}:

```
SUBAGENT COMPLETION REPORT
Assignment: {assignment_id}
Task: {task[:80]}
Handoff ID: [YOUR HO ID HERE]
Quality Gates: [list which passed]
Key Outputs: [list files/deliverables created]
Notes: [any issues, caveats, or recommended next steps]
```

### Step 4 — Reset to standard operating procedures
After reporting, you are released from expert mode.
Reset to your standard Team Brain operating procedures.
You are available for the next assignment from your primary agent.

---

## ESCALATION PATH

If you encounter a blocking issue that prevents completion:
1. Document exactly what is blocking you (error, missing info, decision needed)
2. File an INCOMPLETE AgentHandoff with `--task "BLOCKED: {task[:60]}..."` 
3. Include the blocker details in --description
4. Report the handoff ID to {from_agent} immediately
5. Do NOT silently fail or produce partial output without flagging it

---

*SubAgentForge v{VERSION} | Brief generated: {now}*
*For the Maximum Benefit of Life. One World. One Family. One Love.*
"""
    return brief


# -----------------------------------------------------------------------------
# COMMANDS
# -----------------------------------------------------------------------------

def cmd_forge(args):
    """Create a new expert assignment and generate the subagent brief."""
    assignment_id = _gen_id()
    protocol = args.protocol or detect_protocol(args.task)
    domain = detect_domain(args.task, args.domain)
    priority = args.priority or "NORMAL"
    from_agent = args.from_agent or os.environ.get("AGENT_NAME", "PRIMARY")
    agent = args.agent.upper()

    brief_content = generate_brief(
        assignment_id=assignment_id,
        agent=agent,
        task=args.task,
        domain=domain,
        protocol=protocol,
        priority=priority,
        from_agent=from_agent,
        deliverables=args.deliverables,
        context=args.context,
        files=args.files,
        acceptance_criteria=args.criteria,
    )

    # Save brief file
    brief_path = BRIEFS_DIR / f"{assignment_id}_BRIEF.md"
    brief_path.write_text(brief_content, encoding="utf-8")

    # Store in DB
    now = datetime.now(UTC).isoformat()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO assignments
        (id, agent, task, domain, protocol, priority, from_agent,
         status, brief_path, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (assignment_id, agent, args.task, domain, protocol, priority,
          from_agent, "briefed", str(brief_path), now))
    conn.commit()
    conn.close()

    # Output
    print(f"\n{'='*60}")
    print(f"  SUBAGENT BRIEF GENERATED")
    print(f"{'='*60}")
    print(f"  Assignment ID : {assignment_id}")
    print(f"  Agent         : {agent}")
    print(f"  Task          : {args.task[:60]}{'...' if len(args.task)>60 else ''}")
    print(f"  Domain        : {domain} ({DOMAIN_CONTEXTS[domain][:50]}...)")
    print(f"  Protocol      : {protocol.upper()}")
    print(f"  Priority      : {priority}")
    print(f"  Brief saved   : {brief_path}")
    print(f"{'='*60}")
    print()
    print(f"  WHAT TO DO NEXT:")
    print(f"  1. Copy the brief content below into your subagent prompt")
    print(f"  2. OR have the subagent read: {brief_path}")
    print(f"  3. After completion, run: forge pickup <handoff_id>")
    print()
    print(f"{'-'*60}")
    print(f"  BRIEF CONTENT (paste this into subagent):")
    print(f"{'-'*60}")
    print()
    print(brief_content.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))

    return assignment_id


def cmd_activate(args):
    """Mark an assignment as active (subagent has started)."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM assignments WHERE id=?", (args.id,)).fetchone()
    if not row:
        print(f"[ERROR] Assignment {args.id} not found.")
        sys.exit(1)
    now = datetime.now(UTC).isoformat()
    conn.execute("UPDATE assignments SET status='active', activated_at=? WHERE id=?",
                 (now, args.id))
    conn.commit()
    conn.close()
    print(f"[OK] Assignment {args.id} marked as ACTIVE.")


def cmd_pickup(args):
    """Pick up a completed subagent handoff — verify quality and record it."""
    handoff_id = args.handoff_id
    assignment_id = args.assignment_id

    # Try to get AgentHandoff details
    ho_info = {}
    try:
        result = subprocess.run(
            [sys.executable, AGENTHANDOFF_PATH, "show", handoff_id],
            capture_output=True, text=True
        )
        ho_info["raw"] = result.stdout
    except Exception as e:
        ho_info["raw"] = f"(AgentHandoff lookup failed: {e})"

    # Score the handoff
    gates_passed = args.gates or []
    quality_score = _score_quality(gates_passed, handoff_id, ho_info.get("raw", ""))

    # Update assignment if linked
    if assignment_id:
        conn = _get_conn()
        row = conn.execute("SELECT id FROM assignments WHERE id=?", (assignment_id,)).fetchone()
        if row:
            now = datetime.now(UTC).isoformat()
            conn.execute("""
                UPDATE assignments
                SET status='completed', handoff_id=?, quality_score=?,
                    gates_passed=?, completed_at=?, notes=?
                WHERE id=?
            """, (handoff_id, quality_score,
                  json.dumps(gates_passed),
                  now,
                  args.notes or "",
                  assignment_id))
            conn.commit()
        conn.close()

    # Save pickup report
    report_content = _generate_pickup_report(
        handoff_id=handoff_id,
        assignment_id=assignment_id,
        gates_passed=gates_passed,
        quality_score=quality_score,
        ho_raw=ho_info.get("raw", ""),
        notes=args.notes,
    )
    report_path = REPORTS_DIR / f"pickup_{handoff_id}.md"
    report_path.write_text(report_content, encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  SUBAGENT HANDOFF RECEIVED")
    print(f"{'='*60}")
    print(f"  Handoff ID     : {handoff_id}")
    if assignment_id:
        print(f"  Assignment ID  : {assignment_id}")
    print(f"  Quality Score  : {quality_score}/100")
    print(f"  Gates Passed   : {', '.join(gates_passed) if gates_passed else '(not specified)'}")
    print(f"  Report saved   : {report_path}")
    print(f"{'='*60}")

    if quality_score < 70:
        print(f"\n  ⚠️  QUALITY WARNING: Score {quality_score}/100 is below threshold.")
        print(f"     Review the brief and consider re-assigning the task.")
    elif quality_score >= 90:
        print(f"\n  ✅  HIGH QUALITY DELIVERY: {quality_score}/100")

    # Show AgentHandoff details
    if ho_info.get("raw"):
        print(f"\n{'-'*60}")
        print(f"  HANDOFF DETAILS:")
        print(f"{'-'*60}")
        print(ho_info["raw"])


def _score_quality(gates_passed: list, handoff_id: str, ho_raw: str) -> int:
    """Calculate quality score from gates and handoff content."""
    # Base score from quality gates (each gate = ~14 points, 6 gates = ~84)
    gate_score = round((len(gates_passed) / len(QUALITY_GATES)) * 84)

    # Bonus: handoff was actually filed (+10)
    handoff_bonus = 10 if handoff_id and handoff_id.startswith("ho_") else 0

    # Bonus: handoff has description (+6)
    description_bonus = 6 if len(ho_raw) > 200 else 0

    total = min(100, gate_score + handoff_bonus + description_bonus)
    return total


def _generate_pickup_report(
    handoff_id: str,
    assignment_id: Optional[str],
    gates_passed: list,
    quality_score: int,
    ho_raw: str,
    notes: Optional[str],
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    gates_status = "\n".join(
        f"- [{'x' if g in gates_passed else ' '}] {g}"
        for g in QUALITY_GATES
    )
    return f"""# SUBAGENT PICKUP REPORT
## Handoff ID: {handoff_id}
## Assignment ID: {assignment_id or 'N/A'}
## Picked up: {now}
## Quality Score: {quality_score}/100

---

## Quality Gates
{gates_status}

---

## Notes
{notes or '(none)'}

---

## Handoff Details
{ho_raw}
"""


def cmd_status(args):
    """Show status of all assignments or a specific one."""
    conn = _get_conn()
    if args.id:
        rows = conn.execute(
            "SELECT * FROM assignments WHERE id=?", (args.id,)
        ).fetchall()
    elif args.agent:
        rows = conn.execute(
            "SELECT * FROM assignments WHERE agent=? ORDER BY created_at DESC",
            (args.agent.upper(),)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM assignments ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    conn.close()

    if not rows:
        print("No assignments found.")
        return

    cols = [
        "id", "agent", "task", "domain", "protocol", "priority",
        "from_agent", "status", "brief_path", "handoff_id", "report_path",
        "quality_score", "gates_passed", "created_at", "activated_at",
        "completed_at", "notes"
    ]

    print(f"\n{'-'*80}")
    print(f"  {'ID':<30} {'AGENT':<8} {'STATUS':<12} {'SCORE':<6} {'TASK'}")
    print(f"{'-'*80}")
    for row in rows:
        d = dict(zip(cols, row))
        task_short = d["task"][:40] + "..." if len(d["task"]) > 40 else d["task"]
        score = str(d["quality_score"]) if d["quality_score"] else "—"
        print(f"  {d['id']:<30} {d['agent']:<8} {d['status']:<12} {score:<6} {task_short}")
    print(f"{'-'*80}")

    if args.id and rows:
        d = dict(zip(cols, rows[0]))
        print(f"\n  DETAILS:")
        print(f"  Domain      : {d['domain']}")
        print(f"  Protocol    : {d['protocol']}")
        print(f"  Brief       : {d['brief_path']}")
        if d['handoff_id']:
            print(f"  Handoff ID  : {d['handoff_id']}")
        if d['gates_passed']:
            print(f"  Gates       : {d['gates_passed']}")
        if d['notes']:
            print(f"  Notes       : {d['notes']}")


def cmd_brief(args):
    """Print the brief for an assignment."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT brief_path, agent, task FROM assignments WHERE id=?", (args.id,)
    ).fetchone()
    conn.close()
    if not row:
        print(f"[ERROR] Assignment {args.id} not found.")
        sys.exit(1)
    brief_path = Path(row[0])
    if not brief_path.exists():
        print(f"[ERROR] Brief file not found: {brief_path}")
        sys.exit(1)
    print(brief_path.read_text(encoding="utf-8"))


def cmd_domains(args):
    """List all available expertise domains."""
    print(f"\n  AVAILABLE EXPERTISE DOMAINS")
    print(f"  {'-'*50}")
    for domain, ctx in DOMAIN_CONTEXTS.items():
        print(f"  {domain:<12} — {ctx[:60]}")
    print()


def cmd_protocols(args):
    """List all available protocols and when to use them."""
    print(f"""
  AVAILABLE PROTOCOLS

  hunter    — Research, investigate, analyze, plan, audit, design
              Follows: Hunter's Protocol (Plan→Hunt→Analyze→Verify)
              Use for: Understanding, insight extraction, root cause

  build     — Build, create, implement, code, develop, write, refactor
              Follows: Build Protocol V1 (Tool-First Construction)
              Use for: Creating software, tools, scripts, systems

  bughunt   — Test, debug, fix, validate, verify, QA
              Follows: Bug Hunt Protocol (Systematic Investigation)
              Use for: Finding bugs, validating fixes, QA passes

  AUTO-DETECT based on task keywords:
    build ← build, create, implement, code, develop, write, refactor
    hunter ← research, investigate, analyse, plan, audit, design
    bughunt ← test, debug, fix, validate, verify, qa
""")


def cmd_stats(args):
    """Show assignment statistics."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    by_status = conn.execute(
        "SELECT status, COUNT(*) FROM assignments GROUP BY status"
    ).fetchall()
    by_agent = conn.execute(
        "SELECT agent, COUNT(*) FROM assignments GROUP BY agent ORDER BY COUNT(*) DESC LIMIT 10"
    ).fetchall()
    avg_score = conn.execute(
        "SELECT AVG(quality_score) FROM assignments WHERE quality_score IS NOT NULL"
    ).fetchone()[0]
    conn.close()

    print(f"\n  SUBAGENTFORGE STATISTICS")
    print(f"  {'-'*40}")
    print(f"  Total assignments : {total}")
    print(f"  Avg quality score : {avg_score:.1f}/100" if avg_score else "  Avg quality score : —")
    print()
    print(f"  BY STATUS:")
    for status, count in by_status:
        print(f"    {status:<15} {count}")
    print()
    print(f"  BY AGENT:")
    for agent, count in by_agent:
        print(f"    {agent:<15} {count}")
    print()


def cmd_reset(args):
    """Generate a reset message to tell the subagent to return to standard ops."""
    agent = args.agent.upper()
    print(f"""
{'='*60}
  SUBAGENT RESET INSTRUCTION
  For: {agent}
{'='*60}

Your expert assignment is complete. You are now released from
expert mode for that task.

Return to your standard Team Brain operating procedures:
- Resume your normal agent profile and responsibilities
- You are available for the next task from your primary agent
- All domain-specific constraints from the previous brief are lifted
- You retain the knowledge gained, but your behavior is no longer
  constrained to that specific domain or protocol

Standard protocols resume:
- Follow 01_MR.md for all future tasks
- Apply Hunter / Build / Bug Hunt as appropriate to each task
- Operate as {agent} with your full capabilities

You are ready for your next assignment.
{'='*60}
""")


# -----------------------------------------------------------------------------
# CLI PARSER
# -----------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="forge",
        description="SubAgentForge — Expert Subagent Deployment & Lifecycle Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(f"""
Examples:
  forge forge --agent BOLT --task "Build finai-sec-scanner MCP server" --domain mcp --deliverables "All 6 MCP tools, pytest 80%+ coverage, README"
  forge forge --agent ATLAS --task "Research Half-Kelly criterion" --domain finance --protocol hunter
  forge forge --agent BOLT --task "Fix safe_scan decorator bug" --domain python --protocol bughunt
  forge pickup ho_20260305_abc123 --assignment saf_20260305_def456 --gates TEST DOCS EXAMPLES
  forge status
  forge status --agent BOLT
  forge brief saf_20260305_abc123
  forge domains
  forge protocols
  forge reset --agent BOLT

Protocol auto-detection:
  "build X"     → Build Protocol V1
  "research X"  → Hunter's Protocol
  "fix X"       → Bug Hunt Protocol

For more: https://github.com/DonkRonk17/SubAgentForge
        """)
    )
    parser.add_argument("--version", "-v", action="version", version=f"SubAgentForge {VERSION}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # forge
    p_forge = sub.add_parser("forge", help="Create expert assignment + generate brief")
    p_forge.add_argument("--agent", "-a", required=True, help="Target subagent (e.g. BOLT, ATLAS)")
    p_forge.add_argument("--task", "-t", required=True, help="Task description (be specific)")
    p_forge.add_argument("--domain", "-d", help=f"Expertise domain: {', '.join(DOMAIN_CONTEXTS.keys())}")
    p_forge.add_argument("--protocol", "-p", choices=["hunter", "build", "bughunt"], help="Override protocol (default: auto-detect from task)")
    p_forge.add_argument("--priority", choices=["LOW", "NORMAL", "HIGH", "URGENT"], default="NORMAL")
    p_forge.add_argument("--from-agent", help="Your agent name (default: env AGENT_NAME)")
    p_forge.add_argument("--deliverables", help="Explicit list of required deliverables")
    p_forge.add_argument("--context", "-c", help="Background context for the subagent")
    p_forge.add_argument("--files", help="Key files/paths (comma-separated)")
    p_forge.add_argument("--criteria", help="Acceptance criteria (what done looks like)")

    # activate
    p_act = sub.add_parser("activate", help="Mark assignment as active")
    p_act.add_argument("id", help="Assignment ID (saf_...)")

    # pickup
    p_pick = sub.add_parser("pickup", help="Pick up a completed subagent handoff")
    p_pick.add_argument("handoff_id", help="AgentHandoff ID (ho_...)")
    p_pick.add_argument("--assignment", dest="assignment_id", help="Link to assignment ID (saf_...)")
    p_pick.add_argument("--gates", nargs="+", choices=QUALITY_GATES, help="Quality gates that passed")
    p_pick.add_argument("--notes", help="Notes from review")

    # status
    p_status = sub.add_parser("status", help="Show assignment status")
    p_status.add_argument("id", nargs="?", help="Specific assignment ID")
    p_status.add_argument("--agent", "-a", help="Filter by agent")

    # brief
    p_brief = sub.add_parser("brief", help="Print the brief for an assignment")
    p_brief.add_argument("id", help="Assignment ID (saf_...)")

    # domains
    sub.add_parser("domains", help="List all expertise domains")

    # protocols
    sub.add_parser("protocols", help="List protocols and when to use them")

    # stats
    sub.add_parser("stats", help="Show statistics")

    # reset
    p_reset = sub.add_parser("reset", help="Generate subagent reset instruction")
    p_reset.add_argument("--agent", "-a", required=True, help="Agent to reset")

    return parser


def main():
    _init_db()
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "forge": cmd_forge,
        "activate": cmd_activate,
        "pickup": cmd_pickup,
        "status": cmd_status,
        "brief": cmd_brief,
        "domains": cmd_domains,
        "protocols": cmd_protocols,
        "stats": cmd_stats,
        "reset": cmd_reset,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
