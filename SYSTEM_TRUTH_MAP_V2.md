# SYSTEM TRUTH MAP — V2
## File / Flow / Knowledge / Objective — Consolidated, Code-Verified

**Date:** 2026-09-10
**Type:** READ-ONLY audit. Builds on `SYSTEM_ARCHITECTURE_DATA_LINEAGE_AUDIT_V1.md` (read first —
this document does not repeat V1's master diagram or layer discrepancy table, only extends them).
**Method:** 3 parallel deep-dive research passes + direct grep verification of every contested
claim by me before writing this document. Where a subagent's claim could not be confirmed by a
direct grep against the actual gate/check code, it is marked **CORRECTED** below and V1 is
superseded on that specific point.

**Mandate for this phase (per explicit instruction):** no new features, no wiring changes, no
deletions. Understand what exists, trace where every information chain actually terminates,
and answer one question per component: *"How does this help the trading system make a better
decision — concretely, in code?"* If that cannot be answered, it is flagged, not assumed.

---

## 0. Three corrections to V1 / this session's own prior claims

Honesty about the audit process itself is part of the deliverable. These three items were
stated as 🟢/🟡 LIVE in V1 or in this session's subagent passes, and **direct grep verification
in this session found no supporting code**. They are downgraded below.

| Claim (V1 / prior passes) | Verification performed | Result |
|---|---|---|
| "options_research_pipeline's KS_VALIDATING→VALIDATED state gates live options orders" | `grep "knowledge_state\|KS_VALID\|options_knowledge_store"` in `risk_control/options_risk_engine.py` and `execution_engine/options_order_manager.py` | **ZERO matches in either file.** `OptionsRiskEngine.approve_and_size()` has exactly 4 gates: capital exposure, per-trade max loss, VIX guard, strategy loss-streak. None reference options knowledge state. **CORRECTED: 🔵 RESEARCH ONLY, not LIVE+USED.** |
| "oios/phase_f/outcome_tracker.py feeds KDA's evidence_state" | Traced `evidence_state` computation in `knowledge_authority/knowledge_decision_authority.py:211` → `_classify_evidence_state(ess, stability, oos_status, contradiction_factor)` → inputs come from `BehaviourMetrics` via `HistoricalBehaviourEngine`, which loads from `data/klp/*.jsonl`, bootstrap files, and `data/audit/dta041/PIT_DISCOVERY_*.jsonl` (grep-confirmed in `historical_behaviour_engine.py:931-1002`). **Zero reference to `oios/` anywhere in `knowledge_authority/`.** | **CORRECTED: the KDA evidence pipeline runs on KLP + PIT_DISCOVERY data, not OIOS Phase F output.** OIOS's `outcome_tracker` writes to `market_leader_outcomes` (its own internal table) for its own research purposes — real, but a separate, currently non-intersecting evidence stream from KDA's. |
| "ResearchCoordinator / scientific_director.py actively wired to live" (one subagent pass, V1 §5.1) | `grep "ResearchCoordinator\|scientific_director" orchestrator/master_orchestrator.py` | **Zero matches** — reconfirmed a second time this session. Fully dead/disconnected. |

**Pattern across all three corrections:** the wrong claim always came from reading a module's
own docstring/intent, or a design document, rather than tracing the actual consumer's gate
logic. This is the single most repeatable failure mode found across two audit rounds now —
recorded permanently in repo memory (see end of this document).

---

## 1. FILE LEVEL — where each information chain physically terminates

V1 §5 gave module-level summaries. This is the file-by-file pass across the 7 knowledge/research
directories (~96 files). Full per-file tables were produced; condensed here to the actionable
signal — which files' output reaches a live decision, and which stop earlier.

### 1.1 Directories where the chain reaches DECISION (🟢)

| Directory | File(s) that reach DECISION | Consumer (verified) |
|---|---|---|
| `knowledge_authority/` | `knowledge_decision_pipeline.py` | `risk_manager_ai.py`, `portfolio_allocation_ai.py` — every signal, every cycle |
| `edge_discovery/` | `edge_discovery_engine.py` (all 6 stages feed forward) | `evolved_strategies.json` → `MetaStrategyController.get_active_strategies()` |
| `meta_learning/` | `regime_strategy_map.py` | `portfolio_allocation_ai.py:~119` — `perf_weight` scales capital allocation 0.5x–2.0x |
| `learning_system/` | `strategy_performance_tracker.py` | `master_orchestrator.py:2372,2387` — disabled strategies excluded from signal assignment |
| `risk_control/` | `correlation_engine.py` | `master_orchestrator.py:1836` — signals literally removed from the list past this point |
| `market_learning/` | `pig_integration.py` (`pig_enrich_signals`, `pig_build_vote`) | Confidence boost in scanner; 8%-weighted vote in `DecisionEngine` |
| `debate_system/` | `multi_agent_debate.py` | `decision_ai/decision_engine.py:62-72` — weighted sum literally gates approve/reject |

### 1.2 Directories where the chain stops before DECISION (🔵 / 🟠)

| Directory | Where it stops | What it produces instead |
|---|---|---|
| `autonomous_research/` (28 files) | VALIDATION/RESEARCH — `ResearchCoordinator` never called | Fully-built, 190-test-covered 8-stage pipeline; hypothesis registry populated daily; nothing executes it |
| `production_readiness/` (14 files) | INFORMATION — all 9 gates are reports | `certification_status` computed daily; grep-confirmed zero reads in `risk_guardian.py`, `decision_engine.py`, `order_manager.py` |
| `knowledge_system/` options pipeline (13 files) | **CORRECTED from V1**: KNOWLEDGE, not DECISION | Real self-learning loop (observe→feature→pattern→hypothesis→validate→store), but `options_risk_engine.py`'s 4 gates never read it (§0) |
| `scripts/knowledge_system/` phases 3-6 (RQ generation, prioritization, proposal building) | RESEARCH | Feeds `hypothesis_registry.json` / `research_question_queue.jsonl` — same dead end as `autonomous_research/` since the only reader (`ResearchCoordinator`) is disconnected |
| `predictive_gap/` main PGA pipeline (gainer/loser RCA, 9 markdown reports) | INFORMATION | Human-readable reports only; **exception:** this session's `broad_market_universe.py` + `market_opportunity_benchmark.py` addition DOES reach `rejection_audit.db` → `knowledge_fusion_engine.py` (🟡 confirmed) |

### 1.3 Two-out-of-three loop closures (partial credit, be precise about which third)

`scripts/knowledge_system/` is the clearest example of a **partially-closed loop**:
- Phase 1-2 (fingerprint discovery) → Phase 8 (`controlled_live_candidates_001.py`) → Phase 9
  (`live_selection_eligibility_001.py`) → **reaches** `equity_scanner_ai.py` as a bounded
  confidence nudge. This third works.
- KLP evidence adapter (`klp_evidence_adapter_001.py`) → `shadow_evidence_ledger.jsonl` →
  pattern miner → EOD learning cycle. This third works (feeds `HistoricalBehaviourEngine`
  indirectly via KLP files, per §0's corrected evidence_state trace).
- Research-question generation → prioritization → proposal building (Phases 3-6) → dead end,
  since the only intended executor (`ResearchCoordinator`) is disconnected. This third does not
  close.

---

## 2. FLOW LEVEL — the real pipeline, ambiguity resolved

The user's mental model was: `Scanner → 20-pool → 5-pool → Strategy → Risk → Simulation → KDA →
Decision → AET → Execution → Monitoring → Outcome`. Verified against code:

### 2.1 "20-pool → 5-pool" — RESOLVED: this is a shadow research experiment, not live filtering

Direct evidence:
- `opportunity_engine/mover_discovery_v3.py` docstring: *"NEVER generates TradeSignal objects."*
- `orchestrator/master_orchestrator.py:7070` — explicit comment: *"NOTHING reads this file:
  mover_discovery_v3.py, final_c2_selector.py, ..."*
- `grep "v3_score" opportunity_engine/equity_scanner_ai.py` → **zero matches**. The real
  `EquityScannerAI.scan()` returns `TradeSignal` objects with no v3_score/c2_rank filtering at all.
- The V3/C2 20-pool→5-pool scoring only runs when `MOVER_DISCOVERY_V3_SHADOW_MODE` is enabled
  (default OFF), writing purely observational records to
  `data/logs/mover_discovery_v3_shadow.jsonl` and `data/shadow_evidence_ledger.jsonl`.

**Correct mental model:** live signals go **scanner → StrategyLab directly**, with no 20-pool/
5-pool gate in between. The 20-pool/5-pool concept exists only as a parallel, non-blocking
research experiment asking "what would an idealized selector have picked?" — its scores
(`v3_score`, `c2_rank`, `selected_final_5`) are used *only* for post-hoc classification
(this is exactly what this session's own `market_opportunity_benchmark.py` A-F taxonomy
consumes them for) — never to gate a real trade.

### 2.2 `discovered_edges.json` vs `evolved_strategies.json` — RESOLVED

- `strategy_lab/meta_strategy_controller.py:37-38,236-239` reads **only**
  `evolved_strategies.json` (`EVOLVED_STRATEGIES_PATH`) to build the active-strategy map used by
  `get_active_strategies()` every cycle.
- `edge_discovery/edge_ranking_engine.py` writes **directly** to `evolved_strategies.json` on
  promotion — there is no separate "staging→promotion" bridge file.
- `discovered_edges.json` is a parallel, research-only artifact read only by
  `growth_validator/gva_collector.py` and `knowledge_provider.py` (both 🔴/🔵, non-live).
- **`discovered_edges.json` and `evolved_strategies.json` are not the same pipeline stage** —
  the former is a research side-channel, the latter is the one live strategies actually load from.

### 2.3 AET (Adaptive Entry Timing) — confirmed position

AET is not a separate architectural layer; it is a stage **inside `execution_engine/order_manager.py`**,
between `DecisionEngine`'s approval and the actual broker call:

```
DecisionEngine APPROVE (confidence ≥ VIX-adaptive threshold)
        │
        ▼
OrderManager._determine_aet_mode()   — IMMEDIATE | PULLBACK | CONFIRMATION
        │
        ├─ IMMEDIATE / PULLBACK → place_order() now
        │
        └─ CONFIRMATION → deferred to `_aet_pending`, retried up to N candles
                 │
                 ▼
        attempt_aet_confirmations() — RE-CHECKS RiskGuardian.halt_status()
        before every deferred placement attempt (execution_engine/order_manager.py:~1578)
```

RiskGuardian does not "know about" AET specifically — it is simply re-consulted as a gate every
time a deferred CONFIRMATION slot tries to convert to a real order, so a kill-switch trip during
the deferral window still blocks the trade. This is a genuine safety interlock, correctly placed.

### 2.4 Corrected master flow (supersedes the ambiguous "20-pool/5-pool" wording)

```
MARKET → Scanner (opportunity_engine/equity_scanner_ai.py, no pool-gate)
       → StrategyLab (WFT/Overfit/CrossMarket gates)
       → KDA Authority (can override either direction)
       → CapitalRiskEngine → RiskControl → [Options Fast Path | MarketSimulation]
       → RiskGuardian 🔒 → CorrelationEngine → SmartExecutionEngine
       → DebateAndDecision (weighted vote, VIX-adaptive threshold)
       → AET timing (IMMEDIATE/PULLBACK/CONFIRMATION, RiskGuardian re-checked)
       → ExecutionEngine → Broker
       → TradeMonitoring (outcome capture)
       → LearningSystem/EOD (strategy weights, regime map, performance tracker)
       → [KLP evidence adapter → shadow_evidence_ledger.jsonl → HistoricalBehaviourEngine
          → KDA evidence_state] ← the ONE confirmed live feedback loop, corrected in §0
          to run through KLP/PIT_DISCOVERY data, NOT oios/ Phase F.
```

The "20-pool/5-pool" and OIOS Phase F machinery run **alongside** this, not **inside** it.

---

## 3. KNOWLEDGE / RESEARCH LEVEL — the DATA→LEARNING chain, per subsystem

Using the chain: **DATA → INFORMATION → RESEARCH → VALIDATION → KNOWLEDGE → DECISION → OUTCOME → LEARNING → NEXT DECISION**

| Subsystem | Furthest stage reached | Does it loop back to NEXT DECISION? |
|---|---|---|
| KDA (`knowledge_authority/`) | **DECISION → OUTCOME → LEARNING → NEXT DECISION** | ✅ Full loop — the only subsystem confirmed complete this session |
| Edge Discovery | **KNOWLEDGE → DECISION** (via `evolved_strategies.json`) | ✅ Effectively closed — new edges alter next cycle's strategy pool |
| Regime Strategy Map / Strategy Performance Tracker | **KNOWLEDGE → DECISION** (capital weight / auto-disable) | ✅ Closed |
| Correlation Engine / Debate weights | **DECISION** (structural, not learned) | N/A — deterministic rules, not a learning loop |
| PMCI / market_learning | **KNOWLEDGE → DECISION** (confidence + vote) | ✅ Closed for the enrichment/vote path |
| Options research pipeline | **VALIDATION → KNOWLEDGE** | ❌ **Stops here** — corrected in §0, no live gate consumes it |
| OIOS Phase F | **INFORMATION → RESEARCH** (own internal tables) | ❌ Does not feed KDA as previously believed (§0) — genuinely a separate, currently-parallel research stream |
| `scripts/knowledge_system/` RQ generation (phases 3-6) | **RESEARCH** | ❌ Stops — `ResearchCoordinator` (the intended executor) is disconnected |
| `autonomous_research/` (28 files, incl. ResearchCoordinator, ScientificDirector) | **VALIDATION** (hypothesis registry populated) | ❌ Stops — zero call sites in production |
| `production_readiness/` (9 gates) | **INFORMATION** | ❌ Stops — reports only, no gate reads `certification_status` |
| PGA main pipeline (gainer/loser RCA) | **RESEARCH** | ❌ Stops — 9 markdown reports, no consumer found (except the new benchmark addition, which is a different code path) |

**Answer to the user's framing directly:** validated research reaching decisions automatically
*does* happen — but only in **3 of the ~10 subsystems traced this session** (KDA, Edge Discovery,
Strategy Performance/Regime Map). The rest genuinely stop at RESEARCH, VALIDATION, or INFORMATION,
regardless of how sophisticated or well-tested the code producing them is.

---

## 4. OBJECTIVE LEVEL — "how does this help make a better decision?"

Ten components tested directly against this question, with code citations. ✅ = concretely
answered with a traced code path; ❌ = could not be answered, flagged explicitly.

| # | Component | Answer | Evidence |
|---|---|---|---|
| 1 | PMCI engine (`market_learning/pmci_engine.py`) | ✅ Boosts scanner confidence AND casts an 8%-weighted `DebateVote` | `pig_integration.py` `pig_enrich_signals()`/`pig_build_vote()`, called `master_orchestrator.py:~2317,~3700` |
| 2 | `options_research_pipeline.py` | ❌ **NO DECISION IMPACT FOUND** (corrected from earlier claim) | `options_risk_engine.py`'s 4 gates never reference knowledge state |
| 3 | OIOS Phase F `outcome_tracker.py` | ❌ **NO DECISION IMPACT FOUND** (corrected from earlier claim) | Writes to its own `market_leader_outcomes` table only; `evidence_state` computed from KLP/PIT_DISCOVERY, not OIOS |
| 4 | `EdgeDiscoveryEngine` | ✅ New strategies literally added to the tradeable list | `edge_ranking_engine.py` → `evolved_strategies.json` → `meta_strategy_controller.py:135` |
| 5 | `regime_strategy_map.py` | ✅ Win-rate changes capital allocation weight (0.5x–2.0x) | `portfolio_allocation_ai.py:~119`, `perf_weight` multiplies `base_alloc` |
| 6 | `strategy_performance_tracker.py` | ✅ Auto-disabled strategies excluded from signal assignment | `master_orchestrator.py:2372,2387` — `excluded_strategies=shm_disabled|perf_disabled` |
| 7 | `correlation_engine.py` | ✅ Signals actually removed (not just logged) past sector quota | `master_orchestrator.py:1836`, list length shrinks, confirmed against `test_dta_correlation_001.py` |
| 8 | 5-agent debate | ✅ Each score multiplies its weight into the sum that gates approval | `decision_engine.py:62-72`, `weighted_sum += vote.score * w` |
| 9 | `knowledge_feedback_loop_001.py` (hypothesis output) | ❌ **NO DECISION IMPACT FOUND** | `hypothesis_registry.json` has zero readers in live trading code |
| 10 | `prr_runner.py` (9 certification gates) | ❌ **NO DECISION IMPACT FOUND** | `certification_status` never read by `risk_guardian.py`, `decision_engine.py`, or `order_manager.py` |

**6 of 10 concretely change a decision. 4 of 10 do not — despite all four being real, running,
tested code that produces genuinely accurate analysis.** This is the exact distinction the user
asked this phase to establish.

---

## 5. What this means for "no new invention, understand what exists first"

This audit deliberately stops at mapping. It does **not** recommend which of the 🔴/🔵/🟠 items
should be wired in, retired, or left alone — that is a decision for a separate, explicitly
authorized session per the user's own sequencing ("Audit → Map → Understand → Classify →
Identify waste/gaps → Decide → Only then modify").

**What IS now established, with code citations, and can inform that future decision:**
- The **only fully-closed DATA→LEARNING loop** in the entire knowledge ecosystem is KDA
  (`knowledge_authority/`), fed by KLP/HistoricalBehaviourEngine/PIT_DISCOVERY evidence — not by
  OIOS, not by the options research pipeline, not by ResearchCoordinator.
- **Three subsystems are "one broken link away" from closing their loop**: options research
  pipeline (needs a real gate in `options_risk_engine.py`), OIOS Phase F (currently an isolated
  research stream — would need an explicit bridge to KDA or HBE to matter), and
  `scripts/knowledge_system/` RQ generation (needs either `ResearchCoordinator` wired in, or a
  simpler executor).
- **`production_readiness/`'s 9 gates and `autonomous_research/`'s 28 files are the largest
  "sophisticated but currently inert" blocks** — real engineering effort, zero live consumption,
  by design/historical accident rather than by architecture.

---

## 6. Explicit residual unknowns (not resolved in this pass, flagged rather than guessed)

- Whether OIOS Phase F's `market_leader_outcomes` data is intended to eventually feed KDA (a
  design decision) or is a permanently separate research stream (as ARCH-006 suggested for
  similar modules) was not stated in any document found — flagged for the user to clarify intent,
  not inferred.
- `production_readiness/`'s `ph1_edge_gate.py` DOES compute a "DECAYING edge" filter result, but
  whether `edge_ranking_engine.py` independently applies the same or a different decay rule was
  not cross-checked line-by-line in this pass — worth a focused 1-file diff if it matters later.
