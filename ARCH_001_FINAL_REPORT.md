# ARCH-001 Architecture Re-Verification — Final Report

**Date:** 2026-08-14  
**Scope:** Full production + knowledge pipeline audit (Sections A–D)  
**Status:** COMPLETE — all gaps classified, implementation items resolved  
**Tests:** 314/314 passing  
**Pre-deploy status:** READY — awaiting git commit + VPS deploy

---

## 1. Actual Production Call Graph (Intraday Cycle)

```
GlobalIntelligence          → GlobalDataAI.fetch() → GlobalSnapshot (5-min cached)
MarketIntelligence          → MarketDataAI → NIFTY/BANKNIFTY regime, VIX
RegimeProbabilityModel      → regime distribution (BULL/BEAR/SIDEWAYS/CRISIS)
MetaLearning                → RegimeStrategyMap weights, MetaStrategyController active set
OpportunityEngine           → EquityScannerAI.scan() → List[TradeSignal]
KLP-001 shadow (observe)    → KLPEvaluator.evaluate_and_record() — observational only
StrategyLab                 → StrategyGeneratorAI.assign_strategy() + BacktestingAI gate
KLP-001 annotate            → KLPEvaluator annotates each surviving signal
KDA-003 shadow (NEW)        → KnowledgeDecisionPipeline.run_knowledge_shadow() — SHADOW ONLY
CapitalRiskEngine           → allocate() per strategy budget
RiskControl                 → RiskManagerAI.filter_with_heat_split() → approved signals
                               + get_rejection_tracker().ingest_rejection() (risk rejects)
                               + get_rejection_tracker().ingest_rejection() (strategy-lab rejects) [NEW GAP-009]
Options fast-path           → OptionsQualityGate + OptionsOrderManager.execute()
MarketSimulation            → MonteCarlo 14 scenarios → scenario scores
RiskGuardian                → FailSafeRiskGuardian.evaluate() → kill switch (VIX>45, loss>2%)
CorrelationEngine           → correlation de-duplication
SmartExecutionEngine        → adaptive execution timing
Debate (5 agents)           → MultiAgentDebate.run(TradeSignal, MarketSnapshot) — NO KDA INPUT
DecisionEngine              → DecisionEngine.decide() → approved=True/False (threshold 6.5)
MarketTruthGovernor         → final governance check
OrderManager                → OrderManager.execute() — PAPER_TRADING gated
```

Full detail: [ARCHITECTURE_ACTUAL_CURRENT.md](ARCHITECTURE_ACTUAL_CURRENT.md)

---

## 2. Actual Knowledge Call Graph

```
EquityScannerAI.scan()
  │
  ├─► KLPEvaluator.evaluate_and_record()          [writes klp/klp_YYYY-MM-DD.jsonl]
  │
  ├─► KnowledgeDecisionPipeline.run_knowledge_shadow()
  │     ├─► HistoricalBehaviourEngine.get_behaviour_profile(symbol)
  │     ├─► KnowledgeFusionEngine.analyse_record(symbol, angles)
  │     │     reads: rejection_audit.db, klp/*.jsonl, kda_decisions*.jsonl
  │     ├─► KnowledgeDecisionAuthority.evaluate(hbe_profile, kfe_view, signal)
  │     └─► KDALedger.record(decision_record)      [writes kda/kda_decisions_YYYY-MM-DD.jsonl]
  │
  └─► [via RiskManagerAI] RejectionTracker.ingest_rejection()    [writes rejection_audit.db]
      [via _run_strategy_lab] RejectionTracker.ingest_rejection() [NEW GAP-009]

EOD (_do_eod_learning):
  KnowledgeDecisionPipeline.run_eod_knowledge_update()
    ├─► KDALedger.load_decisions(today)
    ├─► KLPOutcomeEngine.fill_pending_outcomes()    [reads klp JSONL, writes outcomes]
    ├─► KDAOutcomeEngine.evaluate(decisions, outcomes)
    ├─► KDAComparativeAnalyzer.compare(decisions, outcomes)
    ├─► KDAAuthorityReporter.generate_report()      [writes kda_authority_validation.json]
    └─► Telegram notification if gate advances [NEW GAP-008]

KLP→KSL bridge (EOD, unconditional):
  run_klp_loop()  [scripts/knowledge_system/knowledge_feedback_loop_001.py]
    reads KLP JSONL → writes ksl_training_YYYY.jsonl → HBE.load_outcomes()
```

---

## 3. Actual Information-Flow Graph

Full detail: [INFORMATION_FLOW_MATRIX.md](INFORMATION_FLOW_MATRIX.md)

Key data flows:

| Producer | Storage | Consumer | Freshness |
|---|---|---|---|
| KLPEvaluator | `data/klp/klp_YYYY-MM-DD.jsonl` | KLPOutcomeEngine, HBE, KFE | Intraday + EOD |
| KDALedger | `data/klp/kda/kda_decisions_*.jsonl` | KDAOutcomeEngine, KDAComparativeAnalyzer | EOD |
| RejectionTracker | `data/rejection_audit.db` | KFE.load_fusion_records() | EOD |
| KDAAuthorityReporter | `data/klp/kda/kda_authority_validation.json` | Telegram /kda command [NEW] | EOD |
| StrategyPerformanceTracker | `data/strategy_perf.db` | StrategyLab._run_strategy_lab() | Per cycle |
| LearningEngine | `data/learning_*.json` | MasterOrchestrator._do_eod_learning() | EOD |

---

## 4. Components Already Correctly Connected

| Component | Status | Evidence |
|---|---|---|
| KLP JSONL → HBE | ✅ | `HBE.load_outcomes()` reads `ksl_training_*.jsonl` |
| KLP JSONL → KFE | ✅ | `KFE.load_fusion_records()` reads KLP JSONL |
| RejectionTracker ← RiskManagerAI | ✅ | `filter_with_heat_split()` calls `ingest_rejection()` |
| RejectionTracker → KFE | ✅ | `KFE.load_fusion_records()` reads `rejection_audit.db` |
| KDA Ledger ← Pipeline | ✅ | `_shadow_impl` calls `ledger.record()` |
| KDA Decisions → EOD Outcome Engine | ✅ | `_eod_impl` calls `ledger.load_decisions()` |
| LearningEngine → StrategyLab | ✅ | `perf_tracker.get_disabled_set()` read in `_run_strategy_lab()` |
| KLP→KSL bridge | ✅ | `run_klp_loop()` unconditional in `_do_eod_learning()` |
| PAPER_TRADING defence-in-depth | ✅ | OrderManager checks both PAPER_TRADING AND LIVE_TRADING_AUTHORIZED |

---

## 5. Components Disconnected (at start of ARCH-001)

| Gap | Component | Issue | Resolution |
|---|---|---|---|
| GAP-009 | StrategyLab → rejection_audit.db | Strategy-rejected signals not tracked | **FIXED** — ingest_rejection() added |
| GAP-008 | KDA authority gate → Telegram | No operator notification when gate advances | **FIXED** — market_alert() added |
| GAP-010 | /kda Telegram command | No visibility into KDA shadow status | **FIXED** — /kda command added |
| GAP-011 | Architecture tests | No automated structural verification | **FIXED** — 56 tests added |

---

## 6. Orphan Modules

| Module | Orphan Type | Classification |
|---|---|---|
| `autonomous_research/research_coordinator.py` | WRITE→NO CONSUMER (ResearchCoordinator output) | P4 — WAIT_FOR_EVIDENCE |
| `market_intelligence/market_monitor.py` (continuous scan) | Output consumed only via EventBus | P4 — BY DESIGN |

No P0/P1 orphans found.

---

## 7. Duplicate Responsibilities

None found. Each critical responsibility has exactly one authoritative owner:

- **Entry price**: EquityScannerAI only
- **Final approved/rejected**: DecisionEngine only  
- **Hard kill switch**: FailSafeRiskGuardian only
- **Position sizing**: CapitalRiskEngine + PortfolioAllocationAI (complementary, not duplicate)
- **KDA shadow decisions**: KnowledgeDecisionPipeline only

---

## 8. Data-Flow Breaks

No P0 breaks found. Three P3 gaps existed at start of audit; all resolved.

---

## 9. Gap Priority Classification

| Gap | Severity | Description | Status |
|---|---|---|---|
| GAP-001 | P3 | KDA needs 30+ decisions for statistical gate | WAIT_FOR_EVIDENCE |
| GAP-002 | P3 | KDA directional accuracy < 57% threshold | VALIDATE_WITH_DATA |
| GAP-003 | P3 | HBE needs 6+ outcome samples per symbol | WAIT_FOR_EVIDENCE |
| GAP-004 | P2 | KLP→KSL bridge scheduling | ALREADY_RESOLVED |
| GAP-005 | P4 | Dhan API blocked (451) → yfinance fallback | KEEP_AS_CONTEXT |
| GAP-006 | P4 | Debate agents receive no KDA context | KEEP_AS_CONTEXT (by design) |
| GAP-007 | P3 | KFE multi-angle confidence calibration | WAIT_FOR_EVIDENCE |
| **GAP-008** | **P2** | KDA gate → Telegram notification | **IMPLEMENTED** |
| **GAP-009** | **P2** | StrategyLab → rejection_audit.db | **IMPLEMENTED** |
| **GAP-010** | **P2** | /kda Telegram command | **IMPLEMENTED** |
| **GAP-011** | **P1** | Architecture tests | **IMPLEMENTED** |
| GAP-012 | P3 | KDA vs Debate agent disagreement rate | VALIDATE_WITH_DATA |

Full register: [ARCHITECTURE_GAP_REGISTER.md](ARCHITECTURE_GAP_REGISTER.md)

---

## 10. What Was Fixed (This Session)

### GAP-009: StrategyLab → rejection_audit.db (CONNECT_NOW)
**File:** `orchestrator/master_orchestrator.py`  
**Location:** `_run_strategy_lab()` — inside `[StrategyLabReject]` loop  
**Change:** Added `get_rejection_tracker().ingest_rejection()` call per strategy-rejected signal, wrapped in `try/except`. Feeds `quality_tier="STRATEGY_REJECTION"` so KFE can distinguish from risk-layer rejects.

### GAP-008: KDA Gate → Telegram Notification (IMPLEMENT_NOW)
**File:** `orchestrator/master_orchestrator.py`  
**Location:** `_do_eod_learning()` — in the `KDA-003 EOD update` block  
**Change:** After EOD update, reads `authority_report.authority_status`. If gate has advanced beyond `NOT_VALIDATED`, sends `market_alert()` with decisions count + direction accuracy.

### GAP-010: /kda Telegram Command (IMPLEMENT_NOW)
**File:** `notifications/telegram_bot.py`  
**Changes:**
1. Registered `/kda` → `self._cmd_kda` in the command dispatch map
2. Added `/kda` entry to `/help` response text
3. Added `_cmd_kda()` method: reads `data/klp/kda/kda_authority_validation.json` + today's JSONL ledger, returns authority status, decision count, accuracy, and top-3 decisions by authority score

### GAP-011: Architecture Tests (IMPLEMENT_NOW)
**File:** `tests/test_arch_001_integration.py`  
**56 tests across 6 groups:**
- T1 (12): Production call graph — all 12 production layers importable, OrderManager PAPER_TRADING enforcement
- T2 (12): Knowledge pipeline — HBE/KFE/KDA/Ledger/Pipeline importable, safety invariants, shadow-only result
- T3 (10): Data producer→consumer — KLP, HBE, KFE, RejectionTracker, KDA Ledger, EOD, KLP→KSL bridge
- T4 (7): No orphan critical outputs — KDA→EOD, KLP→Outcome, HBE→KDA, KFE→KDA, Authority→Telegram
- T5 (8): Responsibility ownership — entry price, final decision, kill switch, position sizing, KDA shadow-only
- T6 (7): PAPER_TRADING safety — config default, LIVE_TRADING_AUTHORIZED absent, no cross-layer imports

---

## 11. What Remains

| Item | Why Remaining | Action |
|---|---|---|
| KDA statistical gate validation | Needs 30+ live decisions (30 days of paper trading) | WAIT_FOR_EVIDENCE |
| KDA direction accuracy ≥57% | Needs 30+ validated outcomes | VALIDATE_WITH_DATA |
| HBE outcome calibration | Needs 6+ outcomes per symbol | WAIT_FOR_EVIDENCE |
| KFE multi-angle confidence | Needs outcome data for calibration | WAIT_FOR_EVIDENCE |
| KDA→Debate integration | Architectural decision: debate agents intentionally isolated from KDA | KEEP_AS_CONTEXT |

---

## 12. Why Anything Remains

**P3 gaps (WAIT_FOR_EVIDENCE):** These items require accumulated live data before they can be validated or acted upon. The infrastructure to collect that data is fully connected (KDA Ledger, KLP JSONL, rejection_audit.db, HBE outcome files). They will resolve organically as trading sessions accumulate.

**P4 gaps (KEEP_AS_CONTEXT):** Architectural decisions made intentionally. KDA is shadow-only by design until the statistical authority gate is earned. Debate agents receive only market-observable inputs by design.

No P0 or P1 items remain unresolved.

---

## 13. Tests

| Suite | Tests | Result |
|---|---|---|
| KDA-001 (knowledge decision authority) | 100 | ✅ 100/100 |
| KDA-002 (validation + comparative) | 120 | ✅ 120/120 |
| KDA-003 (shadow pipeline integration) | 38 | ✅ 38/38 |
| ARCH-001 (architecture integration) | 56 | ✅ 56/56 |
| **TOTAL** | **314** | **✅ 314/314** |

---

## 14. Safety Verification

| Invariant | Verified By | Status |
|---|---|---|
| PAPER_TRADING=True (default) | T6.test_paper_trading_is_true_in_config | ✅ |
| LIVE_TRADING_AUTHORIZED absent | T6.test_live_trading_authorized_absent | ✅ |
| KDA execution_authority=False always | T2.test_kda_shadow_result_has_no_execution_authority | ✅ |
| KDA broker_calls=0 always | T2.test_knowledge_pipeline_safety_invariants | ✅ |
| Knowledge pipeline does NOT import execution_engine | T6 x3 (HBE, KFE, Pipeline) | ✅ |
| Debate agents do NOT receive KDA output | T5.test_kda_is_not_production_authority | ✅ |
| DecisionEngine is sole approved/rejected authority | T5.test_final_decision_made_by_decision_engine | ✅ |
| RiskGuardian kill switch checks VIX + daily loss | T5.test_hard_kill_switch_owned_by_risk_guardian | ✅ |
| RejectionTracker called by RiskManagerAI | T3.test_rejection_tracker_called_by_risk_manager | ✅ |
| KDA decisions have EOD consumer | T4.test_kda_decisions_have_eod_consumer | ✅ |

---

## 15. Commit Hash + Deployment Status

| Item | Value |
|---|---|
| Previous deployed commit | `42c642d` (KDA-003) |
| ARCH-001 changes | NOT YET COMMITTED |
| VPS status | `42c642d` — both containers `Up (healthy)` |
| Deploy status | **PENDING** — awaiting `git commit` + `git push` + VPS deploy |

### Files Changed (ARCH-001)
```
tests/test_arch_001_integration.py          NEW — 56 architecture tests
orchestrator/master_orchestrator.py         GAP-008 (KDA gate Telegram) + GAP-009 (StrategyLab→RejectionTracker)
notifications/telegram_bot.py               GAP-010 (/kda command)
ARCHITECTURE_ACTUAL_CURRENT.md             NEW — Section A: production call graph
INFORMATION_FLOW_MATRIX.md                 NEW — Section C: data flow matrix
ARCHITECTURE_GAP_REGISTER.md               NEW — Section D: gap register (12 gaps)
ARCH_001_FINAL_REPORT.md                   THIS FILE — Section B + summary
```

### Deploy Command
```powershell
git add tests/test_arch_001_integration.py orchestrator/master_orchestrator.py notifications/telegram_bot.py ARCHITECTURE_ACTUAL_CURRENT.md INFORMATION_FLOW_MATRIX.md ARCHITECTURE_GAP_REGISTER.md ARCH_001_FINAL_REPORT.md
git commit -m "ARCH-001: architecture re-verification + GAP-008/009/010/011 implementation

- GAP-011: 56 architecture integration tests (T1-T6), all 314 tests passing
- GAP-009: StrategyLab rejections wired to rejection_audit.db (KFE coverage)
- GAP-008: KDA authority gate advances trigger Telegram market_alert
- GAP-010: /kda Telegram command for KDA shadow status
- Section A/C/D documentation: call graph, flow matrix, gap register"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

---

*Report produced by: GitHub Copilot (ARCH-001 audit agent)*  
*All architectural conclusions are grounded in direct code inspection — no speculation.*
