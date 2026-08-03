# SCIENTIFIC DIRECTOR — GOVERNANCE MODEL
## Research Classification, Approval Protocol, and Boundary Rules

**Status:** FROZEN  
**Phase:** 0 — Architecture Design  
**Date:** 2026-08-03

---

## PART 5 — Governance Levels

### 5.1 Classification Overview

All ARS research activities are classified into two governance classes before execution. The classification is determined at study planning time (Step 5 of the decision flow) and is immutable — a Class A study may not be reclassified to Class B post-execution to avoid retroactive approval.

```
┌────────────────────────────────────────────────────────────────┐
│  CLASS A — SAFE                                                 │
│  Automatic after one-time policy approval                       │
│  Zero live system impact                                        │
│  Runs at TaskQueue Priority.LOW                                 │
│  Writes only to data/ars_*.json                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  CLASS B — REQUIRES EXPLICIT APPROVAL                          │
│  Per-study human approval mandatory                             │
│  Results require second human review before integration        │
│  No automation of Class B output into live system              │
└────────────────────────────────────────────────────────────────┘
```

---

### 5.2 Class A — Safe Research (Automatic)

**Definition:** A study is Class A if and only if ALL of the following are true:

1. It reads only from: `data/replay.db`, `data/study*.json`, `data/ars_*.json`, `data/learning_db.json`, `data/strategy_performance.json`, `data/discovered_edges.json`, `data/regime_probability_history.json`
2. It writes only to: `data/ars_study_*.json`, `data/ars_knowledge_base.json`, `data/ars_hypothesis_registry.json`, `data/ars_research_schedule.json`, `data/ars_proposals/RESEARCH_REPORT_*.md`
3. It does NOT modify any live trading parameter, threshold, weight, or strategy
4. It does NOT activate or deactivate any strategy
5. It does NOT require communication with the broker (Dhan/yfinance only for historical data)
6. It runs asynchronously at TaskQueue Priority.LOW

**Class A Activities:**

| Activity | Module Used | Output |
|---|---|---|
| Historical replay analysis | `historical_replay.py` | Feature/outcome dataset |
| Pattern mining on replay.db | `edge_discovery/pattern_miner.py` | Pattern candidates (not yet live) |
| DNA discovery (DT analysis) | `study002a_pipeline.py` wrapped | DNA pattern JSON |
| Feature importance analysis | `autonomous_research/statistics.py` | Feature ranking report |
| Cluster analysis | `autonomous_research/cluster_analysis.py` | Cluster JSON |
| Decile/quantile analysis | `autonomous_research/statistics.py` | Decile report |
| Walk-forward validation (offline) | `performance/walk_forward_tester.py` | WFT results |
| Monte Carlo simulation (offline) | `market_simulation/simulation_engine.py` | MC report |
| Cross-market test (offline) | `validation_engine/cross_market_test.py` | Cross-market results |
| Knowledge synthesis | `autonomous_research/knowledge_synthesizer.py` | ars_knowledge_base.json update |
| Research roadmap update | `autonomous_research/research_director.py` | Roadmap JSON update |
| Hypothesis registration | `autonomous_research/hypothesis_registry.py` | Registry JSON update |
| Research report generation | `autonomous_research/report_generator.py` | Markdown report |
| Gap detection | `autonomous_research/gap_detector.py` | Gap list |
| Regime performance attribution (read-only) | `performance/regime_performance_tracker.py` | Attribution report |
| Study result quality assessment | `autonomous_research/evidence_validator.py` | Quality report |

**One-Time Policy Approval Required:**

Before the first ARS cycle runs, a human must explicitly approve the Class A policy statement. This approval is stored in `data/ars_proposals/CLASS_A_POLICY_APPROVED.md`. After that, all Class A studies run without per-study approval.

---

### 5.3 Class B — Requires Explicit Approval

**Definition:** A study is Class B if ANY of the following is true:

1. Its result may lead to activation of a new strategy in live trading
2. Its result may change any threshold, weight, or parameter in a live module
3. It tests a modification to an existing module's behaviour
4. It involves live market data outside of read-only price feeds
5. Its result may update `evolved_strategies.json` or `learning_db.json`
6. Its result proposes architecture changes
7. It involves capital allocation decisions

**Class B Activities:**

| Activity | Why Class B | Human Gate Trigger |
|---|---|---|
| New strategy activation | Enters live trading pipeline | PROPOSAL + STUDY_RESULT review |
| Parameter change proposal (e.g., raise WR gate from 35% to 40%) | Modifies live behaviour | PROPOSAL + STUDY_RESULT review |
| Evolved strategy parameter tuning | Touches evolved_strategies.json | PROPOSAL + STUDY_RESULT review |
| Debate agent weight adjustment proposal | Touches debate_system weights | PROPOSAL review only (no auto-apply) |
| Decision engine threshold adjustment proposal | Touches decision_ai thresholds | PROPOSAL review only |
| Live trading experiment | Any real-money or paper-money execution | PROPOSAL + explicit trade approval |
| Architecture integration proposal | Wires ARS component into live cycle | PROPOSAL + code review |
| LearningEngine trigger callback addition | Modifies learning_system | PROPOSAL + code review |

---

### 5.4 Approval Protocol (Class B)

```
STEP 1 — GENERATE PROPOSAL
  Scientific Director generates:
  data/ars_proposals/PROPOSAL_{YYYYMMDD}_{topic_slug}.md
  
  Proposal must contain:
    - Hypothesis under test
    - Study design (data, method, validation)
    - Expected outcome and impact on live system
    - Risk assessment (what breaks if finding is wrong?)
    - Rollback plan (how to undo if live integration fails)
    - Governance class justification
    - Estimated study duration and compute cost

STEP 2 — PUBLISH EVENT
  EventBus.publish("APPROVAL_REQUIRED", proposal_path)
  Telegram notification to operator (if bot running)

STEP 3 — HUMAN REVIEW
  Human reads PROPOSAL_*.md
  Human creates EITHER:
    data/ars_proposals/APPROVED_{same_slug}.md   → contains "APPROVED" + reviewer name + date
    data/ars_proposals/REJECTED_{same_slug}.md   → contains rejection reason

STEP 4 — SCIENTIFIC DIRECTOR POLLS
  ScientificDirector.check_approval(proposal_id):
    If APPROVED_*.md found  → proceed to execution
    If REJECTED_*.md found  → mark hypothesis DEFERRED; log reason
    If neither found        → do NOT proceed; re-notify after 24h

STEP 5 — EXECUTION (only after approval)
  Study runs under the same mechanisms as Class A
  But classified internally as "APPROVED_CLASS_B"

STEP 6 — RESULT REVIEW
  On study completion:
    Generate STUDY_RESULT_{slug}.md
    EventBus.publish("CLASS_B_RESULT_READY", result_path)
    Telegram notification to operator

  Human reviews STUDY_RESULT_*.md
  Human creates EITHER:
    data/ars_proposals/INTEGRATE_{slug}.md   → approved for live integration
    data/ars_proposals/ARCHIVE_{slug}.md     → finding noted but not integrated

STEP 7 — INTEGRATION (only after Step 6 approval)
  Scientific Director executes integration only after INTEGRATE_*.md exists
  Integration itself may require a code change → follows ARCHITECTURE.md deploy pipeline
```

---

### 5.5 Governance Boundary Rules

**These rules are absolute. No exception, no override, no "urgent case" bypass.**

| Rule | Statement |
|---|---|
| **G-01** | A Class B study that runs without an APPROVED_*.md file is a governance violation. |
| **G-02** | Scientific Director may never write to: `evolved_strategies.json`, `learning_db.json`, `strategy_performance.json`, `data/replay.db`, `data/paper_trades.csv`, `data/control_tower.db`. |
| **G-03** | Scientific Director may never call: `ExecutionEngine.place_order()`, `RiskGuardian` mutating methods, `DecisionEngine.approve()`, or any broker API write methods. |
| **G-04** | Research tasks submitted to TaskQueue must use Priority.LOW. Priority.CRITICAL and Priority.HIGH are reserved for live trading operations. |
| **G-05** | Research tasks must not run during market hours (09:15–15:30 IST) unless TaskQueue confirms no CRITICAL/HIGH tasks are queued. |
| **G-06** | All Class A findings that propose live system guidance must be published as GUIDANCE_PROPOSAL_*.md and await human review before integration. |
| **G-07** | Scientific Director must never self-approve. The APPROVED_*.md file must contain a human reviewer name. An automated "approved" string is invalid. |
| **G-08** | A study that begins as Class A must not be reclassified to Class B to bypass the approval step. |
| **G-09** | Contradiction between studies does not resolve by precedence. Both studies must be presented to human review. Scientific Director may not decide which study "wins". |
| **G-10** | The KPI for G-01 through G-09 violations is zero. Any violation suspends ARS operation until root cause is resolved. |

---

### 5.6 Governance Audit Trail

All governance events are logged through the existing ControlTower pipeline:

| Event | Type | Where Logged |
|---|---|---|
| Study classified | Class A or B | EventBus → ct_events |
| Approval requested | Class B | EventBus → ct_events + `ars_proposals/` file |
| Approval received | Class B | EventBus → ct_events |
| Study executed | Both | EventBus → ct_events |
| Finding promoted | Both | EventBus → ct_events + ars_knowledge_base.json |
| Finding rejected | Both | EventBus → ct_events + HypothesisRegistry |
| Guidance proposed | Both | EventBus → ct_events + `ars_proposals/` file |
| Integration approved | Class B | EventBus → ct_events + `ars_proposals/INTEGRATE_*.md` |
| Governance violation | N/A | EventBus → ct_events + CRITICAL alert |

ControlTower's wildcard subscription (`"*"`) means no additional logging wiring is required. All events are automatically captured.

---

### 5.7 Emergency Override Protocol

If a critical performance failure requires immediate research intervention:

1. Human creates `data/ars_proposals/EMERGENCY_APPROVAL_{slug}.md` directly
2. File must contain: EMERGENCY, reason, human name, date, explicit study scope
3. Scientific Director treats this as an APPROVED Class B file
4. After emergency study: normal Class B result review applies
5. Emergency override is logged to ct_events with CRITICAL severity

---

*Scientific Director Governance | ARS Phase 0 | Frozen 2026-08-03*
