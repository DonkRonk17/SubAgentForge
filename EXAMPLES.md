# SubAgentForge — Working Examples

> All examples use the `forge` CLI command (installed via `pip install -e .`).
> Each example shows the exact command + expected output.

---

## Example 1: Assign a Build Task to BOLT

**Scenario:** ATLAS (primary agent) needs to assign BOLT to build a new MCP server.

```powershell
forge forge `
  --agent BOLT `
  --task "Build finai-sec-scanner MCP server with 6 tools: ingest_filing, scan_form4, scan_8k, scan_13d, get_filings, health" `
  --domain mcp `
  --protocol build `
  --priority HIGH `
  --from-agent ATLAS `
  --deliverables "server.py, scanner.py, config.py, signals.py, tests/ (80%+ coverage), README.md, .env.example" `
  --context "Part of FINAI Phase 1 Hunting Engine. Uses EdgarTools library. Follows FastMCP architecture." `
  --criteria "All 6 tools implemented, pytest passes with 80%+ coverage, README complete"
```

**Expected output:**

```
============================================================
  SUBAGENT BRIEF GENERATED
============================================================
  Assignment ID : saf_20260305_200000_abc12345
  Agent         : BOLT
  Task          : Build finai-sec-scanner MCP server with 6 tool...
  Domain        : mcp (Model Context Protocol (MCP), FastMCP, to...)
  Protocol      : BUILD
  Priority      : HIGH
  Brief saved   : C:\Users\logan\.subagentforge\briefs\saf_20260305_200000_abc12345_BRIEF.md
============================================================

  WHAT TO DO NEXT:
  1. Copy the brief content below into your subagent prompt
  2. OR have the subagent read: C:\Users\...\BRIEF.md
  3. After completion, run: forge pickup <handoff_id>

------------------------------------------------------------
  BRIEF CONTENT (paste this into subagent):
------------------------------------------------------------

# SUBAGENT EXPERT BRIEF
## Assignment ID: saf_20260305_200000_abc12345
## Agent: BOLT
...
```

---

## Example 2: Research Task with Hunter Protocol (auto-detected)

**Scenario:** FORGE assigns ATLAS to research Half-Kelly criterion.

```powershell
forge forge `
  --agent ATLAS `
  --task "Research Half-Kelly criterion — find academic sources, best practices, and implementation examples in Python" `
  --domain finance `
  --from-agent FORGE
```

**Auto-detection:** The word "Research" triggers Hunter's Protocol automatically.

**Expected output (key lines):**

```
  Domain        : finance (quantitative finance, Half-Kelly criterion...)
  Protocol      : HUNTER
  Priority      : NORMAL
```

---

## Example 3: Bug Fix Task (Bug Hunt Protocol auto-detected)

**Scenario:** FORGE assigns BOLT to fix a failing decorator.

```powershell
forge forge `
  --agent BOLT `
  --task "Fix the safe_scan decorator in finai-crypto-scanner — missing return wrapper causes TypeError" `
  --domain python `
  --files "D:\BEACON_HQ\PROJECTS\00_ACTIVE\$$ FINAI $$\servers\finai-crypto-scanner\scanner.py"
```

**Auto-detection:** The word "Fix" triggers Bug Hunt Protocol.

**Expected output (key lines):**

```
  Protocol      : BUGHUNT
  Domain        : python (Python 3.12, async/await, pydantic v2...)
```

---

## Example 4: Pick Up a Completed Handoff

**Scenario:** BOLT reports: "Done. Handoff: ho_20260305_210000_xyz98765"

```powershell
forge pickup ho_20260305_210000_xyz98765 `
  --assignment saf_20260305_200000_abc12345 `
  --gates TEST DOCS EXAMPLES ERRORS QUALITY `
  --notes "BOLT delivered 5 of 6 tools. BRANDING gate skipped — acceptable for backend service."
```

**Expected output:**

```
============================================================
  SUBAGENT HANDOFF RECEIVED
============================================================
  Handoff ID     : ho_20260305_210000_xyz98765
  Assignment ID  : saf_20260305_200000_abc12345
  Quality Score  : 93/100
  Gates Passed   : TEST, DOCS, EXAMPLES, ERRORS, QUALITY
  Report saved   : C:\Users\logan\.subagentforge\reports\pickup_ho_20260305_210000_xyz98765.md
============================================================

  HIGH QUALITY DELIVERY: 93/100

------------------------------------------------------------
  HANDOFF DETAILS:
------------------------------------------------------------
[AgentHandoff show output here]
```

---

## Example 5: Check Status of All Assignments

```powershell
forge status
```

**Expected output:**

```
--------------------------------------------------------------------------------
  ID                             AGENT    STATUS       SCORE  TASK
--------------------------------------------------------------------------------
  saf_20260305_200000_abc12345   BOLT     completed    93     Build finai-sec-scanner MCP ser...
  saf_20260305_195000_def67890   ATLAS    active       —      Research Half-Kelly criterion —...
  saf_20260305_190000_ghi11111   FORGE    briefed      —      Design FINAI system architecture
--------------------------------------------------------------------------------
```

---

## Example 6: Filter Status by Agent

```powershell
forge status --agent BOLT
```

**Expected output:**

```
--------------------------------------------------------------------------------
  ID                             AGENT    STATUS       SCORE  TASK
--------------------------------------------------------------------------------
  saf_20260305_200000_abc12345   BOLT     completed    93     Build finai-sec-scanner MCP ser...
  saf_20260304_180000_jkl22222   BOLT     completed    78     Build finai-social-sentinel...
--------------------------------------------------------------------------------
```

---

## Example 7: View a Specific Assignment with Full Details

```powershell
forge status saf_20260305_200000_abc12345
```

**Expected output:**

```
--------------------------------------------------------------------------------
  ID                             AGENT    STATUS       SCORE  TASK
--------------------------------------------------------------------------------
  saf_20260305_200000_abc12345   BOLT     completed    93     Build finai-sec-scanner MCP ser...
--------------------------------------------------------------------------------

  DETAILS:
  Domain      : mcp
  Protocol    : build
  Brief       : C:\Users\logan\.subagentforge\briefs\saf_20260305_200000_abc12345_BRIEF.md
  Handoff ID  : ho_20260305_210000_xyz98765
  Gates       : ["TEST", "DOCS", "EXAMPLES", "ERRORS", "QUALITY"]
  Notes       : BOLT delivered 5 of 6 tools...
```

---

## Example 8: Print the Expert Brief for an Assignment

```powershell
forge brief saf_20260305_200000_abc12345
```

**Output:** Full Markdown brief content printed to stdout — the same document the subagent received. Useful for reviewing what instructions were given.

---

## Example 9: List All Available Expertise Domains

```powershell
forge domains
```

**Expected output:**

```
  AVAILABLE EXPERTISE DOMAINS
  --------------------------------------------------
  python       — Python 3.12, async/await, pydantic v2, pytest, loguru, httpx
  mcp          — Model Context Protocol (MCP), FastMCP, tool signatures, JSON-RPC
  finance      — quantitative finance, Half-Kelly criterion, circuit breakers, signal conf
  sec          — SEC EDGAR, 8-K, Form 4, 13D/G filings, EdgarTools library
  crypto       — on-chain analytics, DeFiLlama, DexScreener, whale tracking, token unlocks
  social       — PRAW Reddit API, pytrends Google Trends, mention velocity, sentiment scor
  risk         — risk management, position sizing, portfolio theory, Hurst exponent, VIX r
  trading      — algorithmic trading, Alpaca API, paper trading, order management, stop-lo
  ai           — LLM orchestration, prompt engineering, multi-agent systems, RAG
  devops       — Docker, CI/CD, pytest coverage, deployment, monitoring
  data         — pandas, SQLite, data pipelines, ETL, schema design
  general      — full-stack development, system design, software engineering best practice
```

---

## Example 10: List All Protocols and When to Use Them

```powershell
forge protocols
```

**Expected output:**

```
  AVAILABLE PROTOCOLS

  hunter    — Research, investigate, analyze, plan, audit, design
              Follows: Hunter's Protocol (Plan->Hunt->Analyze->Verify)
              Use for: Understanding, insight extraction, root cause

  build     — Build, create, implement, code, develop, write, refactor
              Follows: Build Protocol V1 (Tool-First Construction)
              Use for: Creating software, tools, scripts, systems

  bughunt   — Test, debug, fix, validate, verify, QA
              Follows: Bug Hunt Protocol (Systematic Investigation)
              Use for: Finding bugs, validating fixes, QA passes

  AUTO-DETECT based on task keywords:
    build  <- build, create, implement, code, develop, write, refactor
    hunter <- research, investigate, analyse, plan, audit, design
    bughunt <- test, debug, fix, validate, verify, qa
```

---

## Example 11: Generate Reset Instruction for a Subagent

After BOLT completes its assignment:

```powershell
forge reset --agent BOLT
```

**Expected output:**

```
============================================================
  SUBAGENT RESET INSTRUCTION
  For: BOLT
============================================================

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
- Operate as BOLT with your full capabilities

You are ready for your next assignment.
============================================================
```

---

## Example 12: View Statistics Dashboard

```powershell
forge stats
```

**Expected output:**

```
  SUBAGENTFORGE STATISTICS
  ----------------------------------------
  Total assignments : 7
  Avg quality score : 88.3/100

  BY STATUS:
    completed       5
    active          1
    briefed         1

  BY AGENT:
    BOLT            4
    ATLAS           2
    NEXUS           1
```

---

## Example 13: Mark Assignment as Active (Subagent Started)

When the subagent confirms it has read the brief and begun working:

```powershell
forge activate saf_20260305_200000_abc12345
```

**Expected output:**

```
[OK] Assignment saf_20260305_200000_abc12345 marked as ACTIVE.
```

---

## Example 14: Low Quality Warning on Pickup

When only 2 of 6 gates pass:

```powershell
forge pickup ho_20260305_220000_low99999 --gates TEST DOCS
```

**Expected output:**

```
============================================================
  SUBAGENT HANDOFF RECEIVED
============================================================
  Handoff ID     : ho_20260305_220000_low99999
  Quality Score  : 44/100
  Gates Passed   : TEST, DOCS
  Report saved   : ...
============================================================

  WARNING: Score 44/100 is below threshold.
     Review the brief and consider re-assigning the task.
```

---

## Example 15: Urgent Priority Research Task — Full Flow

**Step 1: Forge the assignment**
```powershell
forge forge `
  --agent OPUS `
  --task "Investigate QEGG dodecahedral geometry — find all published literature on quantum entangled geometric grids" `
  --domain ai `
  --protocol hunter `
  --priority URGENT `
  --from-agent FORGE `
  --deliverables "Research report (min 2000 words), source list with URLs, key findings summary, gap analysis"
```

**Step 2: Activate when OPUS starts**
```powershell
forge activate saf_YYYYMMDD_HHMMSS_xxxxxxxx
```

**Step 3: OPUS files handoff after research complete**
*(OPUS runs: `python agenthandoff.py create --to FORGE --task "COMPLETE: Investigate QEGG..." ...`)*

**Step 4: Pick up with all 6 gates**
```powershell
forge pickup ho_YYYYMMDD_HHMMSS_yyyyyyyy `
  --assignment saf_YYYYMMDD_HHMMSS_xxxxxxxx `
  --gates TEST DOCS EXAMPLES ERRORS QUALITY BRANDING
```

**Step 5: Reset OPUS**
```powershell
forge reset --agent OPUS
```

---

## Protocol Auto-Detection Examples

| Task String | Auto-Detected Protocol |
|---|---|
| "Build a REST API for..." | `build` |
| "Create a Python script..." | `build` |
| "Research the best approach to..." | `hunter` |
| "Investigate why the tests are failing..." | `hunter` |
| "Fix the memory leak in..." | `bughunt` |
| "Debug the authentication error..." | `bughunt` |
| "Test the new pipeline end-to-end..." | `bughunt` |
| "Validate all output against schema..." | `bughunt` |
| "Design the database schema for..." | `hunter` |
| "Implement the Half-Kelly criterion..." | `build` |
| "Analyze the performance bottleneck..." | `hunter` |
| "Refactor the signal processor..." | `build` |

---

## Quality Score Breakdown

| Condition | Points |
|---|---|
| Each quality gate passed (max 6) | ~14 pts each (84 pts total) |
| Handoff ID provided (ho_ prefix) | +10 pts |
| Handoff has description (>200 chars) | +6 pts |
| **Maximum possible score** | **100 pts** |

---

*SubAgentForge — Quality is not an act, it is a habit.*
*ATLAS @ Team Brain — For the Maximum Benefit of Life.*
