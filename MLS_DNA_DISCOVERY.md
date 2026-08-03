# Market Learning System — DNA Discovery

**Phase 0 — Architecture Freeze**  
**Date:** 2026-08-03  
**Status:** FROZEN

---

## 1. The Central Problem

Every trading day, a small group of stocks significantly outperforms the
market and a small group significantly underperforms.

**The question is not:** "Why did they move?"  
**The question is:** "What separated them BEFORE the movement?"

DNA Discovery is the process of finding the answer — systematically,
statistically, and repeatedly — across every trading day.

---

## 2. Group Definitions

Groups are defined by configurable percentile thresholds in `MLSConfig`.
All defaults shown below are starting points, not constants.

### 2.1 Return-Based Groups

| Group | Definition | Default Threshold |
|-------|-----------|------------------|
| `TOP_5PCT` | Daily return ≥ 95th percentile of universe | Configurable |
| `TOP_10PCT` | Daily return ≥ 90th percentile | Configurable |
| `TOP_20PCT` | Daily return ≥ 80th percentile | Configurable |
| `BOTTOM_5PCT` | Daily return ≤ 5th percentile | Configurable |
| `BOTTOM_10PCT` | Daily return ≤ 10th percentile | Configurable |
| `BOTTOM_20PCT` | Daily return ≤ 20th percentile | Configurable |
| `NEUTRAL` | Between 20th and 80th percentile | Configurable |

### 2.2 Sector-Relative Groups

| Group | Definition |
|-------|-----------|
| `SECTOR_WINNER` | Return ≥ sector's 80th percentile AND return > 0 |
| `SECTOR_LOSER` | Return ≤ sector's 20th percentile AND return < 0 |
| `SECTOR_NEUTRAL` | Within sector's 20th–80th percentile |

### 2.3 Regime-Relative Groups

| Group | Definition |
|-------|-----------|
| `REGIME_WINNER` | Outperforms Nifty by ≥ `MLSConfig.regime_outperformance_threshold` |
| `REGIME_LOSER` | Underperforms Nifty by ≥ `MLSConfig.regime_underperformance_threshold` |

---

## 3. Pre-Move Feature Taxonomy

**All features MUST have capture timestamps BEFORE the measured outcome.**  
Features are computed at T-1 market open (09:15 IST) at the latest.  
The measured outcome is computed from Close(T) vs Close(T-1).

Features are provided by the existing `FeatureExtractor` (reused from `edge_discovery`).
The following taxonomy documents every feature category and naming convention.

### Category 1: Price Momentum (multi-timeframe)

| Feature Name | Definition | Direction |
|---|---|---|
| `mom_1d` | 1-day return | Continuous |
| `mom_5d` | 5-day return | Continuous |
| `mom_10d` | 10-day return | Continuous |
| `mom_20d` | 20-day return | Continuous |
| `mom_60d` | 60-day return (from market data) | Continuous |

**DNA Hypothesis:** Winners show positive multi-timeframe momentum alignment BEFORE the day.

### Category 2: Volatility

| Feature Name | Definition |
|---|---|
| `atr_5d` | Average True Range, 5-period |
| `atr_14` | Average True Range, 14-period (standard) |
| `atr_21` | Average True Range, 21-period |
| `bb_position` | Position within Bollinger Bands (0=lower, 1=upper) |
| `bb_width` | Bollinger Band width (volatility proxy) |
| `vol_score` | Market-wide volatility level (LOW=0.2, MED=0.5, HIGH=0.8, EXTREME=1.0) |

### Category 3: Volume

| Feature Name | Definition |
|---|---|
| `volume_ratio_5d` | Today's volume / 5-day average volume |
| `volume_ratio_10d` | Today's volume / 10-day average volume |
| `volume_ratio_20d` | Today's volume / 20-day average volume |
| `delivery_pct` | Delivery percentage (institutional proxy) |

**DNA Hypothesis:** Winner volume ratios are elevated at T-1 (institutional accumulation signal).

### Category 4: Technical Oscillators

| Feature Name | Definition |
|---|---|
| `rsi_7` | RSI with 7-period lookback |
| `rsi_14` | RSI with 14-period lookback (standard) |
| `rsi_21` | RSI with 21-period lookback |
| `macd_histogram` | MACD histogram value (signal line position) |
| `vwap_deviation` | Deviation of price from VWAP |

### Category 5: Market Structure

| Feature Name | Definition |
|---|---|
| `regime_score` | Continuous regime strength (0=bear, 1=bull) |
| `regime_bull` | 1 if BULL_TREND regime, else 0 |
| `regime_bear` | 1 if BEAR_MARKET regime, else 0 |
| `regime_volatile` | 1 if VOLATILE regime, else 0 |
| `regime_range` | 1 if RANGE_MARKET regime, else 0 |
| `breadth` | Market breadth (advance/decline ratio, 0–1) |
| `breadth_strong` | 1 if breadth > 0.60 |
| `breadth_weak` | 1 if breadth < 0.40 |

### Category 6: Options / Derivatives

| Feature Name | Definition |
|---|---|
| `vix` | India VIX, normalized to 0–1 range |
| `vix_low` | 1 if VIX < 14 (low fear) |
| `vix_high` | 1 if VIX > 22 (high fear) |
| `pcr` | Put/Call Ratio, normalized |
| `pcr_bullish` | 1 if PCR < 0.7 (bullish positioning) |
| `pcr_bearish` | 1 if PCR > 1.3 (bearish positioning) |
| `pcr_neutral` | 1 if PCR between 0.7 and 1.3 |

### Category 7: Sector

| Feature Name | Definition |
|---|---|
| `sector_strength` | Sector momentum vs benchmark (0–1) |
| `sector_rank_pct` | Stock's percentile within sector |
| `sector_flow_count` | Number of sectors with positive flows (normalized) |

### Category 8: Institutional Flow Proxy

| Feature Name | Definition |
|---|---|
| `fii_flow_proxy` | FII directional flow indicator (0=selling, 1=buying) |
| `dii_flow_proxy` | DII directional flow indicator (0=selling, 1=buying) |
| `event_count` | Number of significant market events today (normalized) |

### Category 9: Cross-Market

| Feature Name | Definition |
|---|---|
| `global_bias` | Global sentiment from S&P futures, Nikkei, DJIA (0–1) |

---

## 4. DNA Discovery Algorithm

### 4.1 Daily Algorithm (per trading day T)

```
INPUTS:
  classified_universe: ClassifiedUniverse
  feature_vectors:     Dict[symbol, FeatureVector]  (all captured at T-1)
  config:              MLSConfig

STEP 1 — Build Population Arrays
  for each GroupLabel G in [TOP_5PCT, TOP_10PCT, NEUTRAL, BOTTOM_5PCT, BOTTOM_10PCT]:
    build feature matrix M_G: shape (n_G × n_features)

STEP 2 — Statistical Comparison (for each feature F):
  winner_group = classified_universe.groups[TOP_5PCT]   (primary winner group)
  neutral_group = classified_universe.groups[NEUTRAL]
  loser_group = classified_universe.groups[BOTTOM_5PCT]

  for each feature F:
    # Winner vs Neutral
    stat_W, p_W = mann_whitney_u(
      [features[F] for symbol in winner_group],
      [features[F] for symbol in neutral_group]
    )
    d_W = cohens_d(winner_features_F, neutral_features_F)

    # Loser vs Neutral
    stat_L, p_L = mann_whitney_u(
      [features[F] for symbol in loser_group],
      [features[F] for symbol in neutral_group]
    )
    d_L = cohens_d(loser_features_F, neutral_features_F)

STEP 3 — Filter Significant Characteristics
  winner_dna = []
  for each feature F:
    if abs(d_W) >= MLSConfig.min_effect_size AND p_W <= MLSConfig.max_p_value:
      direction = "WINNER_HIGHER" if mean(winner_F) > mean(neutral_F) else "WINNER_LOWER"
      winner_dna.append(DNACharacteristic(feature=F, direction=direction,
                                          effect_size=d_W, p_value=p_W))
  # same for loser_dna

STEP 4 — Produce DailyDNAResult
  return DailyDNAResult(
    date=T,
    winner_dna=winner_dna,
    loser_dna=loser_dna,
    regime=classified_universe.regime,
    difference_report=compute_difference_report(winner_dna, loser_dna)
  )
```

### 4.2 Statistical Test Selection

| Scenario | Test | Reason |
|---|---|---|
| Default comparison | Mann-Whitney U | Non-parametric; does not assume normality |
| Effect size | Cohen's d | Standardized; comparable across features |
| Proportion features | Fisher's exact test | Binary features (regime_bull, vix_low) |
| Multiple comparisons | Benjamini-Hochberg FDR | Controls false discovery rate |

All tests and corrections are configurable via `MLSConfig`. No test is hardcoded.

---

## 5. Temporal Aggregation

### 5.1 Aggregation Levels

| Level | Window | Update Frequency | Purpose |
|-------|--------|-----------------|---------|
| DAILY | 1 day | Every day | Immediate detection |
| WEEKLY | 5 trading days | Every day (rolling) | Noise reduction |
| MONTHLY | 20 trading days | Every day (rolling) | Stable patterns |
| QUARTERLY | 60 trading days | Every day (rolling) | Long-horizon DNA |

### 5.2 Consensus Algorithm

```
for each aggregation level WINDOW:
  characteristics = all characteristics seen in last WINDOW trading days

  for each unique feature F in characteristics:
    days_present    = count of days F appeared as winner_dna (or loser_dna)
    consistency_pct = days_present / WINDOW * 100
    avg_effect_size = mean(effect_size) across days F was present
    avg_p_value     = geometric_mean(p_values) across days F was present

    if consistency_pct >= MLSConfig.min_consistency_pct[WINDOW]:
      add to consensus_dna with confidence = f(consistency_pct, avg_effect_size)
```

### 5.3 Confidence Formula

```
confidence = (
    consistency_weight  * (consistency_pct / 100)
  + effect_size_weight  * min(avg_effect_size / 2.0, 1.0)
  + significance_weight * (1 - avg_p_value)
)
where:
  consistency_weight  = MLSConfig.confidence_consistency_weight  (default 0.50)
  effect_size_weight  = MLSConfig.confidence_effect_size_weight  (default 0.30)
  significance_weight = MLSConfig.confidence_significance_weight (default 0.20)
```

---

## 6. Daily Difference Report

Every day MLS produces a `DifferenceReport` answering these questions:

### 6.1 Core Questions

| Question | What MLS Computes |
|----------|-----------------|
| Why did today's winners outperform? | Top-5 features with highest winner_vs_neutral effect size |
| Why did today's losers underperform? | Top-5 features with highest loser_vs_neutral effect size |
| Which characteristics appeared before both? | Features present in BOTH winner_dna AND loser_dna |
| Which characteristics disappeared? | Features in yesterday's DNA but absent today |
| Which sectors behaved differently? | Per-sector winner/loser DNA comparison |
| Which regime changed behaviour? | If regime differs from yesterday, regime_shift=True |

### 6.2 Report Schema

```json
{
  "date": "2026-08-03",
  "regime": "BULL",
  "regime_change": false,
  "winner_drivers": [
    {"feature": "mom_5d", "effect_size": 1.58, "direction": "WINNER_HIGHER"},
    {"feature": "breadth_strong", "effect_size": 1.21, "direction": "WINNER_HIGHER"}
  ],
  "loser_drivers": [
    {"feature": "mom_5d", "effect_size": 1.43, "direction": "LOSER_LOWER"},
    {"feature": "rsi_14", "effect_size": 1.12, "direction": "LOSER_LOWER"}
  ],
  "shared_characteristics": ["mom_5d"],
  "new_characteristics": ["volume_ratio_10d"],
  "retired_characteristics": [],
  "sector_divergence": {
    "BANKING": {"winner_driver": "fii_flow_proxy", "loser_driver": "vix_high"},
    "IT":      {"winner_driver": "global_bias",    "loser_driver": "pcr_bearish"}
  },
  "knowledge_gain_estimate": 0.72
}
```

---

## 7. DNA Lifecycle

```
CANDIDATE     ← first seen today (may be noise)
EMERGING      ← present in WEEKLY consensus
ESTABLISHED   ← present in MONTHLY consensus with confidence ≥ 0.80
VALIDATED     ← passed EvidenceValidator all gates → submitted to ARS
ACTIVE        ← accepted by HypothesisRegistry
DECLINING     ← consistency dropping (MONTHLY dropping below WEEKLY threshold)
RETIRED       ← absent from MONTHLY consensus for > 20 consecutive trading days
```

Lifecycle transitions are tracked in `market_learning_history.json`.

---

## 8. Regime-Specific DNA

DNA is always tagged with the regime at time of discovery. This enables:

- **Regime-conditional patterns:** "mom_5d separation only appears in BULL regime"
- **Regime-transition detection:** DNA shifts are early signals of regime change
- **Cross-regime validation:** A characteristic validated in ≥ 3 regimes is more reliable

The 14 regime types from `RegimeDetector` provide granular conditioning:
`BULL, BEAR, SIDEWAYS, RANGING, VOLATILE, CALM, TRENDING, EXPANSION, CONTRACTION,
ACCUMULATION, DISTRIBUTION, RECOVERY, TRANSITION, CRISIS`

---

## 9. Sector-Specific DNA

For each sector (BANKING, IT, PHARMA, AUTO, FMCG, ENERGY, METALS, REALTY, TELECOM, FMCG):

1. Build sector-only winner/loser/neutral groups from sector members
2. Run the same DNA Discovery algorithm on sector subpopulations
3. Compare sector DNA to market-wide DNA
4. Flag sectors where DNA diverges from market pattern

Sector DNA is stored separately in `winner_dna_daily.json` under `sector_dna` key.

---

## 10. New and Retired Characteristics

### New Characteristic
A feature enters `new_characteristics` if it was absent from the last
`MLSConfig.new_char_lookback_days` (default 5) daily results but is
present today with effect_size ≥ threshold.

### Retired Characteristic
A feature enters `retired_characteristics` if it was present in the
monthly consensus but has been absent for `MLSConfig.retirement_days`
(default 20) consecutive days.

Retired characteristics are preserved in `market_learning_history.json`
and submitted to GapDetector as potential TEMPORAL_GAP records.
