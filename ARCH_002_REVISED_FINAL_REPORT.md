# ARCH-002-R: KDA Authority + System Alignment — Final Report

**Commit:** `afec1da`  
**Date:** 2026-08-22  
**Tests:** 337/337 passing  
**VPS:** Both containers `Up (healthy)`  
**PAPER_TRADING:** `true`  
**LIVE_TRADING_AUTHORIZED:** absent  
**broker_calls:** 0  
**orders:** 0  

---

## Final Architecture

```
MARKET DATA
→ GlobalIntelligence / MarketIntelligence
→ EquityScannerAI.scan()              ← SIGNAL GENERATION
→ KLPEvaluator.evaluate_and_record()  ← KLP observation (before StrategyLab)
→ StrategyLab (_run_strategy_lab)     ← SHADOW / CONTEXT (no longer the gate)
→ KLPEvaluator.annotate_strategy_outcome()  ← KLP annotation
→ KnowledgeDecisionPipeline.run_knowledge_shadow()  ← KDA INTELLIGENCE AUTHORITY
    → HBE.get_behaviour_profile()     ← HISTORICAL EVIDENCE
    → KFE.analyse_record()            ← KNOWLEDGE FUSION
    → KDADecisionAuthority.evaluate() ← KNOWLEDGE DECISION
    → KDALedger.record()              ← PERSIST DECISION
→ Signal merge (KDA union StrategyLab) ← NEW: KDA-authorized bypass StrategyLab gate
→ kda_vs_stratlab JSONL persisted     ← COMPARISON
→ CapitalRiskEngine.allocate()        ← RISK
→ RiskManagerAI.filter_with_heat_split() ← RISK VETO
→ MarketSimulation                    ← SCENARIO VALIDATION
→ RiskGuardian.evaluate()             ← KILL SWITCH (VIX>45, loss>2%)
→ Debate + DecisionEngine             ← QUALITY GATE
→ OrderManager.execute()              ← PAPER EXECUTION (PAPER_TRADING=true)
→ OUTCOME
→ KDAOutcomeEngine (EOD)              ← OUTCOME MEASUREMENT
→ KDAComparativeAnalyzer (EOD)        ← KDA vs StrategyLab comparison
→ KDAAuthorityReporter (EOD)          ← AUTHORITY VALIDATION
→ run_klp_loop() / KSL (EOD)         ← KNOWLEDGE FEEDBACK
```

---

## A. Component Inventory

| Component | Role | Classification |
|---|---|---|
| EquityScannerAI | Signal generation from Nifty 500 | CORE |
| KLPEvaluator | Knowledge observation + annotation | KNOWLEDGE |
| StrategyLab (StrategyGeneratorAI + BacktestingAI) | Strategy context + comparison | SHADOW/CONTEXT |
| KnowledgeDecisionPipeline | Intelligence authority orchestration | KNOWLEDGE |
| HistoricalBehaviourEngine (HBE) | Per-symbol historical behaviour profiles | KNOWLEDGE |
| KnowledgeFusionEngine (KFE) | Multi-angle evidence fusion | KNOWLEDGE |
| KnowledgeDecisionAuthority (KDA) | Knowledge decision engine | KNOWLEDGE |
| KDALedger | Decision persistence | KNOWLEDGE |
| KDAOutcomeEngine | Outcome measurement (EOD) | KNOWLEDGE |
| KDAComparativeAnalyzer | KDA vs StrategyLab comparison | KNOWLEDGE |
| KDAAuthorityReporter | Authority gate reporting | KNOWLEDGE |
| RejectionTracker | Rejection audit (Risk + StrategyLab) | KNOWLEDGE |
| CapitalRiskEngine | Capital allocation + exposure | RISK |
| RiskManagerAI | Heat-split risk veto | RISK |
| FailSafeRiskGuardian | Hard kill switch | RISK |
| MarketSimulation | Monte Carlo scenario validation | RISK |
| CorrelationEngine | Sector decorrelation | RISK |
| SmartExecutionEngine | Trade selection | RISK |
| DecisionEngine | Final paper approval (threshold 6.5) | CORE |
| MultiAgentDebate | 5-agent quality vote | CORE |
| OrderManager | Paper execution | CORE |
| KLPOutcomeEngine | KLP outcome fill (EOD) | KNOWLEDGE |
| MarketLearningCoordinator + AMLS | DNA + IDR + PIG learning | LEARNING |
| LearningEngine | EOD strategy learning | LEARNING |
| StrategyPerformanceTracker | Auto-disable underperforming strategies | LEARNING |
| PIGTradingAdapter | DNA-derived signal enrichment | CONTEXT |
| ResearchCoordinator | 8-stage research pipeline | RESEARCH |
| KSL-001 (run_klp_loop) | Knowledge evidence feedback | KNOWLEDGE |
| mop_rc001_observer | Expected move observation | RESEARCH |
| ILC runner | Institutional learning cycle | RESEARCH |
| OIOS pipeline | Market leader research | RESEARCH |
| IKN | Institutional knowledge network | RESEARCH |
| KDE | Knowledge discovery engine | RESEARCH |

---

## B. Purpose Alignment

Every component in the production path contributes to:

`SIGNAL → KNOWLEDGE → RISK VETO → EXECUTION → OUTCOME → VALIDATION → LEARNING → BETTER DECISION`

| Component | Primary Purpose | Decision Contribution |
|---|---|---|
| EquityScannerAI | Generate raw signals | Provides candidates |
| KDA | Intelligence authority | Directional decision |
| HBE | Historical evidence | Behaviour profile |
| KFE | Multi-source fusion | Angle-weighted evidence |
| StrategyLab | Backtest context | Shadow comparison only |
| RiskGuardian | Hard kill switch | Hard veto |
| CapitalRiskEngine | Exposure management | Capacity veto |
| DecisionEngine | Final quality gate | Threshold approval |
| OrderManager | Execution | Paper trade |
| KDAOutcomeEngine | Outcome measurement | Feeds next decision |

---

## C. Information Flow (key paths)

```
EquityScannerAI → TradeSignal → KLPEvaluator → KLP JSONL
TradeSignal → KnowledgeDecisionPipeline → (HBE + KFE) → KDADecisionRecord → KDALedger
KDA decision (KNOWLEDGE_BUY/SELL) → signal merged into enriched_signals → Risk → OrderManager
StrategyLab output → comparison only → kda_vs_stratlab JSONL
KDALedger (EOD) → KDAOutcomeEngine → KDAComparativeAnalyzer → KDAAuthorityReporter
KLP JSONL (EOD) → KLPOutcomeEngine → HBE.load_outcomes() → better profiles
rejection_audit.db → KFE (REJECTION_HISTORY angle) → better fusion
kda_authority_validation.json → Telegram /kda command
```

---

## D. Unconsumed Data

| Source | Status | Reason |
|---|---|---|
| `data/mop_rc001/` | RESEARCH_ONLY | Produced per signal; no active consumer in production pipeline |
| `data/ars/` (ResearchCoordinator) | RESEARCH_ONLY | Research pipeline output; not wired to production |
| `data/ikn/` (IKN) | RESEARCH_ONLY | Knowledge graph for future use; no production consumer |
| `kda_vs_stratlab JSONL` | WAIT_FOR_EVIDENCE | Written each cycle; consumer = EOD comparative (future when evidence accumulates) |
| `shadow_evidence_ledger.jsonl` | KNOWLEDGE | Read by KSL pattern miner and KFE |

---

## E. Unconnected Modules

| Module | Call Sites | Classification | Action |
|---|---|---|---|
| `ResearchCoordinator` | Research scripts only, NOT orchestrator | RESEARCH | KEEP_AS_CONTEXT |
| `IKNNetwork` | Research scripts only | RESEARCH | KEEP_AS_CONTEXT |
| `KDEEngine` | Research scripts only | RESEARCH | KEEP_AS_CONTEXT |
| `mop_rc001_observer` | EquityScannerAI (1 call site) | RESEARCH | KEEP_AS_CONTEXT |
| `run_klp_loop` | EOD orchestrator | KNOWLEDGE | CONNECTED |
| `ILCRunner` | EOD orchestrator | RESEARCH | CONNECTED |
| `MarketLearningCoordinator` | EOD orchestrator | LEARNING | CONNECTED |

---

## F. Duplicate Responsibility Resolution

| Responsibility | AUTHORITATIVE | FALLBACK | CONTEXT/SHADOW |
|---|---|---|---|
| Direction | **KDA** (KNOWLEDGE_BUY/SELL) | Scanner direction | StrategyLab direction |
| Signal generation | **EquityScannerAI** | — | — |
| Signal quality | **KDA evidence score** | Scanner confidence | StrategyLab backtest score |
| Strategy selection | **StrategyGeneratorAI** | — | (shadow comparison only) |
| Historical evidence | **HBE** | ATR fallback | — |
| Knowledge fusion | **KFE** | — | — |
| Target | **KDA empirical** (when VALIDATED/DECISION_ELIGIBLE) | ATR × RR | StrategyLab |
| Stop | **KDA empirical** (when VALIDATED/DECISION_ELIGIBLE) | ATR × stop mult | StrategyLab |
| Expected move | **KDA/HBE** (when evidence sufficient) | `ATR_FALLBACK` | MOP-RC-001 |
| Holding horizon | **HBE p50** (when evidence ≥ USEFUL) | `HORIZON_INSUFFICIENT` | — |
| Decision authority | **KDA** (when DECISION_ELIGIBLE) → **DecisionEngine** (threshold gate) | — | — |
| Position sizing | **CapitalRiskEngine** | — | — |
| Risk veto | **RiskGuardian** (hard kill) + **RiskManagerAI** (heat) | — | — |
| Execution | **OrderManager** | — | — |
| Outcome measurement | **KDAOutcomeEngine** (knowledge) + **KLPOutcomeEngine** (signal) | — | — |
| Learning | **LearningEngine** (strategy) + **KSL-001** (knowledge) | — | — |
| Regime classification | **RegimeProbabilityModel** | — | — |

---

## G. Data-Flow Problems (ARCH-002-R status)

| Flow | Status |
|---|---|
| KLP → HBE | CONNECTED — KLP JSONL outcomes flow via KLPOutcomeEngine + run_klp_loop |
| HBE → KFE | CONNECTED — HBE profiles consumed inside KDA; KFE uses rejection_audit for REJECTION_HISTORY |
| KFE → KDA | CONNECTED — KFE.analyse_record() feeds KDA.evaluate() |
| KDA → KDA Ledger | CONNECTED — _shadow_impl calls ledger.record() |
| KDA → Outcome Engine | CONNECTED — EOD _eod_impl calls outcome_e.evaluate() |
| Outcome → Comparative | CONNECTED — _eod_impl calls _comp.compare() |
| Comparative → Authority | CONNECTED — _eod_impl calls _reporter.generate_report() |
| Outcome → HBE/KFE learning | CONNECTED via run_klp_loop() → HBE.load_outcomes() |
| Risk rejection → RejectionTracker | CONNECTED — RiskManagerAI.filter_with_heat_split() |
| StrategyLab rejection → rejection_audit.db | CONNECTED — GAP-009 (ARCH-001) |
| LearningEngine → Knowledge | CONNECTED via MarketLearningCoordinator EOD |
| market_behavior.db → KFE | CONNECTED via market_behavior_adapter |
| paper execution → outcome learning | CONNECTED via paper_trades.csv → LearningEngine |
| **KDA → production decision path** | **CONNECTED — NEW (ARCH-002-R)** |
| **StrategyLab gate bypassed by KDA** | **IMPLEMENTED — NEW (ARCH-002-R)** |

---

## H. Fixes Implemented

### 1. KDA connected to production decision path (Part 2)
**Files:** `orchestrator/master_orchestrator.py`, `knowledge_authority/knowledge_decision_pipeline.py`  
**Change:** KDA runs on ALL scanner signals. Signals with `kda_decision = KNOWLEDGE_BUY/SELL` are added to `enriched_signals` even if StrategyLab rejected them (Phase 2 merge). Risk layers remain independent.

### 2. StrategyLab demoted to SHADOW/CONTEXT (Part 3)
**File:** `orchestrator/master_orchestrator.py`  
**Change:** StrategyLab output is now `_sl_signal_map`. After KDA runs, `enriched_signals` = merged(StrategyLab-approved + KDA-authorized). StrategyLab cannot block a KDA-authorized signal.

### 3. Target/stop authority (Part 5)
**File:** `orchestrator/master_orchestrator.py`  
**Change:** For KDA-authorized signals with evidence `VALIDATED` or `DECISION_ELIGIBLE` and no fallback: `target_price` and `stop_loss` are replaced with KDA empirical values. `target_source`, `stop_source` annotate origin.

### 4. Authorization metadata (Part 11)
**File:** `models/trade_signal.py`  
**Change:** 8 new optional fields: `authorization_source`, `kda_decision`, `kda_evidence_state`, `kda_target`, `kda_stop`, `kda_horizon_p50`, `target_source`, `stop_source`.

### 5. KDA vs StrategyLab comparison persisted (Part 3)
**File:** `orchestrator/master_orchestrator.py`  
**Change:** Each cycle writes `data/klp/kda/kda_vs_stratlab_YYYY-MM-DD.jsonl` with per-signal direction/confidence/target/approval from all three sources (scanner, StrategyLab, KDA).

---

## I. Fixes Not Implemented and Why

| Item | Reason |
|---|---|
| KDA live execution promotion | Requires PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED — deliberately excluded per spec |
| KDA replaces Debate agents | Debate is a quality gate, not a StrategyLab veto; no change needed |
| StrategyLab removal | Spec says DO NOT delete — kept as SHADOW/CONTEXT |
| Empirical target/stop with DEVELOPING evidence | Only VALIDATED/DECISION_ELIGIBLE: prevents premature overrides |
| ResearchCoordinator → production | RESEARCH_ONLY; no decision value without validation |

---

## J. Architecture Contract

See [ARCHITECTURE_CONTRACT_V1.md](ARCHITECTURE_CONTRACT_V1.md) (produced separately).

### Quick summary:
- **KDA** = intelligence authority (KNOWLEDGE_BUY/SELL = production authorization)
- **StrategyLab** = shadow context (runs, compares, cannot veto KDA)
- **Risk (RiskGuardian + RiskManagerAI + CapitalRiskEngine)** = independent safety veto
- **OrderManager** = paper execution (PAPER_TRADING=true enforced here)
- **Outcome** = KDAOutcomeEngine + KLPOutcomeEngine (separate scopes)
- **Learning** = KSL-001 (knowledge) + LearningEngine (strategy)

---

## K. Remaining Items

| Gap | Severity | Status |
|---|---|---|
| KDA needs ESS ≥ 100 for DECISION_ELIGIBLE | P3 | WAIT_FOR_EVIDENCE (30+ trading days of accumulation) |
| KDA direction accuracy ≥ 57% validation | P3 | VALIDATE_WITH_DATA |
| HBE needs 6+ outcomes per symbol | P3 | WAIT_FOR_EVIDENCE |
| ₹10,000 live experiment readiness | P2 | See readiness checklist below |
| Holding horizon (p50 from HBE) | P3 | WAIT_FOR_EVIDENCE (HBE evidence needed) |

---

## L. ₹10,000 Live Experiment Readiness Checklist

**DO NOT enable until all items pass.**

| # | Check | Current |
|---|---|---|
| 1 | Dhan authentication (token valid, non-expired) | ⚠️ token refresh needed |
| 2 | Static IP confirmed on VPS (not shared NAT) | ✅ dedicated VPS |
| 3 | Token auto-refresh before market open (08:59 IST) | ✅ /token command + hot-reload |
| 4 | Order submission (place_order returns valid order_id) | ❌ NOT TESTED live |
| 5 | Order status polling (order_id → FILLED / REJECTED) | ❌ NOT TESTED live |
| 6 | Fill quantity reconciliation (partial fills) | ❌ NOT TESTED |
| 7 | Average fill price reconciliation | ❌ NOT TESTED |
| 8 | Position reconciliation (Dhan positions = internal state) | ❌ NOT TESTED |
| 9 | Exit reconciliation (SL/target hit detected from Dhan) | ❌ NOT TESTED |
| 10 | Realized P&L calculation (fill price vs entry) | ❌ NOT TESTED live |
| 11 | Duplicate order prevention (same signal in 2 cycles) | ✅ dedup guard in OrderManager |
| 12 | Restart recovery (positions survive container restart) | ✅ paper_trades.csv + data/ volume |
| 13 | Network failure handling (reconnect + status recheck) | ⚠️ partial (data feed fallback exists) |
| 14 | Token expiry mid-session handling | ✅ /token hot-reload |
| 15 | Partial fill handling | ❌ NOT IMPLEMENTED in live path |
| 16 | Broker rejection handling (insufficient margin, SEBI block) | ❌ NOT TESTED |
| 17 | Kill-switch activated on VIX > 45 or loss > 2% | ✅ RiskGuardian |
| 18 | Capital limit enforced (₹10,000 ceiling) | ⚠️ TOTAL_CAPITAL in config must be set to 10000 |
| 19 | Maximum single position exposure (< 30% capital) | ✅ CapitalRiskEngine |
| 20 | KDA accuracy ≥ 57% on 30+ decisions before live | ❌ WAIT_FOR_EVIDENCE |

**Promotion condition for live:** ALL 20 items must pass AND PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED=true must be explicitly set by operator.

---

## M. Objective Alignment Score

| Objective | Status |
|---|---|
| Market data → Market understanding | ✅ GlobalIntelligence + MarketIntelligence |
| Market understanding → Signal observation | ✅ EquityScannerAI |
| Signal observation → Historical evidence | ✅ KLP + HBE |
| Historical evidence → Knowledge fusion | ✅ KFE |
| Knowledge fusion → Knowledge decision | ✅ KDA |
| Knowledge decision → Risk/safety | ✅ CapitalRisk + RiskGuardian |
| Risk/safety → Execution | ✅ OrderManager (paper) |
| Execution → Outcome | ✅ paper_trades.csv + OrderManager |
| Outcome → KDA validation | ✅ KDAOutcomeEngine + Comparative |
| Validation → Knowledge feedback | ✅ KSL-001 + run_klp_loop() |
| Knowledge feedback → Improved decision | 🔄 ACCUMULATING (needs ESS ≥ 100) |

**Score: 10/11 connected. 1 accumulating (evidence).**

---

## N. Production vs Knowledge vs Research Separation

```
PRODUCTION (runs every cycle, affects paper trades):
  EquityScannerAI → KLP → StrategyLab(context) → KDA → Risk → Debate → OrderManager

KNOWLEDGE SHADOW (runs every cycle, builds evidence):
  HBE + KFE + KDA + KDALedger + RejectionTracker + KLPEvaluator

KNOWLEDGE FEEDBACK (EOD only):
  KLPOutcomeEngine + KDAOutcomeEngine + KDAComparativeAnalyzer
  + KDAAuthorityReporter + run_klp_loop()

LEARNING (EOD only):
  LearningEngine + MarketLearningCoordinator + AMLS + DRE + ILC

RESEARCH (manual/offline):
  ResearchCoordinator + IKN + KDE + HKAP + mop_rc001_observer
```

---

## O. Safety Verification

| Invariant | Status |
|---|---|
| PAPER_TRADING=true | ✅ confirmed |
| LIVE_TRADING_AUTHORIZED absent | ✅ confirmed |
| broker_calls=0 (knowledge layer) | ✅ T15 passes |
| orders=0 (knowledge layer) | ✅ T16 passes |
| modifications=0 | ✅ T17 passes |
| cancellations=0 | ✅ T18 passes |
| KDA pipeline does not import execution_engine | ✅ T19 passes (AST check) |
| KDA execution_authority=False always | ✅ T12b passes |
| No live order can be submitted without LIVE_TRADING_AUTHORIZED | ✅ T19 passes |
| Both VPS containers Up (healthy) | ✅ confirmed |

---

## P. Test Results

| Suite | Tests | Result |
|---|---|---|
| KDA-001 | 100 | ✅ 100/100 |
| KDA-002 | 120 | ✅ 120/120 |
| KDA-003 | 38 | ✅ 38/38 |
| ARCH-001 | 56 | ✅ 56/56 |
| **ARCH-002-R** | **23** | **✅ 23/23** |
| **TOTAL** | **337** | **✅ 337/337** |

---

## Q. Commit + Deployment

| Item | Value |
|---|---|
| Commit | `afec1da` |
| Message | ARCH-002-R: KDA becomes intelligence authority; StrategyLab demoted to shadow/context |
| VPS deploy | Both containers `Up (healthy)` |
| PAPER_TRADING | `true` |
| LIVE_TRADING_AUTHORIZED | absent |

---

*Report: GitHub Copilot, ARCH-002-R, 2026-08-22*
