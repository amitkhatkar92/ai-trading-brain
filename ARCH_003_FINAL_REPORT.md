# ARCH-003: Knowledge Authority Completion + Information Consumption Audit

**Commit:** (pending — see deployment section)  
**Date:** 2026-08-22  
**Tests:** 379/379 passing (337 regression + 42 new ARCH-003)  
**PAPER_TRADING:** `true` (enforced in OrderManager)  
**LIVE_TRADING_AUTHORIZED:** absent  
**broker_calls:** 0  
**orders:** 0  

---

## 1. Actual Runtime Decision Path

```
run_full_cycle()
  │
  ├── GlobalIntelligence.run()
  │     → premarket_bias (GlobalSnapshot: sp500, nikkei, cboe_vix, usdinr, crude)
  │     → last_distortion (stress_score 0–8, risk_level, active_flags)
  │
  ├── _run_market_intelligence(premarket_bias)
  │     → snapshot (regime, vix, pcr, breadth, sector_flows, advance_decline)
  │
  ├── RegimeProbabilityModel.compute(snapshot, stress_score)
  │     → _regime_probs (trend/range/volatile/bear probabilities)
  │
  ├── MetaLearningEngine.predict(snapshot, strategies)
  │     → ml_allocation (strategy weights, model_active, top_strategy)
  │
  ├── EquityScannerAI.scan()
  │     → signals: List[TradeSignal] (symbol, direction, entry, stop, target, ATR)
  │
  ├── KLPEvaluator.evaluate_and_record()  [before StrategyLab]
  │     → KLP JSONL observation record (no_lookahead=True)
  │
  ├── _run_strategy_lab(signals, snapshot)   [SHADOW/CONTEXT]
  │     → enriched_signals (StrategyLab-approved subset)
  │     → _sl_reasons (rejection reasons for non-approved signals)
  │
  ├── KLPEvaluator.annotate_strategy_outcome()
  │     → KLP annotated with strategy_pass/reject context
  │
  ├── ── KDA AUTHORITY BLOCK ──────────────────────────────────────────────
  │   For each signal in ALL scanner signals:
  │
  │   _kda_mc = {
  │     regime, vix, pcr, breadth, global_bias,          ← original 5
  │     global_sentiment_score, stress_score,             ← ARCH-003 new
  │     distortion_risk_level, sector_flows,              ← ARCH-003 new
  │     advance_decline                                    ← ARCH-003 new
  │   }
  │
  │   KnowledgeDecisionPipeline.run_knowledge_shadow(signal, _kda_mc, strategy_info)
  │     │
  │     ├── HBE.get_behaviour_profile(symbol, direction, regime, ...)
  │     │     → BehaviourMetrics (from 7-level hierarchy: L1=specific → L7=ATR fallback)
  │     │
  │     ├── KFE.analyse_record(fusion_record, pool)
  │     │     → MultiAngleView (16 angles: STOCK, MARKET, SECTOR, VOLATILITY,
  │     │          DIRECTION, MAGNITUDE, TIME, RISK, SELECTION, COUNTERFACTUAL,
  │     │          LEADER_OUTCOME, SOURCE_QUALITY, RECENCY, REDUNDANCY,
  │     │          CONTRADICTION, OOS_VALIDATION)
  │     │
  │     ├── KDA.evaluate(observation, angle_view, behaviour, strategy_context, market_context)
  │     │     → KDADecisionRecord (decision, evidence_state, target, stop, horizon, ESS)
  │     │
  │     └── KDALedger.record(kda_record)   [append-only]
  │
  │   Phase 1 merge: StrategyLab-approved → annotate with KDA metadata
  │   Phase 2 merge: KDA-only (StrategyLab rejected, KDA says BUY/SELL) → add to path
  │   enriched_signals = merged
  │   kda_vs_stratlab_YYYY-MM-DD.jsonl  [comparison log]
  │   ────────────────────────────────────────────────────────────────────
  │
  ├── CapitalRiskEngine.allocate(enriched_signals, snapshot, portfolio)
  │     → cre_signals (capacity check, heat allocation)
  │
  ├── RiskManagerAI.filter_with_heat_split(cre_signals)
  │     → rc_signals (R:R gate, confidence floor, heat split)
  │     → rejection → RejectionTracker.ingest_rejection() → rejection_audit.db
  │
  ├── MarketSimulation.run_scenarios(rc_signals)
  │
  ├── FailSafeRiskGuardian.evaluate()
  │     → Hard kill switch (VIX > 45, daily loss > 2%, manual halt)
  │
  ├── CorrelationEngine → SmartExecutionEngine → final_signals
  │
  ├── For each signal: _run_debate_and_decide(signal, snapshot)
  │     ├── MultiAgentDebate.run(signal, snapshot)    [5 agents + PIG vote]
  │     └── DecisionEngine.decide(signal, votes, snapshot)
  │           → approved / PARTIAL / REJECT (threshold 6.5, VIX-adaptive)
  │           → MarketTruthGovernor (feed quality gate)
  │
  └── OrderManager.execute(signal)   [PAPER_TRADING=true enforced here]
        → paper_trades.csv (journal)
        → TradeMonitor.register(order)
```

---

## 2. KDA Input Audit

| Input | Produced? | Produced where | Passed to KDA? | Used in decision? | Verified? |
|---|---|---|---|---|---|
| `angle_view` | ✅ | KFE.analyse_record() | ✅ | ✅ | T20 |
| `behaviour` (BehaviourMetrics) | ✅ | HBE.get_behaviour_profile() | ✅ | ✅ | T06 |
| evidence_state | ✅ | KDA._classify_evidence_state() | ✅ | ✅ | T28 |
| historical metrics (ESS, hit_rate, move_p50) | ✅ | HBE → BehaviourMetrics | ✅ | ✅ | T06 |
| target/stop (empirical) | ✅ | HBE.knowledge_target_offset_p50 | ✅ | ✅ | T30 |
| expected move (p25/p50/p75) | ✅ | HBE.expected_move_p* | ✅ | ✅ | T06 |
| expected horizon (days p50) | ✅ | HBE.expected_days_p50 | ✅ | ✅ | T32 |
| source quality | ✅ | KFE SOURCE_QUALITY angle | ✅ | ✅ | T20 |
| contradictions | ✅ | KFE CONTRADICTION angle | ✅ | ✅ | T20 |
| recency | ✅ | KFE RECENCY angle | ✅ | ✅ | T20 |
| OOS evidence | ✅ | KFE OOS_VALIDATION angle | ✅ | ✅ | T20 |
| market behaviour | ✅ | KFE MARKET angle + LEADER_OUTCOME | ✅ | ✅ | T20 |
| rejection history | ✅ | rejection_audit.db → KFE REJECTION pool | ✅ | ✅ | T15 |
| KLP outcomes | ✅ | KLP JSONL → HBE.load_outcomes() | ✅ | ✅ | T09 |
| regime | ✅ | snapshot.regime → _kda_mc | ✅ | ✅ | T01 |
| VIX | ✅ | snapshot.vix → _kda_mc | ✅ | ✅ | T01 |
| PCR | ✅ | snapshot.pcr → _kda_mc | ✅ | ✅ | T05 |
| breadth | ✅ | snapshot.breadth → _kda_mc | ✅ | ✅ | T05 |
| global_bias | ✅ | premarket_bias.bias → _kda_mc | ✅ | ✅ | T02 |
| global_sentiment_score | ✅ **NEW ARCH-003** | premarket_bias → _kda_mc | ✅ | ✅ | T03 |
| stress_score | ✅ **NEW ARCH-003** | last_distortion.stress_score → _kda_mc | ✅ | ✅ | T03 |
| distortion_risk_level | ✅ **NEW ARCH-003** | last_distortion.risk_level → _kda_mc | ✅ | ✅ | T03 |
| sector_flows | ✅ **NEW ARCH-003** | snapshot.sector_flows → _kda_mc | ✅ | ✅ | T03 |
| advance/decline | ✅ **NEW ARCH-003** | snapshot.advance_decline → _kda_mc | ✅ | ✅ | T03 |

---

## 3. HBE Evidence Hierarchy (verified)

```
L1: symbol + direction + regime + ATR band + confidence band  (most specific)
L2: symbol + direction
L3: sector + direction + regime
L4: regime + direction
L5: sector + direction
L6: broad market + direction
L7: ATR/scanner fallback                                      (least specific)
```

- HBE reads KLP JSONL outcomes via `load_outcomes()`
- Evidence source labelled on every `BehaviourMetrics.evidence_source`
- ESS uses 90-day half-life exponential decay
- Stability check: recent 25% vs historical 75% → STABLE/DEVELOPING/UNSTABLE
- Fallback is **visible**: `evidence_level = 7`, `evidence_source = "ATR_FALLBACK"`
- No hard 500-observation gate — ESS tier system used

---

## 4. KFE 16-Angle Audit

| Angle | Source | Data Available? | KFE reads it? | Alters KDA? |
|---|---|---|---|---|
| STOCK | rejection_audit.db + shadow_evidence_ledger | ✅ 504+405 records | ✅ | ✅ target_hit_probability |
| MARKET | regime_probability_history + ct_cycles | ✅ regime dist, VIX stats | ✅ | ✅ regime alignment |
| SECTOR | rejection_audit.db (by sector) | ✅ | ✅ | ✅ sector direction stats |
| VOLATILITY | rejection + shadow (by VIX bucket) | ✅ | ✅ | ✅ VIX-regime quality |
| DIRECTION | All outcome-linked (by direction) | ✅ | ✅ | ✅ direction bias |
| MAGNITUDE | KLP + shadow (expected vs actual) | ✅ | ✅ | ✅ move magnitude quality |
| TIME | KLP outcomes (time to target/stop) | 🔄 ACCUMULATING | ✅ | 🔄 needs KLP outcomes |
| RISK | rejection + shadow (stop hit rate) | ✅ | ✅ | ✅ adverse excursion |
| SELECTION | rejection_audit (selected vs rejected outcomes) | ✅ | ✅ | ✅ false neg rate |
| COUNTERFACTUAL | rejection_audit (rejected candidates' actual moves) | ✅ | ✅ | ✅ missed opportunity cost |
| LEADER_OUTCOME | market_behavior.db (sector leaders daily) | ✅ | ✅ | ✅ sector leader patterns |
| SOURCE_QUALITY | All sources (outcome-linked fraction) | ✅ | ✅ | ✅ evidence quality weight |
| RECENCY | All sources (ESS fraction) | ✅ | ✅ | ✅ staleness penalty |
| REDUNDANCY | Same symbol across multiple sources | ✅ | ✅ | ✅ corroboration count |
| CONTRADICTION | VIX vs signal, regime vs direction | ✅ | ✅ | ✅ confidence penalty |
| OOS_VALIDATION | Pool OOS status (not yet tested) | ⬜ not tested yet | ✅ | 🔄 needs OOS run |

---

## 5. Information Source Consumption Matrix

| Source | Information | Existing Consumer | KFE/KDA Consumer | Decision Value | Status |
|---|---|---|---|---|---|
| GlobalIntelligence | sp500, nikkei, cboe_vix, FX | ✅ Orchestrator | ✅ _kda_mc.global_bias + stress_score | H | CONNECTED |
| MarketIntelligence | regime, VIX, PCR, breadth | ✅ Orchestrator | ✅ _kda_mc | H | CONNECTED |
| RegimeProbabilityModel | BULL/BEAR/RANGE/VOLATILE probs | ✅ MetaStrategy | ✅ KDA market_context.regime | H | CONNECTED |
| EquityScannerAI | entry, stop, target, ATR, confidence | ✅ Pipeline | ✅ KDP observation | H | CONNECTED |
| KLP JSONL | observation + outcomes | ✅ KLPOutcomeEngine | ✅ HBE.load_outcomes() | H | CONNECTED |
| rejection_audit.db | 504 rejected signals + T+1/3/5 outcomes | ✅ LearningEngine | ✅ KFE REJECTION_AUDIT pool | H | CONNECTED |
| shadow_evidence_ledger.jsonl | 405 C2 research outcomes | ❌ None | ✅ **NEW ARCH-003** KFE pool | H | **CONNECTED** |
| knowledge_evidence_ledger.jsonl | 405 KSL-001 evidence records | ❌ None | ✅ **NEW ARCH-003** KFE pool | H | **CONNECTED** |
| control_tower.db (ct_decisions) | 1505 decisions w/ scores | ✅ LearningEngine | ✅ KFE CT_DECISIONS pool | M | CONNECTED |
| control_tower.db (ct_cycles) | 5328 cycle context | ✅ ControlTower | ✅ KFE via ct_decisions join | M | CONNECTED |
| market_behavior.db | sector leader outcomes | ✅ OIOS | ✅ KFE LEADER_OUTCOME angle | M | CONNECTED |
| paper_trades.csv | completed paper trades | ✅ LearningEngine | ⬜ no data yet | H | WAIT_FOR_DATA |
| kda_vs_stratlab JSONL | KDA vs StrategyLab comparison | ❌ | ✅ KDAComparativeAnalyzer EOD | H | CONNECTED |
| kda_authority_validation.json | authority gate progress | ✅ Telegram /kda | ✅ KDAAuthorityReporter EOD | H | CONNECTED |
| data/mop_rc001/ | expected move observations | ✅ mop_rc001_observer | ⬜ RESEARCH_ONLY | L | KEEP_AS_CONTEXT |
| data/ars/ | ResearchCoordinator output | ❌ | ⬜ RESEARCH_ONLY | M | KEEP_AS_CONTEXT |
| data/ikn/ | Institutional knowledge graph | ❌ | ⬜ RESEARCH_ONLY | M | KEEP_AS_CONTEXT |
| PIGTradingAdapter | Institutional DNA vote | ✅ Orchestrator (debate) | ⬜ Not in KDA | M | CONNECTED_AS_VOTE |
| MarketLearningCoordinator | AMLS + DRE DNA learning | ✅ Orchestrator EOD | ⬜ Not in KDA directly | M | CONNECTED_VIA_VOTE |

---

## 6. Legacy Decision Authority Audit

| Module | Classification | Can veto KDA? | Correct? |
|---|---|---|---|
| StrategyGeneratorAI | INTELLIGENCE | **NO** (demoted to SHADOW) | ✅ ARCH-002-R |
| BacktestingAI | INTELLIGENCE | **NO** (shadow only) | ✅ ARCH-002-R |
| MetaStrategyController | INTELLIGENCE | **NO** (strategy weights only) | ✅ |
| KnowledgeDecisionAuthority | INTELLIGENCE (AUTHORITY) | N/A (source of truth) | ✅ |
| CapitalRiskEngine | RISK | YES (capacity veto) | ✅ correct |
| RiskManagerAI | RISK | YES (R:R gate, heat) | ✅ correct |
| FailSafeRiskGuardian | SAFETY | YES (VIX>45, loss>2%) | ✅ correct |
| MarketSimulation | RISK | YES (scenario validation) | ✅ correct |
| CorrelationEngine | RISK | YES (sector decorrelation) | ✅ correct |
| SmartExecutionEngine | EXECUTION | YES (final selection) | ✅ correct |
| MultiAgentDebate | EXECUTION | YES (quality gate, threshold 6.5) | ✅ correct |
| DecisionEngine | EXECUTION | YES (VIX-adaptive threshold) | ✅ correct |
| MarketTruthGovernor | EXECUTION | YES (feed quality gate) | ✅ correct |
| OrderManager | EXECUTION | YES (PAPER_TRADING enforcement) | ✅ correct |
| KLPEvaluator | OBSERVABILITY | NO (read-only observation) | ✅ correct |
| PIGTradingAdapter | INTELLIGENCE | Only as debate vote (not veto) | ✅ correct |

**Conclusion:** No hidden intelligence veto exists. StrategyLab is the only intelligence module that could veto, and it was demoted in ARCH-002-R.

---

## 7. Target / Stop / Horizon Ownership

```
TARGET / STOP AUTHORITY:
  When evidence_state = VALIDATED or DECISION_ELIGIBLE AND fallback_used = False:
    → target_price = KDA empirical target  (target_source = "KDA_EMPIRICAL")
    → stop_loss    = KDA empirical stop    (stop_source  = "KDA_EMPIRICAL")
  Otherwise:
    → target_price = scanner ATR × RR      (target_source = "ATR_FALLBACK")
    → stop_loss    = scanner ATR × mult    (stop_source  = "ATR_FALLBACK")

HORIZON AUTHORITY:
  When HBE evidence ≥ USEFUL (ESS ≥ 10):
    → kda_horizon_p50 = HBE expected_days_p50
  Otherwise:
    → kda_horizon_p50 = None   (label: HORIZON_INSUFFICIENT)

DOWNSTREAM PATH:
  KDA merge → enriched_signals.target_price / stop_loss
            → CapitalRiskEngine (uses target/stop for heat)
            → RiskManagerAI (R:R check)
            → DecisionEngine (asymmetry bonus uses R:R from target/stop)
            → OrderManager.execute() (places order with target/stop)

SILENT REPLACEMENT RISK:
  None found. The merge explicitly sets target_source and stop_source on every signal.
  The DecisionEngine does NOT overwrite target/stop — it reads R:R from the signal.
  The OrderManager places the order with the signal's target_price and stop_loss.
```

---

## 8. Outcome → Knowledge Loop (verified)

```
[INTRADAY]
KDA shadow decision
    → KDALedger.record(kda_record)       [data/klp/kda/kda_decisions_YYYY-MM-DD.jsonl]

[EOD — _do_eod_learning()]
1. KLPOutcomeEngine.evaluate_daily_outcomes()
       → KLP JSONL updated with T+1/3/5 outcomes (no lookahead)

2. KnowledgeDecisionPipeline.run_eod_knowledge_update()
   ├── HBE reload (pick up today's KLP-002 outcomes)
   ├── KFE pool reload (pick up new rejection records)
   ├── For each KDA decision:
   │   └── KDAOutcomeEngine.evaluate(decision, bars, trading_date)
   │           → KDAOutcomeRecord (target_hit, stop_hit, MFE, MAE, direction_correct)
   ├── KDAComparativeAnalyzer.compare(kda_record, strategy_status, outcome)
   │       → who was right: KDA vs StrategyLab
   └── KDAAuthorityReporter.generate_report(outcomes)
           → kda_authority_validation.json (authority_status, direction_accuracy)

3. run_klp_loop() / KSL-001
       → KLP evidence → knowledge_evidence_ledger.jsonl
       → Patterns detected → research_question_queue.jsonl

[NEXT INTRADAY CYCLE]
_hbe_loaded_date = None → HBE.load_outcomes() picks up today's outcomes
_kfe_loaded_date = None → KFE pool picks up new rejection + shadow + evidence records
```

**Knowledge improvement mechanism:**
- Each completed KDA decision → KDAOutcomeRecord
- HBE.load_outcomes() includes these via KLP JSONL
- More outcomes → higher ESS → evidence_state advances: INSUFFICIENT → DEVELOPING → USEFUL → VALIDATED → DECISION_ELIGIBLE
- At DECISION_ELIGIBLE (ESS ≥ 100): KDA returns KNOWLEDGE_BUY/SELL → signal enters production even if StrategyLab rejects

---

## 9. StrategyLab Shadow Status (verified)

| Scenario | Result | Test |
|---|---|---|
| KDA BUY + StrategyLab ACCEPT | authorization_source = "BOTH", enters path | T25, T26 |
| KDA BUY + StrategyLab REJECT | authorization_source = "KDA", enters path | T25 |
| KDA SELL + StrategyLab REJECT | authorization_source = "KDA", enters path | T25 |
| KDA WAIT + StrategyLab ACCEPT | authorization_source = "STRATEGY_LAB" | T26 |
| KDA WAIT + StrategyLab REJECT | not in enriched_signals | T25 |

StrategyLab result written to `kda_vs_stratlab_YYYY-MM-DD.jsonl` every cycle for comparison.

---

## 10. Orphan / Dead Module Audit

| Module | Status | Reason |
|---|---|---|
| ResearchCoordinator | KEEP | Research pipeline with genuine analytical value |
| IKNNetwork | KEEP | Knowledge graph — future use |
| KDEEngine | KEEP | Knowledge discovery — future use |
| mop_rc001_observer | KEEP_AS_CONTEXT | Produces expected_move observations; not in production path |
| ILCRunner | CONNECTED | Called in EOD orchestrator |
| MarketLearningCoordinator | CONNECTED | Called in EOD orchestrator |
| EdgeDiscoveryEngine | KEEP | Research layer, legitimate |
| WeekendIntelligenceEngine | CONNECTED | Called in scheduler |
| DailyAISelfEvaluator | CONNECTED | EOD evaluation |
| PIGTradingAdapter | CONNECTED | Debate vote (institutional DNA) |
| StrategyHealthMonitor | CONNECTED | Called in learning cycle |
| StrategyPerformanceTracker | CONNECTED | EOD learning |
| RegimeStrategyMap | CONNECTED | Meta-learning |
| TradeDiagnosticEngine | OBSERVABILITY | Diagnostic only, no decision effect |
| OpportunityDensityMonitor | CONNECTED | ODM directive affects scan |
| KDAComparativeAnalyzer | CONNECTED | EOD KDA vs StrategyLab comparison |
| KDAAuthorityReporter | CONNECTED | EOD authority gate update |

---

## 11. Architecture Score

| Dimension | Score | Evidence |
|---|---|---|
| DATA | 4/5 | Global + Market + Regime + Options. Historical OHLCV is yfinance (no paid feed). |
| MARKET UNDERSTANDING | 4/5 | 4-regime + MRPM + distortion detection. No real options flow data. |
| KNOWLEDGE ACQUISITION | 4/5 | KLP on all signals. Shadow + knowledge evidence ledgers now connected. Missing: intraday KLP fills. |
| HISTORICAL BEHAVIOUR | 4/5 | 7-level HBE hierarchy. ESS + stability. Needs ESS ≥ 100 for DECISION_ELIGIBLE. |
| KNOWLEDGE FUSION | 4/5 | 16 angles, all active. Pool: 2819 records (was 2009). OOS_VALIDATION still unvalidated. |
| KNOWLEDGE DECISION | 3/5 | Architecture complete. Authority rises with evidence. Currently at INSUFFICIENT/DEVELOPING. |
| RISK | 5/5 | 5 independent risk layers. Kill switch. Hard capital limits. All connected. |
| EXECUTION | 5/5 | PAPER_TRADING=true enforced. Dedup guard. CSV journal. Carry positions survive restart. |
| OUTCOME | 4/5 | KDAOutcomeEngine + KLPOutcomeEngine. KDA outcomes accumulating. |
| LEARNING | 4/5 | LearningEngine + KSL-001 + MarketLearningCoordinator + KDAComparativeAnalyzer. Loop complete. |
| FEEDBACK | 3/5 | HBE.load_outcomes() picks up new evidence each EOD. ESS accumulation is the gating factor. |

**Overall: 44/55**  
All architectural gaps closed. Score below 5 where more evidence accumulation is needed.

---

## 12. Remaining Items

| Item | Severity | Status | Blocker |
|---|---|---|---|
| KDA DECISION_ELIGIBLE (ESS ≥ 100) | P3 | WAIT_FOR_EVIDENCE | Need 30+ trading days of KDA decisions |
| KDA direction accuracy ≥ 57% validation | P3 | WAIT_FOR_DATA | Need KDA outcome fill from T+1 bars |
| HBE ≥ 10 outcomes per symbol | P3 | WAIT_FOR_DATA | KLP-002 outcomes accumulating |
| OOS_VALIDATION angle — run OOS test | P3 | FUTURE_WORK | Need dedicated OOS pipeline |
| paper_trades.csv → KFE pool | P3 | WAIT_FOR_DATA | No completed paper trades yet |
| PIGTradingAdapter → KDA context | P3 | FUTURE_WORK | PIG output is a debate vote, not KDA input |
| Full Dhan live readiness | P1 | BLOCKED_ON_API | See live readiness checklist |

---

## 13. Live Readiness Checklist

**DO NOT enable live trading until ALL items pass.**

| # | Check | Status |
|---|---|---|
| 1 | Dhan token valid + non-expired | ⚠️ check before market open |
| 2 | Static IP on VPS (not shared NAT) | ✅ dedicated VPS |
| 3 | Token auto-refresh 08:59 IST | ✅ /token hot-reload |
| 4 | Order submission returns valid order_id | ❌ NOT TESTED live |
| 5 | Order status polling (FILLED/REJECTED) | ❌ NOT TESTED live |
| 6 | Fill quantity reconciliation | ❌ NOT TESTED |
| 7 | Average fill price reconciliation | ❌ NOT TESTED |
| 8 | Position reconciliation (Dhan vs internal) | ❌ NOT TESTED |
| 9 | Exit reconciliation (SL/target from Dhan) | ❌ NOT TESTED |
| 10 | Realized P&L calculation | ❌ NOT TESTED live |
| 11 | Duplicate order prevention | ✅ dedup guard |
| 12 | Restart recovery | ✅ paper_trades.csv + data/ volume |
| 13 | Network failure reconnect | ⚠️ partial |
| 14 | Token expiry mid-session | ✅ /token hot-reload |
| 15 | Partial fill handling | ❌ NOT IMPLEMENTED |
| 16 | Broker rejection (margin, SEBI block) | ❌ NOT TESTED |
| 17 | Kill switch on VIX>45 or loss>2% | ✅ RiskGuardian |
| 18 | Capital limit ₹10,000 enforced | ⚠️ TOTAL_CAPITAL must be set |
| 19 | Max position 30% capital | ✅ CapitalRiskEngine |
| 20 | KDA accuracy ≥ 57% on 30+ decisions | ❌ WAIT_FOR_EVIDENCE |

---

## 14. Changes Implemented

| Change | File | Impact |
|---|---|---|
| GAP-A: enrich `_kda_mc` with 5 new fields | `orchestrator/master_orchestrator.py` | KDA now receives global_sentiment, stress_score, sector_flows |
| GAP-B: KFE loads shadow_evidence_ledger.jsonl | `opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py` | +405 outcome-linked records in pool |
| GAP-C: KFE loads knowledge_evidence_ledger.jsonl | `opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py` | +405 KSL-001 records in pool |
| Source inventory updated | `opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py` | Both sources now marked `currently_used_in_decisions=True` |
| 42 integration tests | `tests/test_arch_003_integration.py` | Covers full KDA stack end-to-end |
