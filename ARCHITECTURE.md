# ARCHITECTURE.md - SubAgentForge
## Phase 3: Architecture Design per Build Protocol V1.0

**Project:** SubAgentForge - Expert Subagent Deployment & Lifecycle Manager
**Builder:** ATLAS (Team Brain Implementation Lead)
**Date:** March 5, 2026

---

## System Architecture Overview

```
Primary Agent
    |
    | forge forge --task "build X" --domain python --agent BOLT
    v
[SubAgentForge CLI]
    |
    +-- [ExpertBriefEngine]
    |       |-- Domain Profiles (12 domains: python, mcp, finance, sec, crypto,
    |       |                    social, risk, trading, ai, devops, data, general)
    |       |-- Protocol Auto-Detection (keyword → Hunter/Build/BugHunt)
    |       |-- Quality Gate Embedding (6 gates: TEST/DOCS/EXAMPLES/ERRORS/QUALITY/BRANDING)
    |       |-- AgentHandoff Command Injection
    |       +-- 01_MR.md Requirement Embedding
    |
    +-- [AssignmentDatabase (SQLite)]
    |       |-- forge.db at ~/.subagentforge/forge.db
    |       |-- assignments table: id, agent, task, domain, protocol, status, timestamps
    |       +-- Status transitions: briefed → active → completed
    |
    +-- [LifecycleManager]
            |-- forge: Creates assignment, generates brief (→ BRIEF.md)
            |-- activate: Marks assignment as active
            |-- pickup: Reads AgentHandoff output, scores quality (0-100)
            |-- status: Lists all assignments with filtering
            |-- stats: Aggregate metrics per agent/domain/protocol
            +-- reset: Clears active assignment (subagent resets to standard ops)
```

---

## Core Components

### 1. ExpertBriefEngine
**Purpose:** Generate a paste-ready expert brief for any subagent
**Input:** task description, domain, agent name, optional assignment_link
**Output:** Formatted BRIEF.md text with 7 sections

**Brief Structure:**
```
[1] EXPERT IDENTITY      - Who you are for this task
[2] TECHNICAL CONTEXT    - Domain-specific knowledge
[3] MANDATORY REQUIREMENTS - From 01_MR.md
[4] PROTOCOL             - Exact protocol to follow (auto-detected)
[5] QUALITY GATES        - 6 gates that must pass before completion
[6] COMPLETION PROCEDURE - Exact steps when task is done
[7] ESCALATION PATH      - What to do if blocked
[8] RESET INSTRUCTION    - Return to standard ops after completion
```

### 2. Protocol Auto-Detection
**Algorithm:** Keyword matching in priority order

```python
PROTOCOL_MAP = {
    "hunter":   ["research", "investigate", "analyze", "plan", "discover"],
    "bughunt":  ["debug", "fix", "test", "validate", "verify", "diagnose"],
    "build":    ["build", "create", "implement", "develop", "write", "make"],
}
```

**Priority:** bughunt > hunter > build (debug keywords must not match build)

### 3. Quality Scoring Engine
**Algorithm:** Weighted gate scoring (each gate = 16.67 points out of 100)

```python
gates = {
    "TEST":     "tests run and pass",
    "DOCS":     "README.md complete",
    "EXAMPLES": "working examples provided",
    "ERRORS":   "error handling implemented",
    "QUALITY":  "clean, organized code",
    "BRANDING": "Team Brain style applied",
}
score = (gates_passed / 6) * 100
```

### 4. AssignmentDatabase Schema
```sql
CREATE TABLE assignments (
    id          TEXT PRIMARY KEY,      -- UUID4
    agent       TEXT NOT NULL,         -- e.g. BOLT, NEXUS
    task        TEXT NOT NULL,         -- task description
    domain      TEXT NOT NULL,         -- expertise domain
    protocol    TEXT NOT NULL,         -- HUNTER/BUILD/BUGHUNT
    status      TEXT NOT NULL,         -- briefed/active/completed
    brief_path  TEXT,                  -- path to saved BRIEF.md
    handoff_id  TEXT,                  -- AgentHandoff ID on completion
    quality_score REAL,                -- 0-100 on pickup
    created_at  TEXT NOT NULL,         -- ISO 8601
    activated_at TEXT,
    completed_at TEXT
);
```

---

## Data Flow

### Forge Flow (Primary Agent → Subagent)
```
1. Primary Agent runs: forge forge --task "..." --domain python --agent BOLT
2. SubAgentForge creates UUID assignment ID
3. ExpertBriefEngine generates BRIEF.md (domain + protocol + gates)
4. Assignment saved to SQLite with status=briefed
5. BRIEF.md written to ~/.subagentforge/briefs/[ID].md
6. Primary Agent pastes BRIEF.md content to subagent (Bolt, Nexus, etc.)
7. Subagent reads brief, activates expert mode
```

### Activate Flow (Subagent Acknowledgment)
```
1. Subagent runs: forge activate [ID]
2. Status transitions: briefed → active
3. activated_at timestamp recorded
4. Confirmation displayed
```

### Completion Flow (Primary Agent Pickup)
```
1. Subagent completes task per protocol + quality gates
2. Subagent files AgentHandoff: agenthandoff complete [ID] --notes "..."
3. Primary Agent runs: forge pickup [ID] (or forge pickup --latest)
4. SubAgentForge reads AgentHandoff output
5. Quality scoring: reads gate compliance from pickup report
6. Status transitions: active → completed
7. Completion report displayed with quality score
```

---

## Error Handling Strategy

| Error Type | Strategy |
|------------|----------|
| AgentHandoff not found | Graceful fallback, pickup works without it |
| Assignment not found | Clear error with list of valid IDs |
| Invalid domain | Lists all valid domains with --help |
| SQLite locked | Retry with exponential backoff |
| Windows encoding | errors="replace" on all output, ASCII-safe format |
| Missing DATA_DIR | Auto-creates on first run |

---

## File Layout

```
SubAgentForge/
├── subagentforge.py          # Main tool (single file, stdlib only)
├── tests/
│   ├── __init__.py
│   └── test_subagentforge.py # 73 tests, 96.58% coverage
├── README.md                 # 400+ lines, comprehensive
├── EXAMPLES.md               # 15+ working examples
├── QUICK_START.txt           # Quick reference
├── BUILD_COVERAGE_PLAN.md    # Phase 1
├── BUILD_AUDIT.md            # Phase 2
├── ARCHITECTURE.md           # Phase 3 (this file)
├── BUILD_LOG.md              # Implementation decisions
├── BUILD_REPORT.md           # Phase 8 metrics
├── branding/
│   └── BRANDING_PROMPTS.md   # DALL-E prompts for logo
├── pyproject.toml            # Package config (pytest-cov threshold)
├── .gitignore
└── LICENSE                   # MIT
```

---

## Design Principles Applied

1. **Zero Dependencies:** stdlib only (argparse, sqlite3, uuid, json, pathlib, datetime)
2. **Single File:** All logic in subagentforge.py - easy to copy, inspect, modify
3. **Delta Simplicity:** Keyword matching over ML model for protocol detection
4. **Windows Safe:** ASCII-only output, utf-8 file I/O, no Unicode box drawing
5. **Graceful Degradation:** Works even if AgentHandoff is unavailable

---

*Built by ATLAS for Logan Smith / Metaphy LLC / Team Brain*
*Architecture designed for maximum reliability with minimum complexity*
