# Market Learning System — Architecture

**Phase 0 — Architecture Freeze**  
**Date:** 2026-08-03  
**Status:** FROZEN — No production code shall be written in Phase 0

---

## 1. Purpose

The Market Learning System (MLS) continuously learns from the entire market
rather than only from IIOS trades.

**Primary Research Question:**
> *Can IIOS identify the hidden characteristics that consistently separate
> future outperformers from ordinary stocks BEFORE the movement begins?*

MLS observes every NSE-listed stock every trading day, classifies outcomes,
extracts pre-move features, compares populations statistically, and feeds
verified discoveries into ARS as traceable, reproducible knowledge.

---

## 2. Position in IIOS

```
                    ┌─────────────────────────────────────────┐
                    │              IIOS Core                  │
                    │  (execution engine, strategies, orders) │
                    └─────────────────────────────────────────┘
                                        ↑
                              verified knowledge
                                        ↑
                    ┌─────────────────────────────────────────┐
                    │        ARS (Autonomous Research System) │
                    │  KP · Registry · Synthesizer · Gap      │
                    │  Roadmap · Validator · StudyPlanner     │
                    └─────────────────────────────────────────┘
                                        ↑
                              validated DNA findings
                                        ↑
                    ┌─────────────────────────────────────────┐
                    │  MLS (Market Learning System)  ← NEW   │
                    │  Observer · Classifier · Extractor     │
                    │  Comparator · DNAExtractor · Integrator │
                    └─────────────────────────────────────────┘
                                        ↑
                              daily market data
                                        ↑
                    ┌─────────────────────────────────────────┐
                    │       NSE Universe (∼2000 symbols)      │
                    └─────────────────────────────────────────┘
```

MLS is a **read-only learner**.  
MLS never executes trades, never modifies strategies, never changes
thresholds, and never writes directly to knowledge stores.  
It only proposes validated evidence to ARS via the KnowledgeIntegrator.

---

## 3. Architecture Overview

MLS consists of **6 new modules** layered over **12 reused IIOS modules**.

### 3.1 New MLS Modules

| Module | File | Responsibility |
|--------|------|---------------|
| `MarketObserver` | `market_learning/market_observer.py` | Fetch full NSE universe daily; produce DailyMarketSnapshot |
| `StockClassifier` | `market_learning/stock_classifier.py` | Classify stocks into 9 groups; produce ClassifiedUniverse |
| `PopulationComparator` | `market_learning/population_comparator.py` | Statistical comparison of group feature distributions |
| `DNAExtractor` | `market_learning/dna_extractor.py` | Extract winner/loser/neutral DNA from comparison results |
| `KnowledgeIntegrator` | `market_learning/knowledge_integrator.py` | Propose verified DNA as Findings and Hypotheses to ARS |
| `MLSConfig` | `market_learning/mls_config.py` | All thresholds; no hardcoded values in any module |

### 3.2 Reused IIOS Modules (no modification)

| Module | Package | MLS Usage |
|--------|---------|-----------|
| `FeatureExtractor` | `edge_discovery` | Extract ≈70 pre-move features per symbol |
| `DataFeedManager` | `data_feeds` | Fetch OHLCV, FII/DII, PCR, VIX from live feeds |
| `MarketIntelligenceEngine` | `iios.investment.market` | Regime classification |
| `RegimeDetector` | `iios.investment.market.regime` | 14-type regime detection with confidence |
| `BreadthAnalyzer` | `iios.investment.market.analytics` | Advance/decline, new highs/lows |
| `KnowledgeProvider` | `autonomous_research` | Read findings, edges, studies |
| `HypothesisRegistry` | `autonomous_research` | Submit DNA patterns as hypotheses |
| `CrossStudySynthesizer` | `autonomous_research` | Synthesize DNA across daily studies |
| `GapDetector` | `autonomous_research` | Identify gaps in DNA coverage |
| `RoadmapManager` | `autonomous_research` | Prioritize gap-filling studies |
| `EvidenceValidator` | `autonomous_research` | Validate DNA statistical quality |
| `StudyPlanner` | `autonomous_research` | Design follow-on studies for DNA patterns |

**Reuse ratio: 12 reused / 18 total = 67% by module count.**  
**Reuse ratio by lines of code: estimated > 90% (new modules are thin orchestration layers).**

---

## 4. Twelve-Stage Pipeline

```
Stage 1  Market Close (16:00 IST)
          ↓
Stage 2  MarketObserver
          Fetch full NSE universe (~2000 symbols)
          Collect OHLCV, FII/DII flow, India VIX, PCR, sector flows
          ↓
Stage 3  StockClassifier
          Compute 1-day forward return for every symbol
          Classify into 9 groups (Top5%, Top10%, Bottom5%, etc.)
          ↓
Stage 4  FeatureExtractor (REUSED)
          Extract T-1 feature vector per symbol
          Timestamp MUST precede classified outcome
          ↓
Stage 5  PopulationComparator
          For each feature: compute Winner vs Neutral statistics
                            compute Loser vs Neutral statistics
          Apply configurable statistical tests
          ↓
Stage 6  DNAExtractor
          Extract statistically significant feature differences
          Produce: DailyWinnerDNA, DailyLoserDNA, DailyNeutralDNA
          Produce: DailyDifferenceReport
          ↓
Stage 7  Temporal Aggregation
          Weekly consensus (5-day rolling)
          Monthly consensus (20-day rolling)
          Quarterly consensus (60-day rolling)
          ↓
Stage 8  EvidenceValidator (REUSED)
          Validate each DNA characteristic against 7 statistical gates
          Reject characteristics that fail any critical gate
          ↓
Stage 9  KnowledgeIntegrator
          Convert validated DNA to Finding objects (WINNER_DNA / LOSER_DNA)
          Submit to KnowledgeProvider staging area
          Create ScientificHypotheses in HypothesisRegistry
          ↓
Stage 10 ARS Update
          CrossStudySynthesizer synthesizes new DNA findings
          GapDetector identifies new knowledge gaps
          RoadmapManager re-prioritizes research roadmap
          ↓
Stage 11 Storage
          Persist daily DNA to mls/winner_dna_daily.json
          Persist daily DNA to mls/loser_dna_daily.json
          Update mls/dna_consensus.json
          Append to mls/market_learning_history.json
          ↓
Stage 12 StudyPlanner (REUSED)
          For every new validated DNA characteristic:
            Create StudyPlan (EDGE_VALIDATION or DNA_DISCOVERY type)
            Assign to RoadmapManager queue
```

---

## 5. System Boundaries

### 5.1 What MLS owns
- Daily universe fetch and classification
- Pre-move feature extraction (via FeatureExtractor)
- Population statistical comparison
- DNA extraction and temporal aggregation
- Validation gate enforcement
- Knowledge integration proposal

### 5.2 What MLS does NOT own
- Trading decisions (owned by IIOS execution engine)
- Strategy parameters (owned by StrategyLab)
- Knowledge store content (owned by KnowledgeProvider)
- Hypothesis lifecycle (owned by HypothesisRegistry)
- Research prioritization (owned by RoadmapManager)
- Quality gates for existing knowledge (owned by EvidenceValidator)

### 5.3 Governance Contract
```
MLS never:
  • executes trades
  • changes strategies or thresholds
  • writes directly to knowledge stores
  • promotes its own findings without ARS validation
  • assumes its DNA is correct before validation

MLS always:
  • timestamps features BEFORE outcomes
  • traces every characteristic to source evidence
  • enforces statistical gates before proposing any finding
  • routes all discoveries through ARS, never directly to execution
  • preserves the full audit trail from raw data to finding
```

---

## 6. Module Interfaces (frozen — no production code)

### MarketObserver
```
Input:  trading_date: date
Output: DailyMarketSnapshot
        - universe: List[StockRecord]  (symbol, ohlcv, fii, dii, delivery_pct)
        - market_level: MarketLevelData  (VIX, PCR, breadth, global_sentiment)
        - regime: RegimeClassification  (via RegimeDetector)
        - sectors: Dict[sector, SectorData]
        - timestamp: datetime  (feature capture time)
```

### StockClassifier
```
Input:  DailyMarketSnapshot
Output: ClassifiedUniverse
        - groups: Dict[GroupLabel, List[StockRecord]]
        - thresholds: Dict[GroupLabel, float]  (configurable from MLSConfig)
        - date: date
```

### PopulationComparator
```
Input:  ClassifiedUniverse, feature_vectors: Dict[symbol, FeatureVector]
Output: ComparisonResult
        - winner_vs_neutral: Dict[feature_name, FeatureStatistics]
        - loser_vs_neutral:  Dict[feature_name, FeatureStatistics]
        - sample_sizes: Dict[GroupLabel, int]
        - date: date
```

### DNAExtractor
```
Input:  ComparisonResult, config: MLSConfig
Output: DailyDNAResult
        - winner_dna: List[DNACharacteristic]
        - loser_dna:  List[DNACharacteristic]
        - neutral_dna: List[DNACharacteristic]
        - difference_report: DifferenceReport
        - date: date
```

### KnowledgeIntegrator
```
Input:  ValidatedDNA (from EvidenceValidator)
Output: IntegrationResult
        - findings_proposed: List[Finding]
        - hypotheses_created: int
        - gaps_flagged: List[str]
        - studies_scheduled: List[StudyPlan]
```

---

## 7. Technology Constraints

- **Language:** Python 3.14 (matches IIOS)
- **Statistics:** `scipy.stats` for tests (t-test, Mann-Whitney U, effect size)
- **Storage:** JSON with atomic writes (`.tmp` → `os.replace`) matching ARS pattern
- **Concurrency:** `threading.Lock()` — matches existing ARS pattern
- **Scheduling:** Triggered by IIOS scheduler at 16:05 IST each trading day
- **Data feeds:** Dhan API (primary) / yfinance (fallback) — matches existing data_feeds layer

---

## 8. Final Questions (Preliminary Answers)

These are addressed definitively in `MLS_PHASE0_FREEZE.md`.

1. **Can MLS discover characteristics BEFORE movement?**  
   Yes — the temporal contract (Stage 4) enforces feature timestamp < outcome timestamp at the architecture level.

2. **Can every discovered characteristic be traced to evidence?**  
   Yes — every DNACharacteristic carries source date, group sizes, statistical test results, and regime/sector context.

3. **Can MLS reuse existing IIOS modules with > 90% reuse?**  
   Yes — 12 of 18 total modules are reused. By LOC, new modules are thin orchestration layers estimated at < 10% of total execution path code.

4. **Can ARS consume MLS knowledge without architectural changes?**  
   Yes — MLS produces `Finding` objects with `FindingClassification.WINNER_DNA` or `LOSER_DNA`, the exact classifications already defined in `autonomous_research/models.py`. Zero ARS schema changes required.
