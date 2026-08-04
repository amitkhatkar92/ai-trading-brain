# Knowledge Flow Review
## AR-001 Part 3: Complete Knowledge Path Verification

**Date:** 2026-08-04

---

## 1. Canonical Knowledge Flow

The intended signal path from raw market data to order execution:

```
[Raw Market Data]
      ↓
  [DATA LAYER]
  DataFeedManager → DhanFeed / YahooFeed / NSEFeed
      ↓
  [GLOBAL INTELLIGENCE]
  GlobalDataAI → GlobalSnapshot (S&P, Nikkei, bonds, FX)
  GlobalSentimentAI → SentimentScore
  MacroSignalAI → MacroSignals
      ↓
  [MARKET INTELLIGENCE]
  MarketRegimeAI → RegimeLabel (BULL/BEAR/RANGE/VOLATILE)
  SectorRotationAI → SectorRanking
  LiquidityAI → LiquidityScore
  EventDetectionAI → EventTriggers
      ↓
  [OPPORTUNITY ENGINE]
  EquityScannerAI → Candidates
  CandidateStore → RankedCandidates
      ↓
  [META-LEARNING]
  RegimeStrategyMap → Strategy weights by regime
  StrategyWeightPredictor → StrategyAllocation
      ↓
  [STRATEGY LAB]
  MetaStrategyController → Active strategy list
      ↓
  [CAPITAL RISK ENGINE]
  CapitalRiskEngine → Position size
  LiquidityGuard → Capacity check
      ↓
  [RISK CONTROL]
  RiskManagerAI → Pre-execution approval
      ↓
  [MARKET SIMULATION]
  SimulationEngine → Monte Carlo result
      ↓
  [RISK GUARDIAN]
  FailSafeRiskGuardian → GO / HALT
      ↓
  [DEBATE & DECISION]
  MultiAgentDebate → Conviction score (0–10, threshold 6.5)
  DecisionEngine → ORDER / SKIP
      ↓
  [EXECUTION]
  OrderManager → Order placed (paper or live)
      ↓
  [MONITORING & LEARNING]
  TradeMonitor → Live PnL
  LearningEngine → Weight updates (EOD)
```

---

## 2. Path Completeness Verification

### 2.1 GlobalSnapshot → Market Intelligence ✅

`GlobalDataAI.fetch()` returns `GlobalSnapshot`.
`master_orchestrator.py` reads `GlobalSnapshot` and passes context to
`MarketRegimeAI` and `SectorRotationAI`. Path is verified.

---

### 2.2 RegimeLabel → MetaLearning ✅

`MarketRegimeAI.classify()` returns `RegimeLabel`.
`MetaLearningEngine` receives regime via `FeatureExtractor`.
`RegimeStrategyMap` maps regime→strategy weights. Path is verified.

---

### 2.3 OpportunityEngine → CapitalRiskEngine ✅

Candidates from `EquityScannerAI` pass through `CandidateStore`.
`CapitalRiskEngine` receives candidate + regime context and computes size.
Path is verified.

---

### 2.4 RiskGuardian → DecisionEngine ✅

`FailSafeRiskGuardian` returns `GuardianDecision(GO)` or `GuardianDecision(HALT)`.
When HALT, trading cycle aborts before `DecisionEngine` is reached.
Path is verified.

---

### 2.5 DecisionEngine → OrderManager ✅

`DecisionEngine.decide()` returns `ORDER` or `SKIP`.
`OrderManager.place_order()` is called only on `ORDER`.
Paper trading journal writes to CSV. Path is verified.

---

### 2.6 OrderManager → LearningEngine ✅ (EOD)

`LearningEngine` reads `paper_trades.csv` and `strategy_performance.json` at EOD.
`StrategyPerformanceTracker` updates win rates.
`RegimeStrategyMap` updates regime weights. Path is verified.

---

## 3. Missing or Incomplete Paths (CRITICAL GAPS)

### GAP-001: MLS output → Trading path ❌

**What exists:**
- `PMCIEngine.compute()` → `PMCIResult(pmci_score, confidence, context_factors)`
- `CDSEngine.evaluate_library()` → `CDSLibraryResult(scores)` per DNA
- `CAPMCIEngine.compute()` → `CAPMCIResult(ca_pmci)`

**What is missing:**
- No call to `PMCIEngine` in `master_orchestrator.py`
- No call to `CDSEngine` in `master_orchestrator.py`
- `EquityScannerAI` does not receive PMCI score as input
- `CapitalRiskEngine` does not receive CDS scores
- `DecisionEngine` does not receive PMCI/CDS context

**Impact:** The entire MLS system is analytically inert. All DNA
discovered, all context computed, all CDS scores generated — produce
zero influence on any trade decision.

**Recommended bridge:**
```
MarketObserver → (background) → DNADiscoveryEngine → DNAConsensusEngine
                                                            ↓
                                                      CDSEngine.evaluate_library()
                                                            ↓
OpportunityEngine.score_candidate(candidate, cds_scores) → adjusted_score
                                                            ↓
DecisionEngine receives adjusted_score + CDS top_dna
```

---

### GAP-002: EdgeDiscovery → StrategyLab ❌

**What exists:**
- `EdgeDiscoveryEngine.discover()` → `DiscoveredEdge` objects
- `CandidateStrategyGenerator.generate_from_edge()` → strategy config

**What is missing:**
- No call to `EdgeDiscoveryEngine` from `master_orchestrator.py`
- `StrategyEvolutionAI` does not receive discovered edges as seed strategies

**Impact:** The edge discovery engine runs independently (if at all) and
never contributes to strategy evolution.

---

### GAP-003: AutonomousResearch → LearningSystem ❌

**What exists:**
- `HypothesisRegistry` — tracks market hypotheses
- `EvidenceValidator` — validates evidence
- `GapDetector` — identifies knowledge gaps
- `KnowledgeProvider` — synthesises knowledge

**What is missing:**
- No call to any ARS module from `master_orchestrator.py`
- No connection between `KnowledgeProvider` and `LearningEngine`
- ARS operates as a completely isolated subsystem

**Impact:** Autonomous research produces no influence on trading.

---

### GAP-004: StrategyPerformanceTracker → MetaLearning ⚠️ PARTIAL

**What exists:**
- `StrategyPerformanceTracker` writes win rates, Sharpe, DD
- `RegimeStrategyMap` is updated at EOD

**What is missing:**
- No direct feed from `StrategyPerformanceTracker` to
  `StrategyWeightPredictor`'s training data
- `PerformanceDataset` (meta-learning) may not ingest live EOD results

**Assessment:** Partially wired. Meta-learning weight predictor may
be trained on historical data only, not on live paper trading results.

---

## 4. Knowledge Path Quality Summary

| Path | Status | Gap Ref |
|---|---|---|
| Data → GlobalIntelligence | ✅ Complete | — |
| GlobalIntelligence → MarketIntelligence | ✅ Complete | — |
| MarketIntelligence → MetaLearning | ✅ Complete | — |
| MarketIntelligence → OpportunityEngine | ✅ Complete | — |
| OpportunityEngine → CapitalRiskEngine | ✅ Complete | — |
| CapitalRiskEngine → RiskManagerAI | ✅ Complete | — |
| RiskGuardian → DecisionEngine | ✅ Complete | — |
| DecisionEngine → OrderManager | ✅ Complete | — |
| OrderManager → LearningEngine (EOD) | ✅ Complete | — |
| MLS → Trading (PMCI, CDS) | ❌ Missing | GAP-001 |
| EdgeDiscovery → StrategyLab | ❌ Missing | GAP-002 |
| ARS → LearningSystem | ❌ Missing | GAP-003 |
| StrategyPerformanceTracker → MetaLearning | ⚠️ Partial | GAP-004 |
