# Dependency Analysis
## AR-001 Part 2: Dependency Graph, Coupling, Cycles, and Orphans

**Date:** 2026-08-04

---

## 1. Dependency Graph (Simplified — Direction = imports)

```
main.py
  └── orchestrator/master_orchestrator.py     [GOD OBJECT — 15+ imports]
        ├── global_intelligence
        ├── market_intelligence
        ├── market_learning
        ├── meta_learning
        ├── opportunity_engine
        ├── strategy_lab
        ├── capital_risk_engine
        ├── risk_control
        ├── market_simulation
        ├── risk_guardian
        ├── debate_system
        ├── decision_ai
        ├── execution_engine
        ├── trade_monitoring
        ├── learning_system
        ├── performance
        ├── validation_engine
        ├── communication
        ├── system_monitor
        ├── notifications
        └── data_feeds

data_feeds                      [INFRASTRUCTURE — imported by many]
  ├── global_intelligence.*
  ├── market_intelligence.*
  ├── opportunity_engine.*
  ├── risk_control.options_risk_engine
  └── trade_monitoring.*

communication                   [INFRASTRUCTURE — imported by many]
  ├── orchestrator
  ├── learning_system
  ├── execution_engine
  └── opportunity_engine

models                          [INFRASTRUCTURE — imported by most]
  └── (all layers)
```

---

## 2. Duplicate Module Analysis

### 2.1 CorrelationEngine — THREE copies (DEFECT)

| Location | File | Observations |
|---|---|---|
| Copy 1 | `global_intelligence/correlation_engine.py` | Multi-asset correlation for global macro |
| Copy 2 | `capital_risk_engine/correlation_engine.py` | Portfolio correlation for sizing |
| Copy 3 | `risk_control/correlation_engine.py` | Risk-level correlation check |

**Assessment:** All three implement cross-asset Pearson/Spearman correlation.
No single owner. When correlation logic changes, three files need updating.
This creates a latent divergence bug.

**Recommendation:** See R-003 — merge into a single `analytics/correlation_engine.py`.

---

### 2.2 Regime Computation — THREE independent implementations

| Location | Function |
|---|---|
| `market_intelligence/market_regime_ai.py` | Classifies NIFTY into BULL/BEAR/RANGE/VOLATILE |
| `market_learning/market_observer.py` | Captures regime observation for MLS |
| `meta_learning/feature_extractor.py` | Extracts 6-dim feature vector including regime |

**Assessment:** These do NOT compute the same regime. They are appropriately
layered: Layer 2 computes the canonical label; MLS and meta-learning consume it.
The concern is that `meta_learning/feature_extractor.py` may re-derive regime
independently rather than consuming `MarketRegimeAI` output.

**Recommendation:** Verify that `FeatureExtractor` reads regime from
`MarketRegimeAI` output rather than re-computing from raw quotes.

---

### 2.3 Walk-Forward Testing — TWO implementations

| Location | Class |
|---|---|
| `strategy_lab/backtesting_ai.py` | Includes WFT as part of backtest |
| `validation_engine/walkforward_test.py` | `WalkForwardAnalyzer` |
| `performance/walk_forward_tester.py` | `WFFold` |

**Assessment:** The strategy_lab WFT is used during strategy evolution.
The validation_engine WFT is used during the 6-stage validation gate.
The performance WFF is used for performance attribution.
These serve different purposes. However they may produce inconsistent
split logic (70/30 vs rolling window).

**Recommendation:** Unify the WFT split calculation into a shared utility
function to avoid inconsistent out-of-sample periods.

---

### 2.4 Confidence Scoring — THREE independent implementations

| Location | What is scored |
|---|---|
| `debate_system/multi_agent_debate.py` | Agent conviction score 0–10 |
| `opportunity_engine/equity_scanner_ai.py` | Breakout confidence |
| `pmci_engine.py` | PMCIResult.confidence [0,1] |

**Assessment:** These are legitimately different confidence domains.
Not a defect — but the scale inconsistency (0–10 vs 0–1) creates
integration confusion. PMCI confidence should be normalised to the
debate scale before passing through DecisionEngine.

---

## 3. Coupling Analysis

### 3.1 `master_orchestrator.py` — Critical Coupling

`master_orchestrator.py` is 5,900+ lines and imports from 15+ packages.
This means:

- Any change to any layer's public API risks breaking the orchestrator.
- The orchestrator cannot be tested in isolation.
- Scheduler logic and coordination logic are entangled.

**Risk level:** HIGH. If the orchestrator fails at 09:45 trade window,
the entire trading cycle fails.

**Recommendation:** See R-002 — decompose into 3 coordinators:
`MarketCoordinator`, `TradingCoordinator`, `LearningCoordinator`.

---

### 3.2 `data_feeds` — Well-Managed Coupling

`DataFeedManager` provides a clean abstraction. All feed consumers import
from `data_feeds.data_feed_manager`, not from individual feeds directly.
Dhan → Yahoo fallback is transparent. This is the correct pattern.

**Assessment:** GOOD architecture. No changes needed.

---

### 3.3 `market_learning` — Correctly Isolated

The MLS package has no imports from trading layers (opportunity_engine,
strategy_lab, execution_engine). It only imports from:
- `models` (canonical data types)
- `numpy`, `scipy` (math)

This isolation is intentional and correct. **MLS should not import from
trading layers.** Integration happens at the orchestrator level by passing
MLS outputs as inputs to trading-layer functions.

---

## 4. Orphan Modules (Generated but not consumed)

| Module / Output | Produced By | Consumed By | Risk |
|---|---|---|---|
| `CDSEngine.evaluate()` output | `cds_engine.py` | Nothing in trading path | No CDS context reaches DecisionEngine |
| `PMCIEngine.compute()` output | `pmci_engine.py` | Nothing in trading path | PMCI score unused by OpportunityEngine |
| `CAPMCIEngine.compute()` output | `ca_pmci_engine.py` | Nothing in trading path | CA-PMCI unused |
| `EdgeDiscoveryEngine.discover()` | `edge_discovery_engine.py` | Nothing | Discovered edges not fed to StrategyLab |
| `AutonomousResearch` results | `autonomous_research/` | Nothing | AR results not consumed |
| `KnowledgeProvider` output | `knowledge_provider.py` | Nothing | No consumer |

**Assessment:** This is the most critical finding. The entire MLS system
(phases 1–5B, ~3,000 lines) produces no output that feeds the trading decision.

---

## 5. Suspected Circular Imports

| Pair | Status | Evidence |
|---|---|---|
| `orchestrator` ↔ `communication` | LOW RISK — orchestrator imports EventBus, not reverse | N/A |
| `learning_system` ↔ `strategy_lab` | MEDIUM RISK — `meta_strategy_controller` references `learning_engine` and vice-versa | Needs verification |
| `execution_engine` ↔ `risk_control` | LOW RISK — one-way dependency only | N/A |
| `market_intelligence` ↔ `meta_learning` | MEDIUM RISK — `regime_probability_model.py` imports from `meta_learning` | Needs verification |

**Note:** No runtime circular import error has been reported, suggesting Python's
import system handles them. However, circular imports prevent proper testing in isolation.

---

## 6. Unused Import Audit

Based on structural analysis, the following modules appear to be imported
but potentially unused in production paths:

| Module | Potential Issue |
|---|---|
| `brokers/angelone_broker.py` | AngelOne not listed as ACTIVE_BROKER |
| `autonomous_research/` | Not called from orchestrator or scheduler |
| `edge_discovery/` | Not called from orchestrator or scheduler |
| `iios/` skeleton | No production calls observed |
| `analysis/` (57 files) | Tooling only — not called from production path |

**Recommendation:** Add `ACTIVE_MODULES` feature flag to `config.py` to
selectively enable/disable research and tooling packages at startup.
