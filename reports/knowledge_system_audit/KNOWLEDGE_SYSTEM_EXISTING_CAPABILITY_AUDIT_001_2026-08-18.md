# KNOWLEDGE_SYSTEM_EXISTING_CAPABILITY_AUDIT_001
**Date:** 2026-08-18  
**Purpose:** Read-only inventory of existing knowledge-engine capabilities before any new implementation  
**Scope:** Full ai_trading_brain codebase  
**Constraint:** Zero production changes; zero new code implemented  

---

## FINAL VERDICT: C — KNOWLEDGE_INFRASTRUCTURE_PARTIAL

The system possesses a **mature research instrumentation layer** and a **functioning hypothesis-testing pipeline**, but it lacks the closed feedback loop that would make it a "Continuous Knowledge Engine." Evidence is recorded comprehensively; learning from that evidence is entirely manual.

---

## 1. WHAT IS ALREADY IMPLEMENTED

### 1a. Per-Signal Observation Recording

**`opportunity_engine/mop_rc001_observer.py`**  
- Records every signal from `EquityScannerAI.scan()` to `data/mop_rc001/MOP_RC001_YYYY-MM-DD.json`
- Fields: symbol, direction, entry_price, stop_loss, target_price, atr, confidence, expected_move_pct, candidate_score, strategy, regime, rsi, vol_ratio, sector
- Outcome fields (`selected`, `actual_return_pct`) are marked post-hoc — NOT populated automatically
- **Status: IMPLEMENTED as write path; outcome backfill is MISSING**
- Test coverage: `test_mop_rc001.py` T001–T015

### 1b. Shadow Architecture Recording (per candidate, per day)

**`scripts/final_trading_architecture_shadow_001.py`**  
- Writes `data/logs/final_trading_architecture_shadow_001.jsonl` (861 lines; 840 `SHADOW_CANDIDATE` + 21 `SHADOW_DAILY_SUMMARY`)
- **SHADOW_CANDIDATE fields:** run_id, trade_date, t1_date, architecture_version, record_type, no_trades_generated, no_broker_calls, symbol, direction, universe_membership, v3_score, v3_rank, v3_model_version, pool_size, pool_rank, pool_direction, previous_close, opening_price, gap_pct, gap_rank, c2_score, c2_rank, selected_final_5, strategy_status, strategy_name, strategy_reason, strategy_regime, strategy_rejected, model_b_included, **t1_ret_pct, mfe_pct, mae_pct** (outcome fields present)
- **SHADOW_DAILY_SUMMARY fields:** t1_dir_acc_model_a_up/down, t1_ge2_model_a_up/down, t1_dir_acc_model_b_up/down, t1_ge2_model_b_up/down (daily aggregates populated)
- **Missing from SHADOW_CANDIDATE:** `knowledge_strategy_disagreement` (field added to selector after current records were written; new runs will include it)
- **Status: IMPLEMENTED** — comprehensive per-candidate selection + outcome record

### 1c. Outcome Tracking (OIOS)

**`oios/engine/signal_outcome_tracker.py`**  
- Fills forward returns at 1D, 3D, 5D, 10D, 20D horizons on `signal_births` table
- `signal_births` columns (8,562 rows in `data/study002_replay.db`): signal_id, opportunity_id, symbol, archetype_id, archetype_version, signal_type, detected_at, birth_price, base_score, regime_at_birth, theme_phase_at_birth, consensus_score_at_birth, expected_move_pct, expected_move_direction, current_state, actual_move_pct, edge_consumed_pct, re_score, final_state, final_age_trading_days, peak_move_pct, days_to_peak, trade_executed, trade_outcome_pct, invalidation_reason
- `decision_log` table: decision_id, action, conviction_score, suppression_reason, price_5d_later, price_10d_later, price_20d_later, max_adverse_20d, max_favorable_20d, counterfactual_type
- `opportunities` table (1,966 rows): full lifecycle from birth to final_state
- Test coverage: `test_outcome_tracking_001.py` A–T (20 tests)
- **Status: IMPLEMENTED** (runs nightly as OIOS Phase C/D)

### 1d. Rejection Classification Taxonomy

**`analysis/rejection_classifier.py`**  
Defines 9 rejection reason types:  
`LOW_DECISION_SCORE, LOW_QUALITY_SCORE, LOW_SFT, HIGH_VOL_REGIME, MAX_POSITIONS, DAILY_LOSS_LIMIT, CORRELATED_POSITION, LOW_CONVICTION, MANUAL_OVERRIDE`

**`analysis/rejection_tracker.py`** → `data/rejection_audit.db`  
- Columns: rejected_reason, rejection_outcome (CORRECT/FALSE_REJECTION/NEUTRAL/PENDING), symbol, strategy, quality_tier, price_at_rejection, price_after

**`analysis/rejection_audit.py`** — CLI with per-reason accuracy calibration  
**Research output:** `reports/mover_discovery_v3/knowledge_vs_strategy_incremental_value_003_rejection_audit.csv` (95 rows, OOS-period rejections)

- **Status: IMPLEMENTED (research layer)**. Taxonomy exists and is populated by research scripts; NOT automatically applied as a production gate.

### 1e. Hypothesis Registry

**`autonomous_research/hypothesis_registry.py`** + **`autonomous_research/hypothesis_models.py`**  
- Persistent store: `data/ars_hypothesis_registry.json` (16 hypotheses, 31 KB)
- Full lifecycle: PROPOSED → UNDER_REVIEW → APPROVED → PLANNED → RUNNING → VALIDATED → CONFIRMED / ARCHIVED / REJECTED
- Every status transition captured in `decision_history` (event_id, timestamp, actor, action, reason, previous_status, new_status, metadata)
- Fields per hypothesis: hypothesis_id, title, research_question, description, origin, origin_study, priority, confidence, status, classification, supporting_evidence, knowledge_gap, validation_method, validation_result, decision_history
- **Status: IMPLEMENTED** — thread-safe, append-only, versioned

### 1f. Hypothesis Testing Pipeline (8 stages)

**`autonomous_research/research_coordinator.py`**  
Stages: STUDY_PLAN → REPLAY → VALIDATION → AUDIT → EVIDENCE → KNOWLEDGE → SYNTHESIS → REPORT  
- Config: `autonomous_research/rc_config.py` (each stage independently toggleable)
- History: `data/ars/rc/history.json` (4 runs retained, max 90 per config)
- History fields per run: run_id, study_plan_id, study_type, date, stages, telemetry, health
- **Status: IMPLEMENTED** (runs as research pipeline; 4 actual runs completed)

### 1g. Strategy Promotion Control

**`validation_engine/`** — 6-stage promotion pipeline  
Gates: WinRate ≥ 50%, Sharpe > 0.8, MaxDD < 15%  
All thresholds configurable in `config.py` (`PROMOTION_WINRATE`, `PROMOTION_SHARPE`, `PROMOTION_MAX_DD`)

**`trade_monitoring/strategy_health_monitor.py`** — automatic demotion  
- Full gate (≥20 trades): WR < 45% AND total_r < −0.50 → DISABLE  
- Partial gate: WR < 35% → DISABLE  
- **Status: IMPLEMENTED** (strategies only; does NOT cover V3/C2 modifications)

### 1h. Pattern Detection (offline)

**`analysis/pattern_miner.py`** — mines rejection patterns by reason × quality tier  
**`analysis/edge_detector.py`** — detects statistical edges; flags possible false rejections  
**`autonomous_research/scientific_director.py`** — scientific approval gate for hypotheses (research layer only)  
- **Status: IMPLEMENTED (offline/research only)**. Not wired to production decision gates.

### 1i. Research Outputs (45 Report Files)

`reports/mover_discovery_v3/` contains 45 files covering:
- V3 discovery research (TRAIN/VAL/OOS splits across 214 days)
- Post-open gap analysis (8,560 rows, C2 validation)
- Knowledge vs Strategy incremental value (3 versions)
- Strategy reconstruction (funnel analysis, regime breakdown)
- Shadow audit (2 days live shadow data)
- Selection quality audit (80 tests, all passing, 2026-08-18)

All confirmed TRAIN=107 days, VAL=53 days, OOS=54 days (2026-05-14 to 2026-07-30).

### 1j. Missed Mover Classification (research artifacts)

**`reports/mover_discovery_v3/mover_discovery_v3_missed_cases.json`**  
**`reports/mover_discovery_v3/mover_discovery_v3_missed_and_recovered.json`**  
**`data/audit/daily_selection_quality_missed_movers.csv`**  
- Classifies `RANKING_MISS`, `CORRECTLY_RANKED`, `POOL_MISS`, `DATA_MISS` for ≥2% movers  
- Subtype reasons: `OUTRANKED_BY_STRONGER_OPENERS` (80), `ADVERSE_OPEN_GAP` (71), `LOW_C2_SCORE` (33)  
- **Status: RESEARCH_ONLY** — computed by `scripts/daily_selection_quality_audit_001.py` per audit run; NOT automatically recorded per live trading day.

---

## 2. WHAT IS AVAILABLE THROUGH EXISTING RESEARCH/AUDIT SYSTEMS

The following exist as **executable research scripts** (manual trigger, produce reports):

| Script | What it produces |
|--------|-----------------|
| `scripts/knowledge_vs_strategy_002.py` | V3/C2/strategy comparison across TRAIN/VAL/OOS; rejection audit CSV |
| `scripts/knowledge_vs_strategy_003.py` | Rejection audit with OOS period; 95-row rejection taxonomy |
| `scripts/strategy_reconstruction_001.py` | Funnel analysis: universe → V3 pool → Top-5 → executed |
| `scripts/daily_selection_quality_audit_001.py` | 15-phase quality audit; rank decay; missed movers; leakage check; 80 tests |
| `scripts/final_trading_architecture_shadow_001.py` | Shadow candidates JSONL with outcomes |

These scripts can be re-run at any time against the existing CSV/DB data to refresh findings.

---

## 3. WHAT IS ONLY MANUAL

The following require a human researcher to trigger, interpret, and act on:

| Capability | What makes it manual |
|---|---|
| Missed mover analysis | Researcher runs audit script; reads markdown report; decides what to change |
| Hypothesis creation | No automatic trigger; researcher manually creates hypothesis in registry |
| Hypothesis → Production change | Researcher must edit config/code; no automation gate |
| Shadow results → Production update | Shadow JSONL grows; nothing reads it back to update gates |
| Rejection audit → Strategy disable | Rejection patterns identified; no auto-disable wired to patterns |
| Regime underperformance detection | Pattern_miner runs offline; no auto-trigger for threshold adjustment |

---

## 4. WHAT IS GENUINELY MISSING

### Gap A — Automatic Missed Mover Recording (LIVE)
The research scripts compute missed movers from historical CSV data. The **live shadow system** (`SHADOW_CANDIDATE` records) contains all necessary fields (c2_rank, selected_final_5, t1_ret_pct) to classify a candidate as a missed mover in near-real-time. **But no process reads the shadow JSONL and writes a missed-mover event.**

### Gap B — Shadow → Research Feedback Loop
Shadow results are written to `data/logs/final_trading_architecture_shadow_001.jsonl` and never read back. No scheduled process:
- Reads new shadow records
- Computes rolling missed-mover rate
- Updates hypothesis evidence
- Triggers a research run when patterns accumulate

### Gap C — Authentication Gate for V3/C2 Changes
V3 enablement is a boolean flag (`V3Config.enabled = False`). Modifying it requires a code/config change with no:
- Required approval workflow
- Audit trail of who changed it and why
- Gate condition (e.g., OOS threshold must be met first)

The promotion policy document (`FINAL_ARCHITECTURE_PROMOTION_POLICY_001.md`) defines governance rules as text, not as enforced code.

### Gap D — Per-Candidate Knowledge Record (Live Trading Day)
The live trading system (when running `main.py --paper`) writes:
- `data/logs/scan_attrition_*.jsonl` — per-candidate attrition with rejection reasons
- `data/paper_trades.csv` — executed trades

But there is **no single per-candidate evidence record** that links:  
discovery_status → pool_status → C2_rank → strategy_status → risk_status → execution_status → outcome  
All in one row, queryable by symbol+date.

The shadow JSONL has most of this for the shadow period, but it is not populated by live trading runs.

### Gap E — Automatic Hypothesis Generation from Patterns
The `pattern_miner.py` and `edge_detector.py` identify patterns and edges. But no code:
- Reads their output
- Formats it as a hypothesis
- Submits it to `hypothesis_registry.py`

This transition is entirely manual.

### Gap F — Persistent Cross-Audit Knowledge Digest
Each audit script writes its own isolated JSON/CSV files. There is no:
- Central "master evidence record" that grows with each cycle
- Mechanism to merge findings from different audits
- Conflict detection when a new finding contradicts a prior confirmed hypothesis

`data/ars_hypothesis_registry.json` is the closest thing to a master store, but it contains hypothesis metadata only (not the raw evidence tables).

---

## 5. WHAT SHOULD NOT BE REBUILT

| Component | Reason |
|---|---|
| `signal_births` table schema | Comprehensive, well-tested, 8,562 rows in replay DB |
| `hypothesis_registry.py` lifecycle | Full status machine, thread-safe, already 16 entries |
| `research_coordinator.py` pipeline | 8-stage orchestrator; 4 real runs; well-structured |
| Shadow JSONL field set | Already contains all pre-execution AND outcome fields needed |
| V3 discovery CSV research artifacts | 45 files; 214 days validated; OOS anchors locked |
| Rejection taxonomy (9 classes) | Well-calibrated per-reason accuracy in rejection_audit.py |
| Strategy promotion gates | Working in production; WinRate/Sharpe/MaxDD gates wired |

---

## 6. WHAT, IF ANYTHING, SHOULD BE IMPLEMENTED NEXT

Given the audit findings, **one component would close the largest gap with minimum risk**:

### Recommended: Shadow → Evidence Consumer (Read-only; no production changes)

A scheduled script that:
1. Reads `data/logs/final_trading_architecture_shadow_001.jsonl` (new records since last run)
2. Classifies each `SHADOW_CANDIDATE` as: `CORRECT_SELECT / RANKING_MISS / CORRECT_REJECT / FALSE_REJECT`
3. Appends classified records to a growing `data/shadow_evidence_ledger.jsonl`
4. When a pattern crosses a threshold (e.g., ≥30 ranking misses in 20 days), auto-creates a draft hypothesis in `hypothesis_registry.py` with status `PROPOSED`

This would close Gap A, Gap B, and Gap E simultaneously without touching any production decision path.

---

## 7. WHICH MISSING CAPABILITY HAS HIGHEST RESEARCH VALUE

**Gap B — Shadow Feedback Loop** (ranked #1)

The shadow system already records everything needed:
- Which candidates were selected (selected_final_5)
- What the outcome was (t1_ret_pct, mfe_pct, mae_pct)
- Why others were rejected (strategy_status, strategy_reason)
- What the C2 rank was for every candidate (c2_rank)

The 45 research reports in `reports/mover_discovery_v3/` were produced by running batch scripts over historical data. The same analysis could run **automatically** from the shadow JSONL as each day's data arrives, without any new signals, models, or production changes.

This would transform the system from "research instruments that a human operates" to "instruments that generate research findings automatically."

---

## CAPABILITY MATRIX

See companion CSV: `knowledge_system_existing_capability_matrix.csv`

---

## EVIDENCE SOURCES

| Source | Location | Rows/Records | Contains |
|---|---|---|---|
| Primary research CSV | `reports/mover_discovery_v3/post_open_gap_analysis.csv` | 8,560 | 214 days × 40 candidates; C2 scores, outcomes |
| Shadow JSONL | `data/logs/final_trading_architecture_shadow_001.jsonl` | 861 | 21 live trading days; pre-execution + outcomes |
| OIOS signal_births | `data/study002_replay.db` | 8,562 | Full lifecycle per signal including outcomes |
| OIOS opportunities | `data/study002_replay.db` | 1,966 | Full opportunity lifecycle |
| Hypothesis registry | `data/ars_hypothesis_registry.json` | 16 | Hypothesis lifecycle + decision history |
| ARS RC history | `data/ars/rc/history.json` | 4 | Research coordinator run history |
| Rejection audit DB | `data/rejection_audit.db` | ~400 | Rejection classification per candidate |
| KvS rejection CSV | `reports/mover_discovery_v3/knowledge_vs_strategy_incremental_value_003_rejection_audit.csv` | 95 | OOS period strategy rejections with outcomes |

---

## SYSTEM SAFETY VERIFICATION

This audit made zero production changes:

- Broker calls: 0
- Orders: 0
- CandidateStore writes: 0
- V3/C2/Strategy/Risk changes: 0
- Config modifications: 0
- New production modules: 0
