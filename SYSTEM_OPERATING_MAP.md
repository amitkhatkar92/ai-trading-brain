# SYSTEM OPERATING MAP
## The single consolidated reference — live decision loop + parallel research ecosystem

**Date:** 2026-09-10
**Type:** READ-ONLY synthesis. Consolidates `SYSTEM_ARCHITECTURE_DATA_LINEAGE_AUDIT_V1.md`,
`SYSTEM_TRUTH_MAP_V2.md`, `SYSTEM_UTILIZATION_DECISION_LINEAGE_AUDIT_V3.md`, and
`SYSTEM_UTILIZATION_INTEGRATION_REVIEW_PHASE4.md` into one operating reference. No new
exploration was needed for most of this — it restates prior, code-verified findings in the format
requested. One genuinely new measurement was added (§9, computational/storage cost), gathered this
round. No code, wiring, or trading logic was changed.

**This document is the intended stopping point of the audit series.** Per your own framing:
Phases 1–4 are complete. This is Phase 5 — the foundation — not a new audit and not a new feature.

---

## 1. The live decision loop — with real file names

```
MARKET DATA (yfinance / Dhan)
    ↓
Scanner ─────────────────────── opportunity_engine/equity_scanner_ai.py
    ↓                            (no 20-pool/5-pool gate — that concept is a
    ↓                             parallel shadow experiment, see §2)
Opportunity Signals ──────────── List[TradeSignal]
    ↓
StrategyLab ───────────────────── strategy_lab/ (WFT≥80%, Overfit<3.0, CrossMarket≥50%)
    ↓
KDA Authority ─────────────────── knowledge_authority/knowledge_decision_pipeline.py
    ↓                              (can override StrategyLab either direction)
CapitalRiskEngine ─────────────── risk_control/capital_risk_engine.py
    ↓
Risk / Portfolio / Stress ─────── risk_control/{risk_manager_ai,portfolio_allocation_ai,stress_test_ai}.py
    ↓
MarketSimulation ──────────────── market_simulation/simulation_engine.py (1000 MC runs)
    ↓
RiskGuardian 🔒 ────────────────── risk_guardian/risk_guardian.py (kill-switch)
    ↓
Correlation / SmartExecution ──── risk_control/{correlation_engine,smart_execution}.py
    ↓
DecisionEngine ────────────────── decision_ai/decision_engine.py + debate_system/ (5+1 weighted vote)
    ↓
AET timing ────────────────────── execution_engine/order_manager.py (IMMEDIATE/PULLBACK/CONFIRMATION,
    ↓                              RiskGuardian re-checked before every deferred placement)
BROKER ─────────────────────────  Dhan / Zerodha (paper mode currently)
    ↓
TradeMonitor ──────────────────── trade_monitoring/ (every 5 min)
    ↓
OUTCOME ────────────────────────  win/loss, R-multiple captured
    ↓
Knowledge / Evidence ──────────── KLP evidence adapter → shadow_evidence_ledger.jsonl
    ↓                              → HistoricalBehaviourEngine (data/klp/*, PIT_DISCOVERY_*.jsonl)
KDA evidence_state ────────────── knowledge_decision_authority.py::_classify_evidence_state()
    ↺
NEXT DECISION
```

**This loop is real, verified, and complete.** Every arrow above was traced to actual code across
four audit rounds, not assumed from documentation. It is the only fully-closed
DATA→DECISION→OUTCOME→LEARNING loop found in the system.

**Also feeding into this loop, confirmed connected (not shown above to keep the spine readable):**
- `market_learning/pig_integration.py` → confidence boost + 8%-weighted debate vote
- `edge_discovery/EdgeDiscoveryEngine` → `evolved_strategies.json` → `MetaStrategyController` (next cycle's active strategy pool)
- `meta_learning/regime_strategy_map.py` + `learning_system/strategy_performance_tracker.py` → capital allocation weight / auto-disable
- `analysis/rejection_tracker.py` → `rejection_audit.db` → `knowledge_fusion_engine.py` → KDA's `angle_view` (confirmed in Phase 4 — this one was undersold in earlier rounds)

---

## 2. The parallel research ecosystem — and exactly what crosses the "?"

```
Research / Experiments ────────── autonomous_research/ (28 files), OIOS (69 files),
    ↓                              scripts/knowledge_system/ Phases 3-6, PGA main pipeline,
    ↓                              production_readiness/ (9 gates), options research pipeline
Evidence / Knowledge Stores ────── hypothesis_registry.json, options_knowledge_store,
    ↓                              market_leader_outcomes, discovered_edges.json
Validation ─────────────────────  OOS/walk-forward tests exist (real, rigorous — e.g.
    ↓                              options: p<0.10, n≥20, OOS win-rate≥50%)
           ?
    ↓
KDA / Decision
```

**What the "?" actually is, itemized (this is the answer, not a mystery):**

| Crosses the "?" | Does NOT cross the "?" |
|---|---|
| KLP evidence adapter → `shadow_evidence_ledger.jsonl` → HistoricalBehaviourEngine → KDA `evidence_state` | `autonomous_research.ResearchCoordinator` — the intended executor for hypothesis_registry.json output; never called (`grep` confirms zero call sites) |
| `rejection_audit.db` → `knowledge_fusion_engine.py` → KDA `angle_view` | `options_research_pipeline`'s `KS_VALIDATED` state — designed for a bounded ±5% confidence adjustment (documented in its own source), never wired to `options_risk_engine.py` |
| `edge_discovery/EdgeDiscoveryEngine` → `evolved_strategies.json` → `MetaStrategyController` | `production_readiness/prr_runner.py`'s 9 certification gates — `certification_status` read by nobody in the live path |
| `market_learning/pig_integration.py` → confidence + debate vote | OIOS Phase F's `market_leader_outcomes` — by its own explicit "ISOLATION CONTRACT," never intended to cross |
| | `scripts/knowledge_system/` Phases 3-6 (RQ generation/prioritization/proposals) — feed only the disconnected ResearchCoordinator |
| | `champion_challenger_registry.jsonl` — by explicit, pre-approved design, deliberately held back pending a future authorized phase |

**The pattern:** the "?" is not a mysterious gap — every single research pipeline in this system
either (a) has a real, traced bridge across it, or (b) stops at a named, identifiable point with a
reason (some genuinely deliberate, one a bug, one an undocumented accident — see §5, §8).

---

## 3–8. The ten questions, answered from consolidated findings

### 1. Understand everything that exists
Two 17(+6)-layer decision paths were verified against code (not docs): the documented ARCHITECTURE.md
17 layers, plus 6 undocumented-but-real ones (RegimeProbabilityModel, KDA Authority, KLP-001
scoring, CorrelationEngine, SmartExecutionEngine, Options Fast Path). Alongside it: a ~96-file
knowledge/research ecosystem across 7 directories, ~23 significant data stores, ~270 markdown
reports, ~150 one-off root scripts.

### 2. Identify what is actually running
Confirmed running automatically: the full intraday cycle (§1), `_do_monitor()` every 5 min
(12 phases), `_do_eod_learning()` daily (20 phases including PGA, PRR, edge discovery, options
research background thread, KLP/KSL), OIOS Phase F at 16:45 IST, weekend intelligence Sat/Sun.
Confirmed NOT running automatically: `ResearchCoordinator`, `ScientificDirector`, `growth_validator`,
`decision_tracer`, `hkap`, `ikn` — all manual/CLI invocation only, all by documented design.

### 3. Identify what information is actually consumed
Every data store traced (V1 §6, V2 §1) has at least one reader — **zero fully-orphaned files
found across three audit rounds.** The real failure mode is subtler: several readers are
themselves disconnected (e.g. `KnowledgeProvider.list_edges()` is correctly gated by
`ph1_edge_gate.py`, but every caller of it lives inside the disconnected `autonomous_research/`
ecosystem — a "correctly-built bridge to nowhere," per V3 §2.2).

### 4. Identify what information reaches a trading decision
Confirmed reaching a live decision: KDA (the only fully-closed loop), edge discovery,
regime/strategy performance tracking, correlation engine, debate/decision weighting, PMCI
enrichment+vote, and — corrected in Phase 4 — `rejection_audit.db` via `knowledge_fusion_engine.py`.
**6 of the 10 components explicitly tested in V2 §4 concretely change a decision; 4 do not.**

### 5. Identify what is generated but does not influence anything
`autonomous_research/`'s 28 files (hypothesis registry, gap detection, cross-study synthesis,
methodology audits — all real, tested, unconsumed), `production_readiness/`'s 9 daily
certification gates, the options research pipeline's validated-knowledge state, OIOS Phase F's
outcome table, and `scripts/knowledge_system/` Phases 3-6's research-question output. All were
checked for a genuine documented reason (V3 §1) — most have one; two (options pipeline, PRR gates)
do not and are flagged in Phase 4 as real open questions worth a future decision.

### 6. Identify duplicated/redundant pathways
The clearest candidate examined was `discovered_edges.json` vs `evolved_strategies.json` —
resolved as NOT duplicated: they are deliberately separate stages (research audit trail vs. the
one live-promoted file `MetaStrategyController` actually reads). No genuine functional duplication
was found in four audit rounds — the system has a *sprawl* problem (many parallel systems), not
a *duplication* problem (two systems doing the identical job).

### 7. Identify where the system learns from outcomes
`TradeMonitor` → `LearningSystem`/EOD → `strategy_performance_tracker.py` (auto-disable),
`regime_strategy_map.py` (regime-weighted ranking), `edge_discovery` (new strategy mining from
outcomes), and — the one full loop — KDA's `evidence_state` machine fed by KLP/HistoricalBehaviourEngine.
This is real, closed-loop learning, not aspirational.

### 8. Identify where validated learning can modify future decisions
Only through the pathways in §1's "also feeding into this loop" list and the KDA loop itself.
Validated knowledge sitting in `options_knowledge_store` (statistically rigorous — p<0.10, n≥20)
currently **cannot** modify a future decision, despite being genuinely validated, because the
wiring step was never completed (Phase 4 #1 — the strongest "connect this" candidate found).

---

## 9. Computational / storage cost vs. decision value — new measurement this round

**Storage:** `data/` totals ~964 MB in this local workspace (caveat: includes historical
one-off local artifacts not necessarily present on the VPS, e.g. `replay.db` 100MB,
`study002_replay.db` 17MB, `ct_db_20260811.db` 29MB — dated snapshots). Breaking down what's
attributable to genuinely disconnected components specifically: `data/ars/` 0.09MB,
`data/ikn/` 0.09MB, `data/prr/` 0.05MB, `data/cle/` 0.03MB, `data/klp/` 0.57MB — **all small.**
The large blobs (`logs/` 550MB, `ede_feature_db.json` 93MB) belong to logging and to
`edge_discovery` — a **confirmed live, connected** component. **Verdict: storage bloat from
disconnected research is not a real problem here** — the ecosystem is cheap to store.

**Compute — this is the more real cost.** `knowledge_system/options_research_pipeline.py` runs a
background thread **every 5 minutes during market hours** (`PIPELINE_INTERVAL_MINUTES = 5`,
confirmed started conditionally when the options chain is live, `master_orchestrator.py:~270`).
Its output — `KS_VALIDATED` state — has **zero live decision consumer** today (Phase 4 #1). This
is the clearest concrete case of continuous, non-trivial background compute spent on a pipeline
that currently returns no decision value. By contrast, `production_readiness/`, PGA, and OIOS
Phase F all run **once daily at EOD** — bounded, low-frequency cost, low urgency regardless of
their current decision-connection status.

**Engineering/maintenance cost (not measured in CPU-seconds, but real):** `autonomous_research/`
alone is 28 files with 190 passing tests — a nontrivial ongoing maintenance surface for a
subsystem with zero current production consumers. This is the more meaningful "cost" in this
system: not compute cycles, but the cognitive and maintenance load of ~96 knowledge/research
files plus ~270 markdown reports that a future engineer (or agent) must wade through to find the
~15 that are actually load-bearing.

**Net cost/value verdict:** the single highest-value, lowest-risk action identified across all
five documents remains Phase 4 item #1 (options research → bounded confidence wiring) —
real validated knowledge, a pre-designed bounded mechanism, currently earning zero return on the
compute already being spent every 5 minutes to produce it.

---

## 10. The central question, answered

> "Do we actually have an intelligent trading system, or do we have many intelligent components
> running beside each other?"

**Both — precisely, and now precisely bounded.** The core decision path (§1) is a genuine,
integrated, closed-loop intelligent system: signals are gated, sized, risk-checked, debated, and
the outcome genuinely retrains the gating for next time, through one real, verified loop. Around
it sits a second, larger population of components — some deliberately kept separate (documented,
correctly cautious — OIOS, ResearchCoordinator, champion/challenger staging), some simply never
finished connecting despite being ready to (options research), and two cases of undocumented
drift (one a stale deprecation record now silently reversed, one a stale bug report never
re-verified). None of the second population is "wasted" in the sense of being redundant or
duplicative — but only a fraction of it currently feeds the first.

**This is now a precisely known state, not a suspicion.** That is the deliverable of Phases 1–4,
consolidated here.

---

## 11. What happens next — explicitly not started here

Per your explicit instruction: no code, wiring, or trading logic changes accompany this document.
The new daily market-opportunity benchmark (`opportunity_engine/market_opportunity_benchmark.py`,
already deployed) will continue accumulating data automatically with no further action needed —
correctly, per your instruction to let it accumulate before evaluating it, rather than acting on
last week's gainers/losers now.

**This document is the intended foundation for future authorization**, not a queued task list.
When you're ready to authorize action, the two concrete, already-scoped candidates are:
1. Wire the options research pipeline's `KS_VALIDATED` state into a bounded (±5% capped) confidence
   adjustment, per its own original design (Phase 4 #1) — highest value / lowest risk found.
2. Decide the fate of `production_readiness/prr_runner.py`'s certification gates — advisory-only
   forever, or should some subset gate trading (Phase 4 #2) — needs a scoping decision first, not
   a direct wire-in.

Everything else reviewed across five documents either already works correctly, or is correctly,
deliberately, and now-verifiably left alone.
