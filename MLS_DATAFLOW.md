# Market Learning System — Data Flow

**Phase 0 — Architecture Freeze**  
**Date:** 2026-08-03  
**Status:** FROZEN

---

## 1. Pipeline Timing

All times IST. All feature captures at T-1 relative to the classified outcome.

```
15:30  Pre-close: FII/DII flow data available
15:30  Pre-close: PCR final snapshot
15:30  Pre-close: India VIX final snapshot
16:00  NSE Market Close
16:05  IIOS Scheduler triggers MarketObserver
16:05  Stage 1: Market data fetch begins
16:10  Stage 2: Classification (T+5 min from close)
16:12  Stage 3: Feature extraction (T-1 features already available from morning)
16:15  Stage 4-5: Statistical comparison
16:20  Stage 6: DNA extraction
16:25  Stage 7: Temporal aggregation
16:30  Stage 8: EvidenceValidator gates
16:35  Stage 9: KnowledgeIntegrator — ARS update
16:40  Stage 10: Storage persistence
16:45  Stage 11: StudyPlanner scheduling
16:50  Daily MLS run complete

CRITICAL CONSTRAINT:
  All features in the FeatureVector MUST carry timestamp ≤ 09:15
  (pre-market open) for the same trading day.
  Features computed from intraday data MUST use only data
  available at or before T-1 market open.
  OUTCOME (forward return) is computed from Close(T) vs Close(T-1).
```

---

## 2. Data Schemas

### 2.1 StockRecord

```json
{
  "symbol": "RELIANCE",
  "isin": "INE002A01018",
  "sector": "ENERGY",
  "open": 2850.00,
  "high": 2910.00,
  "low": 2840.00,
  "close": 2905.00,
  "prev_close": 2860.00,
  "volume": 4250000,
  "delivery_pct": 52.3,
  "fii_flow_proxy": 0.42,
  "dii_flow_proxy": 0.18,
  "forward_return_1d": 0.0157,
  "feature_timestamp": "2026-08-03T09:15:00",
  "outcome_timestamp": "2026-08-03T16:00:00"
}
```

**Invariant:** `feature_timestamp < outcome_timestamp` — enforced by MarketObserver.

### 2.2 GroupLabel (enum)

```
TOP_5PCT        — daily return ≥ 95th percentile of universe
TOP_10PCT       — daily return ≥ 90th percentile
TOP_20PCT       — daily return ≥ 80th percentile
BOTTOM_5PCT     — daily return ≤ 5th percentile
BOTTOM_10PCT    — daily return ≤ 10th percentile
BOTTOM_20PCT    — daily return ≤ 20th percentile
NEUTRAL         — between 20th and 80th percentile
SECTOR_WINNER   — top 20% within same sector
SECTOR_LOSER    — bottom 20% within same sector
REGIME_WINNER   — outperforms regime benchmark by ≥ threshold
REGIME_LOSER    — underperforms regime benchmark by ≥ threshold
```

Thresholds configurable via `MLSConfig`. Default percentile cuts shown above.

### 2.3 ClassifiedUniverse

```json
{
  "date": "2026-08-03",
  "regime": "BULL",
  "regime_confidence": 0.82,
  "universe_size": 1987,
  "groups": {
    "TOP_5PCT": ["ZOMATO", "PAYTM", "ADANIGREEN", "..."],
    "TOP_10PCT": ["RELIANCE", "TCS", "HDFCBANK", "..."],
    "NEUTRAL":   ["WIPRO", "SUNPHARMA", "ONGC", "..."],
    "BOTTOM_10PCT": ["YESBANK", "VODAIDEA", "..."],
    "BOTTOM_5PCT":  ["PVR", "INOXFILM", "..."]
  },
  "group_sizes": {
    "TOP_5PCT": 99, "TOP_10PCT": 198, "NEUTRAL": 1191,
    "BOTTOM_10PCT": 198, "BOTTOM_5PCT": 99
  },
  "thresholds": {
    "TOP_5PCT": 0.0312, "BOTTOM_5PCT": -0.0298
  }
}
```

### 2.4 FeatureVector (per symbol, T-1)

```json
{
  "symbol": "RELIANCE",
  "feature_timestamp": "2026-08-03T09:15:00",
  "features": {
    "regime_score":        0.80,
    "regime_bull":         1.0,
    "regime_bear":         0.0,
    "regime_volatile":     0.0,
    "vix":                 0.38,
    "vix_low":             0.0,
    "vix_high":            0.0,
    "breadth":             0.67,
    "breadth_strong":      1.0,
    "pcr":                 0.45,
    "pcr_bullish":         1.0,
    "global_bias":         0.72,
    "mom_1d":              0.008,
    "mom_5d":              0.031,
    "mom_10d":             0.058,
    "mom_20d":             0.102,
    "volume_ratio_5d":     1.42,
    "volume_ratio_10d":    1.18,
    "rsi_14":              63.4,
    "rsi_7":               71.2,
    "macd_histogram":      0.42,
    "bb_position":         0.78,
    "atr_14":              45.2,
    "vwap_deviation":      0.009,
    "sector_strength":     0.71,
    "sector_rank_pct":     0.82,
    "delivery_pct":        52.3,
    "fii_flow_proxy":      0.42,
    "dii_flow_proxy":      0.18
  }
}
```

### 2.5 FeatureStatistics (per feature, per group comparison)

```json
{
  "feature_name":         "mom_5d",
  "winner_mean":          0.042,
  "winner_std":           0.018,
  "winner_median":        0.039,
  "neutral_mean":         0.011,
  "neutral_std":          0.021,
  "neutral_median":       0.009,
  "effect_size_d":        1.58,
  "p_value":              0.0002,
  "test_used":            "mann_whitney_u",
  "sample_size_winner":   99,
  "sample_size_neutral":  1191,
  "significant":          true,
  "direction":            "WINNER_HIGHER"
}
```

### 2.6 DNACharacteristic

```json
{
  "characteristic_id":  "DNA-W-mom5d-20260803",
  "date":               "2026-08-03",
  "group":              "WINNER",
  "feature_name":       "mom_5d",
  "direction":          "WINNER_HIGHER",
  "effect_size":        1.58,
  "p_value":            0.0002,
  "winner_mean":        0.042,
  "neutral_mean":       0.011,
  "difference_pct":     282.0,
  "regime":             "BULL",
  "confidence":         0.87,
  "validation_gates_passed": 6,
  "validation_gates_total":  7,
  "notes":              "5-day momentum separates winners from neutral in BULL regime"
}
```

### 2.7 DailyDNAResult

```json
{
  "date": "2026-08-03",
  "regime": "BULL",
  "universe_size": 1987,
  "winner_dna": [
    {"feature": "mom_5d",        "effect_size": 1.58, "direction": "WINNER_HIGHER"},
    {"feature": "breadth_strong","effect_size": 1.21, "direction": "WINNER_HIGHER"},
    {"feature": "volume_ratio_5d","effect_size": 0.94, "direction": "WINNER_HIGHER"}
  ],
  "loser_dna": [
    {"feature": "mom_5d",        "effect_size": 1.43, "direction": "LOSER_LOWER"},
    {"feature": "rsi_14",        "effect_size": 1.12, "direction": "LOSER_LOWER"},
    {"feature": "vix_high",      "effect_size": 0.88, "direction": "LOSER_HIGHER"}
  ],
  "new_characteristics": ["volume_ratio_10d"],
  "retired_characteristics": [],
  "knowledge_gain_estimate": 0.72,
  "computation_ms": 3240
}
```

### 2.8 DNAConsensus

```json
{
  "period": "WEEKLY",
  "window_days": 5,
  "end_date": "2026-08-03",
  "start_date": "2026-07-28",
  "trading_days": 5,
  "winner_consensus": [
    {
      "feature":          "mom_5d",
      "days_present":     5,
      "consistency_pct":  100.0,
      "avg_effect_size":  1.52,
      "avg_p_value":      0.0003,
      "direction":        "WINNER_HIGHER",
      "confidence":       0.95
    }
  ],
  "loser_consensus": [
    {
      "feature":          "mom_5d",
      "days_present":     4,
      "consistency_pct":  80.0,
      "avg_effect_size":  1.38,
      "confidence":       0.88
    }
  ]
}
```

---

## 3. Storage Layout

```
data/
  mls/
    winner_dna_daily.json        — array of DailyWinnerDNA, one entry per trading day
    loser_dna_daily.json         — array of DailyLoserDNA, one entry per trading day
    dna_consensus.json           — current weekly/monthly/quarterly consensus
    market_learning_history.json — full pipeline run history (date, metrics, durations)
    raw/
      {YYYY-MM-DD}/
        universe.json            — full StockRecord array for the day
        features.json            — FeatureVector per symbol
        comparison.json          — ComparisonResult
        dna_result.json          — DailyDNAResult
```

**Write pattern:**  
All writes are atomic: write to `{file}.tmp`, then `os.replace(tmp, target)`.  
A `.bak` backup is kept before each overwrite (matches ARS pattern).

**Retention:**  
- `raw/` — 90 days rolling (configurable via `MLSConfig.raw_retention_days`)
- `winner_dna_daily.json` — indefinite (append-only)
- `dna_consensus.json` — rebuilt from daily data daily

---

## 4. Data Flow Invariants

These invariants are enforced at every stage. A run that violates any invariant is aborted.

| # | Invariant | Where Enforced |
|---|-----------|----------------|
| INV-01 | `feature_timestamp < outcome_timestamp` for all StockRecords | MarketObserver |
| INV-02 | `universe_size ≥ MLSConfig.min_universe_size` (default 500) | StockClassifier |
| INV-03 | `sample_size[TOP_5PCT] ≥ MLSConfig.min_group_size` (default 20) | PopulationComparator |
| INV-04 | Every statistical test result includes p_value, effect_size, sample_sizes | DNAExtractor |
| INV-05 | No finding reaches KnowledgeIntegrator without passing all critical validation gates | EvidenceValidator |
| INV-06 | Regime classification is always present for every day's data | MarketObserver |
| INV-07 | Every DNACharacteristic has a unique, deterministic characteristic_id | DNAExtractor |

---

## 5. Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Market data fetch fails | DataFeedManager raises | Abort run, log to market_learning_history.json |
| Universe too small (< min_universe_size) | StockClassifier invariant | Abort classification, log gap |
| Group too small (< min_group_size) | PopulationComparator invariant | Skip group, log warning |
| All characteristics fail validation gates | EvidenceValidator returns empty set | Log "no new DNA today", continue |
| ARS integration fails | KnowledgeIntegrator exception | Log error, retry next day; do NOT bypass gates |
| Storage write fails | Atomic write exception | Retain `.tmp` for manual recovery |
