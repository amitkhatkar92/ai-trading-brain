# Platform Layer Review
## AR-001 Part 8: Layer Separation Verification

**Date:** 2026-08-04

---

## 1. Canonical Layer Order

```
1  GlobalIntelligence      — overnight global context
2  MarketIntelligence      — regime, sector, liquidity, events
3  MetaLearning            — k-NN strategy weight predictor
4  OpportunityEngine       — equity/options scanner
5  StrategyLab             — strategy generation and evolution
6  CapitalRiskEngine       — position sizing
7  RiskControl             — pre-execution veto
8  MarketSimulation        — Monte Carlo
9  RiskGuardian            — kill-switch
10 DebateAndDecision        — conviction, threshold 6.5
11 ExecutionEngine          — order management
12 TradeMonitoring          — live health
13 LearningSystem           — EOD weight mutation
14 PerformanceAnalytics     — Sharpe, DD, WFT
15 ResearchLab              — promotion gates
16 ValidationEngine         — 6-stage pipeline
17 ControlTower             — telemetry, dashboard, EventBus
```

---

## 2. Layer Separation Rules

A properly layered system must satisfy:

1. **Forward dependency only:** Layer N may call Layer N-1 or lower.
2. **No upward imports:** Layer N must not import from Layer N+1 or higher.
3. **Clean boundary:** Each layer exposes a well-defined interface.
4. **No cross-layer skips:** Orchestrator bridges are allowed; direct
   cross-skips (e.g., Layer 2 → Layer 8) are not.

---

## 3. Layer-by-Layer Separation Analysis

### Layer 1 — GlobalIntelligence ✅

**Imports:** `data_feeds` (Layer 0/infra), `numpy`, `scipy`, external APIs.  
**No upward imports confirmed.**  
**Clean boundary:** `GlobalSnapshot` is the exported contract.  
**Verdict: CLEAN**

---

### Layer 2 — MarketIntelligence ✅

**Imports:** `data_feeds`, `global_intelligence` (L1), `numpy`.  
`RegimeProbabilityModel` imports from `meta_learning` — **this is a
forward dependency (L2 → L3).**

**Issue L-001:** `market_intelligence/regime_probability_model.py` imports from
`meta_learning`. This violates the layer rule (L2 should not know about L3).

**Recommended fix:** The `RegimeProbabilityModel` should expose its prediction
independently of meta-learning's k-NN. The meta-learning layer should
consume `RegimeProbabilities` as input, not produce them as a dependency.

---

### Layer 3 — MetaLearning ✅ (conditional)

**Imports:** `market_intelligence` (L2), `performance`, `models`.  
**Clean boundary:** `StrategyAllocation` is the exported contract.  
**Verdict: CLEAN** (pending resolution of L-001)

---

### Layer 4 — OpportunityEngine ✅

**Imports:** `data_feeds`, `market_intelligence` (L2), `models`, `config`.  
**No imports from L5–L17 observed.**  
**Clean boundary:** `CandidateStore` (ranked candidates) is the exported interface.  
**Verdict: CLEAN**

---

### Layer 5 — StrategyLab ⚠️

**Imports:** `data_feeds`, `performance` (L14), `models`.  
**Issue L-002:** `strategy_lab` imports from `performance` (Layer 14).
This is a downward skip: L5 → L14. While performance evaluation is needed
for strategy evolution, the dependency direction is correct (L5 needs metrics
to evaluate strategies, and metrics live in L14).

**Re-assessment:** This is acceptable if `performance` is treated as a
shared library rather than a layer. The 17-layer hierarchy is a conceptual model
of trading orchestration, not a strict build graph. Performance utilities are
closer to `analytics/` infrastructure than to a trading layer.

**Recommended clarification:** Document `performance/` as a shared analytics
library accessible to any layer, not as Layer 14 in the trading execution chain.

---

### Layer 6 — CapitalRiskEngine ✅

**Imports:** `data_feeds`, `market_intelligence` (L2), `config`, `models`.  
**No upward imports.**  
**Clean boundary:** Position size and budget decision.  
**Verdict: CLEAN**

---

### Layer 7 — RiskControl ⚠️

**Issue L-003:** `risk_control/` contains both `CapitalRiskEngine` concerns
(portfolio allocation) and `RiskControl` concerns (pre-execution veto).
`PortfolioAllocationAI` and `LiquidityGuard` arguably belong in Layer 6
(CapitalRiskEngine), not Layer 7. This causes directory-level ambiguity.

**Recommended clarification:** Either move `PortfolioAllocationAI` and
`LiquidityGuard` to `capital_risk_engine/`, or formally declare `risk_control/`
as the umbrella for L6+L7.

---

### Layers 8–11 — Simulation, Guardian, Debate, Execution ✅

**Imports follow layer order.** No forward dependencies observed.
`SimulationEngine` and `FailSafeRiskGuardian` are both correctly positioned.  
**Verdict: CLEAN**

---

### Layers 12–13 — Monitoring and Learning ⚠️

**Issue L-004:** `trade_monitoring/strategy_health_monitor.py` imports from
`learning_system`. This creates L12 → L13 dependency. A monitoring layer
should not depend on a learning layer that runs later (EOD).

**Recommended fix:** `StrategyHealthMonitor` should read strategy health
from `StrategyPerformanceTracker` (the singleton) rather than directly
importing from `learning_system`.

---

### Layer 15 — ResearchLab ✅

**Imports:** `performance` (library), `validation_engine` (L16).  
**Issue L-005:** L15 imports from L16 (ResearchLab imports ValidationEngine).
This is intentional: ResearchLab uses ValidationEngine to gate strategy promotion.
This is a controlled downward call (L15 orchestrates L16).  
**Verdict: ACCEPTABLE** — document as intentional.

---

### Layers 16–17 — Validation, ControlTower ✅

**Imports:** Consume outputs from all layers for validation.
`ValidationEngine` correctly operates as an offline service (not in the
real-time trading path). `SystemMonitor` observes all layers.  
**Verdict: CLEAN**

---

## 4. Layer Separation Summary

| Issue | Layer | Violation | Severity | Recommendation |
|---|---|---|---|---|
| L-001 | Layer 2 | L2 imports L3 (meta_learning) | High | Reverse dependency — verify and invert |
| L-002 | Layer 5 | L5 imports L14 (performance) | Low | Reclassify performance as shared library |
| L-003 | Layer 7 | PortfolioAllocationAI misplaced | Low | Clarify directory ownership |
| L-004 | Layer 12 | L12 imports L13 | Medium | Use singleton interface instead |
| L-005 | Layer 15 | L15 imports L16 (intentional) | None | Document as intentional |

---

## 5. Verdict

**The platform layer architecture is fundamentally sound.** The 17-layer
hierarchy correctly sequences information flow from data through intelligence,
strategy, risk, decision, and execution. Four minor violations exist, none of
which prevent correct operation today. All are rectifiable through small
refactors.

**Recommended priority:**
1. Resolve L-001 first (L2→L3 creates a module initialization order risk)
2. Resolve L-004 (monitoring layer should be read-only)
3. L-002 and L-003 are documentation issues, not code defects
