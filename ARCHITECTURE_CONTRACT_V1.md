# ARCHITECTURE CONTRACT V1

**Effective from commit:** `afec1da`  
**Date:** 2026-08-22  
**Status:** ACTIVE

This document is the authoritative reference for future development.  
Any change that contradicts a rule in this contract requires an explicit architecture decision.

---

## 1. Signal Generation

**AUTHORITATIVE OWNER:** `EquityScannerAI`  
**Source:** `opportunity_engine/equity_scanner_ai.py`  
**Output:** `List[TradeSignal]` with scanner direction, entry, stop, target, ATR  
**Fallback:** None (if scanner returns empty → cycle aborts)  
**Failure:** Empty list → cycle ends at OpportunityEngine

---

## 2. Signal Quality Assessment

**AUTHORITATIVE OWNER:** KDA knowledge_authority_score + evidence_state  
**Fallback:** Scanner `confidence` (0–10)  
**Shadow/Context:** StrategyLab `confidence` (backtest-derived)

---

## 3. Historical Evidence

**AUTHORITATIVE OWNER:** `HistoricalBehaviourEngine` (HBE)  
**Source:** `opportunity_engine/historical_behaviour_engine.py`  
**Input:** KLP outcomes (via KLPOutcomeEngine + run_klp_loop)  
**Output:** `BehaviourProfile` with `BehaviourMetrics` per symbol+direction+regime  
**Evidence tiers:** Tier 0 (0–9 obs) → Tier 6 (500+ obs). Tier ≥ 3 (50+ obs) = USEFUL.  
**Fallback:** Sector → Regime → Broad market → ATR fallback  
**No-lookahead:** Outcomes loaded only from T+1 onward. Never uses intraday data.

---

## 4. Knowledge Fusion (Multi-Angle Evidence)

**AUTHORITATIVE OWNER:** `KnowledgeFusionEngine` (KFE)  
**Source:** `opportunity_engine/knowledge_fusion/knowledge_fusion_engine.py`  
**Inputs:** rejection_audit.db, ct_decisions, regime_history, shadow_evidence_ledger, market_behavior.db, KLP JSONL  
**Output:** `MultiAngleView` with per-angle confidence and overall_signal  
**Failure:** Returns minimal view with 0 angles — KDA proceeds with HBE only

---

## 5. Knowledge Decision (Intelligence Authority)

**AUTHORITATIVE OWNER:** `KnowledgeDecisionAuthority` (KDA)  
**Source:** `knowledge_authority/knowledge_decision_authority.py`  
**Inputs:** HBE BehaviourMetrics + KFE MultiAngleView + signal observation + market context  
**Output:** `KDADecisionRecord` with decision, authority, evidence_state, target, stop, horizon  
**Decisions:** KNOWLEDGE_BUY | KNOWLEDGE_SELL | KNOWLEDGE_HOLD | KNOWLEDGE_WAIT | KNOWLEDGE_EXIT  
**Authority thresholds:**
- `DECISION_ELIGIBLE` (ESS ≥ 100): KDA = full intelligence authority
- `VALIDATED` (ESS 30–99): KDA = strategy context authority
- `USEFUL` (ESS 10–29): KDA = informational
- `DEVELOPING` (ESS 3–9): KDA returns KNOWLEDGE_WAIT
- `INSUFFICIENT` (ESS < 3): KDA returns KNOWLEDGE_WAIT

**Production routing rule:**
- `KNOWLEDGE_BUY` or `KNOWLEDGE_SELL` → signal enters production path (bypasses StrategyLab gate)
- All other decisions → StrategyLab result determines routing

---

## 6. StrategyLab Role (SHADOW/CONTEXT)

**CURRENT ROLE:** Shadow / Context / Comparison  
**Source:** `strategy_lab/strategy_generator_ai.py`, `strategy_lab/backtesting_ai.py`  
**CANNOT:** Block a KDA-authorized signal  
**CAN:** Provide strategy_name, backtest_score, comparison data  
**Output persisted to:** `data/klp/kda/kda_vs_stratlab_YYYY-MM-DD.jsonl`  
**Promotion condition:** StrategyLab may regain gate authority only when KDA accumulates evidence that StrategyLab materially outperforms KDA on a per-regime basis. Requires explicit architecture decision.

---

## 7. Target / Stop Authority

| Evidence State | Target | Stop | source annotation |
|---|---|---|---|
| DECISION_ELIGIBLE or VALIDATED (not fallback) | KDA empirical | KDA empirical | `KDA_EMPIRICAL` |
| All other cases | Scanner ATR × RR | Scanner ATR × mult | `ATR_FALLBACK` |

**Persist:** `target_source`, `stop_source` on every `TradeSignal`.  
**No silent competition:** Only one value in `target_price` / `stop_loss` at execution time.

---

## 8. Holding Horizon Authority

**AUTHORITATIVE OWNER:** HBE (via KDA `expected_days_p50`)  
**When:** Evidence ≥ USEFUL (ESS ≥ 10)  
**Values:** p25 / p50 / p75 from observed outcome distribution  
**When insufficient:** `kda_horizon_p50 = None`, label = `HORIZON_INSUFFICIENT`  
**Rule:** Do NOT invent horizon labels (INTRADAY/SWING) from scanner data alone.

---

## 9. Risk Veto (Independent Safety Layer)

**AUTHORITATIVE OWNERS:**
- `CapitalRiskEngine` — position count, exposure, heat allocation
- `RiskManagerAI` — heat-split filter, R:R gate, confidence floor
- `FailSafeRiskGuardian` — hard kill switch (VIX > 45, daily loss > 2%)
- `CorrelationEngine` — sector decorrelation
- `SmartExecutionEngine` — final selection

**Rule:** Risk layers may block any signal, including KDA-authorized ones.  
**Rule:** Risk layers are NOT StrategyLab replacements.  
**Rule:** Risk layers must not be circumvented to promote KDA output.

---

## 10. Execution Authority

**AUTHORITATIVE OWNER:** `OrderManager`  
**Source:** `execution_engine/order_manager.py`  
**Execution mode:**
- `PAPER_TRADING=true` → paper trade (no Dhan API calls)
- `PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED=true` → live Dhan order
- `PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED absent` → forced back to paper

**Rule:** KDA CANNOT enable live execution. Only OrderManager reads the flags.  
**Rule:** `broker_calls=0, orders=0` must remain true in all knowledge components.

---

## 11. Outcome Measurement

| Scope | Owner | Source |
|---|---|---|
| Signal-level outcomes (T+1 to T+5) | `KLPOutcomeEngine` | `data/klp/KLP_YYYY-MM-DD.jsonl` |
| KDA decision outcomes (target/stop/MFE/MAE) | `KDAOutcomeEngine` | `data/klp/kda/kda_decisions_*.jsonl` |

**Rule:** These are separate scopes. Do not merge them.  
**No-lookahead:** Both engines use only bars from T+1 onward. Never use T+0 bars for outcome.

---

## 12. Learning Authority

| Type | Owner | Reads | Writes | When |
|---|---|---|---|---|
| Strategy performance | `StrategyPerformanceTracker` | closed trades | `strategy_performance.json` | EOD |
| EOD pattern mining | `LearningEngine` | rejection_audit.db, paper_trades.csv | `reports/learning/` | EOD |
| DNA / market learning | `MarketLearningCoordinator` | AMLS + DRE + IDR | institutional_dna.db | EOD |
| Knowledge evidence | `run_klp_loop` (KSL-001) | KLP JSONL + outcomes | `knowledge_evidence_ledger.jsonl` | EOD |

**Rule:** Do NOT create another learning subsystem. Route to one of the above.

---

## 13. Regime Classification

**AUTHORITATIVE OWNER:** `RegimeProbabilityModel` (MRPM) blended with `MetaLearningEngine`  
**Output:** Per-strategy weights used by StrategyGeneratorAI and KDA context

---

## 14. Knowledge Feedback Path

```
KDAOutcomeEngine (EOD)
→ KDAComparativeAnalyzer  (KDA vs StrategyLab outcome comparison)
→ KDAAuthorityReporter    (authority gate: NOT_VALIDATED → DEVELOPING → VALIDATED)
→ kda_authority_validation.json
→ Telegram /kda command (operator visibility)

KLPOutcomeEngine (EOD)
→ run_klp_loop() / KSL-001
→ knowledge_evidence_ledger.jsonl
→ HBE.load_outcomes()
→ Improved BehaviourMetrics for next cycle
```

---

## 15. Shadow / Live Boundary

| Layer | Shadow (paper) | Live |
|---|---|---|
| KDA decision | Always shadow_only=True in pipeline | N/A (KDA never touches execution) |
| OrderManager | `PAPER_TRADING=true` → paper journal | Requires both flags explicitly set |
| Dhan broker | Never called during paper mode | Only when both flags + LIVE_TRADING_AUTHORIZED |
| Risk | Always active | Always active |

---

## 16. Authority Promotion Rule

KDA may be granted live execution authority ONLY when:

1. ESS ≥ 100 per regime per direction (DECISION_ELIGIBLE)
2. Direction accuracy ≥ 57% on 30+ validated decisions
3. Target hit rate ≥ 40% with ATR fallback
4. Paper-mode P&L positive over 60 trading days
5. All 20 readiness checklist items pass (see ARCH_002_REVISED_FINAL_REPORT.md)
6. Operator explicitly sets `PAPER_TRADING=false` AND `LIVE_TRADING_AUTHORIZED=true`

No code change may automate this promotion. It requires a human operator decision.

---

## 17. No-Lookahead Rule

All outcome computations (KLPOutcomeEngine, KDAOutcomeEngine) must:
- Use ONLY bars from T+1 onward relative to decision/signal date
- Never use T+0 (same-day) prices for target/stop detection
- Tag every record with `no_lookahead=True`

---

## 18. Data Freshness Rule

| Source | Max acceptable age |
|---|---|
| market_behavior.db | 2 days (weekend gap allowed) |
| rejection_audit.db | 1 day |
| KLP JSONL | Same trading session |
| HBE profiles | Same trading day (reloaded lazily) |
| KDA decisions | Same trading session |
| kda_authority_validation.json | Updated each EOD |

---

## 19. Failure Behaviour

| Component | On failure |
|---|---|
| KDA pipeline exception | Returns `KNOWLEDGE_PIPELINE_ERROR`; `enriched_signals` unchanged |
| HBE load failure | Returns ATR fallback profile |
| KFE load failure | Returns empty MultiAngleView (0 angles) |
| KDA decision exception | Returns KNOWLEDGE_WAIT record |
| Risk Guardian block | Cycle aborts; no orders placed |
| OrderManager exception | Logs error; no order placed |

---

*Contract version 1.0 — ARCH-002-R, commit `afec1da`, 2026-08-22*
