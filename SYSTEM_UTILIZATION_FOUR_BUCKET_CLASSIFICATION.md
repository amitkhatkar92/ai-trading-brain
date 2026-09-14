# SYSTEM UTILIZATION — FOUR-BUCKET CLASSIFICATION
## Final synthesis — no new exploration, no code changes

**Date:** 2026-09-10
**Type:** READ-ONLY synthesis of `SYSTEM_ARCHITECTURE_DATA_LINEAGE_AUDIT_V1.md`,
`SYSTEM_TRUTH_MAP_V2.md`, `SYSTEM_UTILIZATION_DECISION_LINEAGE_AUDIT_V3.md`,
`SYSTEM_UTILIZATION_INTEGRATION_REVIEW_PHASE4.md`, and `SYSTEM_OPERATING_MAP.md`. All facts below
were code-verified in those five documents; this document only re-sorts them into the four buckets
requested. **No code, wiring, or trading logic changes accompany this document, per explicit
instruction not to modify the system tonight.**

---

## The four buckets applied to every component discovered across five audit rounds

### 🟢 Live + decision-connected

| Component | Confirms |
|---|---|
| `global_intelligence/`, `market_intelligence/` (+ `regime_probability_model.py`) | Layers 1-2, feed every cycle |
| `meta_learning/` (MetaLearning + `regime_strategy_map.py`) | Strategy weight prediction + regime-based ranking, changes capital allocation |
| `opportunity_engine/equity_scanner_ai.py` + `klp_evaluator.py` (KLP-001 scoring) | Scanner + signal annotation |
| `strategy_lab/` (StrategyLab, WFT/Overfit/CrossMarket gates) | Quality-gates every signal |
| `knowledge_authority/knowledge_decision_pipeline.py` (KDA Authority) | **The one fully-closed loop** — can override StrategyLab either direction |
| `risk_control/capital_risk_engine.py`, `risk_manager_ai.py`, `portfolio_allocation_ai.py`, `stress_test_ai.py` | Sizing + risk gates |
| `risk_control/options_risk_engine.py` + Options Fast Path | 4 hard gates (capital/loss/VIX/streak) for options |
| `market_simulation/simulation_engine.py` | 1000 MC runs |
| `risk_guardian/risk_guardian.py` 🔒 | Kill-switch |
| `risk_control/correlation_engine.py`, `smart_execution.py` | Confirmed removes signals, not just logs |
| `debate_system/` + `decision_ai/decision_engine.py` | Weighted vote literally gates approval |
| `execution_engine/order_manager.py` (incl. AET) | Broker placement, timing modes |
| `trade_monitoring/` | Outcome capture |
| `learning_system/strategy_performance_tracker.py` | Auto-disable excludes signals from assignment |
| `edge_discovery/EdgeDiscoveryEngine` | Full RESEARCH→VALIDATION→KNOWLEDGE pipeline reaching `evolved_strategies.json` → `MetaStrategyController` |
| `market_learning/pig_integration.py` (PMCI) | Confidence boost + 8%-weighted debate vote |
| `analysis/rejection_tracker.py` → `rejection_audit.db` → `knowledge_fusion_engine.py` | Confirmed (Phase 4 correction) — feeds KDA's `angle_view` every cycle |
| `control_tower/` | Telemetry backbone the whole system depends on for observability |
| `validation_engine/` 🔒 | 6-stage promotion gate |

**This is the complete, verified core.** Nothing new to add here — it is the same spine documented
in the Operating Map §1.

---

### 🔵 Live research / evidence collection (runs automatically, produces real evidence, does not itself decide)

| Component | What it collects | Status |
|---|---|---|
| KLP evidence adapter → `shadow_evidence_ledger.jsonl` → `HistoricalBehaviourEngine` | Outcome-linked evidence pool | Feeds 🟢 KDA — this is the healthy version of this bucket |
| `knowledge_system/options_research_pipeline.py` | Options pattern/hypothesis research, background thread every 5 min during market hours | Collects rigorously (p<0.10, n≥20 for VALIDATED) but its validated output does not cross into a decision (see 🟡 below) |
| `oios/` Phase F (`outcome_tracker.py` + full A0-F pipeline) | Market-leader outcome tracking, differential analysis | By its own explicit "ISOLATION CONTRACT" — a deliberately separate, parallel evidence stream |
| `predictive_gap/` (PGA) main pipeline | Daily gainer/loser root-cause analysis (13 miss categories), 9 markdown reports | Observational; this session's `broad_market_universe.py` extension DOES cross into 🟢 via `rejection_audit.db` |
| **`opportunity_engine/market_opportunity_benchmark.py`** (this session's new addition) | Daily A-F classification of every market mover against the live universe/pool/selection pipeline, fed into `rejection_audit.db` | **This is exactly this bucket, by design** — see note below |
| `scripts/knowledge_system/` Phases 1-2, 8-9 (fingerprint discovery/validation, controlled-live candidates, live-selection-eligibility) | Fingerprint pattern discovery | Phase 9's output does reach the scanner as a bounded confidence nudge — partially 🟢, collection stages are 🔵 |
| `production_readiness/prr_runner.py` (9 gates) | Daily certification/readiness reporting | Pure collection/reporting; see 🟡 for the open policy question |

**Note on the market benchmark:** your own list of future questions —
*"which strong movers were outside our universe? which were inside but missed by StrategyLab?
which entered the 20-pool but were ranked out of the 5? which reached the 5 but were rejected by
risk/execution?"* — maps almost exactly onto the taxonomy already implemented in
`market_opportunity_benchmark.py`'s `MoverCategory` enum: `OUTSIDE_UNIVERSE` (A),
`IN_UNIVERSE_NOT_IN_20POOL` (B), `IN_20POOL_NOT_SELECTED_5` (C),
`SELECTED_5_REJECTED_DOWNSTREAM` (D). **The instrument to answer these questions already exists
and is running daily** — no new parameter or feature is needed, only accumulated time.

---

### 🟡 Useful but currently disconnected (the real, actionable short list)

Only genuine cases remain here — everything else that looked disconnected turned out to have a
documented reason (moved to ⚪ below) or already be connected (moved to 🟢/🔵 above).

| Component | Why it's here |
|---|---|
| `options_research_pipeline`'s `KS_VALIDATED` state specifically | Statistically rigorous, genuinely validated (p<0.10, n≥20, OOS win-rate≥50%), and its own source already specifies the intended bounded mechanism (*"VALIDATED → BOUNDED influence: max ±5% confidence adjustment"*) — but `options_risk_engine.py` never reads it. **Highest-value, lowest-risk candidate found across all five documents**, precisely because the design work is already done. |
| `production_readiness/prr_runner.py`'s `certification_status` verdict | No prior doc ever decided whether a RED day should halt new signal generation. Needs a scoped policy decision, not a direct wire-in (9 heterogeneous gates, untested false-positive-halt risk). |
| `data/knowledge_pipeline_health.json` | Not a design gap — a previously flagged staleness bug (~2026-08-21) that was never re-verified as fixed. Needs a runtime check, not code. |
| `scripts/knowledge_system/` Phases 3-6 (RQ generation → prioritization → proposal building) | Generates real, well-formed research questions and proposals — but their only intended executor (`ResearchCoordinator`) is itself in the ⚪ bucket below, so these three phases currently produce output nobody acts on. |

---

### ⚪ Intentional isolation / historical / governance

| Component | Documented basis |
|---|---|
| `autonomous_research.ResearchCoordinator` + `ScientificDirector` (28 files) | `ARCH_006_FINAL_REPORT.md` (2026-08-22): *"KEEP_RESEARCH — not wired into production (intentional)"* |
| `growth_validator/` | `ARCHITECTURE_GAP_REGISTER.md`: manual-invocation pattern stated as correct |
| `decision_tracer/` | Built as a CLI debugging tool by construction |
| `hkap/` | `HKAP_DESIGN.md`: standalone historical-replay research tool |
| `ikn/` | `ARS_GAP_ANALYSIS.md`: explicitly listed as disconnected knowledge-graph utility |
| `data/champion_challenger_registry.jsonl` | Own module header: *"explicitly confirmed with the user before implementation... does NOT feed KDA... that would be a separate, later phase requiring its own explicit approval"* — deliberate staged governance |
| `data/discovered_edges.json` (vs. `evolved_strategies.json`) | Deliberately separate research/audit-trail file, not a duplicate |
| `data/ml_performance_dataset.json` | Multiple pre-existing reports confirm: empty by data scarcity (awaiting sufficient closed trades), not by choice |
| `data/scanner_memory.json`, `data/odm_state.json` | Observability/restart-persistence files for already-live components; correctly not separate decision inputs |
| `oios/` Phase F (as a *design* matter, distinct from its evidence-collection role in 🔵) | Its own "ISOLATION CONTRACT" predates this audit — genuinely, originally intentional |

---

## Governing principle for anything considered in the future

> Market → Universe → Opportunities → Selection → Decision → Execution → Outcome → Learning →
> Validated knowledge → Better future decisions

Per your instruction, this becomes the standing filter: **nothing in the 🟡 or ⚪ buckets should
be given more complexity, more features, or more parameters unless a specific step is proposed
to move it concretely along this chain toward a measurable decision effect.** Research is not
complete when it produces a report — it is complete when validated knowledge changes a decision
and that change's effect can later be measured. This is now written down as the standard the
system is held to, not just this session's opinion.

---

## What happens now — nothing

Per explicit instruction: **no system modification tonight.**
- The market opportunity benchmark keeps running automatically at EOD, accumulating evidence —
  no action needed, no analysis of its data yet, exactly as instructed.
- The KDA learning loop continues operating as-is — it is the one component already doing what
  the rest of the system aspires to.
- The two 🟡 items with a clear future path (options research bounded-confidence wiring, PRR gate
  policy) remain identified, not started, awaiting a future explicit decision.
- No new research/intelligence modules are being proposed or added.

This closes the audit/synthesis series. The next natural entry point, whenever you choose it, is
either: (a) act on one of the two identified 🟡 candidates, or (b) revisit the market benchmark
once it has accumulated a meaningful sample, using the exact question set you listed above —
which the instrument already answers.
