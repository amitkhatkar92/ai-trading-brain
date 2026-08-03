# DNADiscoveryEngine — Design Document

**MLS Phase 3 | Module:** `market_learning/dna_discovery_engine.py`  
**Authored:** 2026-08-03

---

## 1. Purpose

The `DNADiscoveryEngine` is the third component in the Market Learning System (MLS).
It answers the question: **"What features systematically separate winning stocks from
losing stocks, and how stable are those separations over time?"**

Given a `DailyMarketSnapshot` (Phase 1) and a `ClassificationResult` (Phase 2) it:

1. Extracts groups of winner / loser / neutral populations.
2. Computes 8 statistical dimensions per feature per group-pair.
3. Filters characteristics below minimum effect-size or Spearman thresholds.
4. Discovers synergistic feature *interactions* (pairs that amplify each other).
5. Assigns a lifecycle label (DISCOVERED → REPLICATED → VERIFIED → STABLE / WEAKENING).
6. Persists the full report atomically to `data/mls/dna/dna_YYYY-MM-DD.json`.

---

## 2. Architecture Position

```
Phase 1: MarketObserver      → DailyMarketSnapshot
Phase 2: PopulationClassifier → ClassificationResult
Phase 3: DNADiscoveryEngine  → DiscoveryReport          ← HERE
Phase 4: (PatternLibrary)    ← will consume DiscoveryReport
```

---

## 3. Statistical Dimensions

Each characteristic is measured on 8 dimensions. All functions are pure Python
(no scipy / statsmodels dependency):

| Dimension | Function | Purpose |
|---|---|---|
| Cohen's d | `_cohen_d(a, b)` | Pooled effect-size; ±1000 sentinel for zero pooled variance |
| Bootstrap CI | `_bootstrap_ci(a, b, n=200)` | 95 % percentile CI on Cohen's d |
| Spearman r | `_spearman(vals, labels)` | Monotonic correlation vs binary winner-label |
| Feature type | `_detect_feature_type(vals)` | BINARY / ORDINAL / CONTINUOUS |
| Pooled z-score | `_zscore_pooled(vals_a, vals_b)` | Normalisation for interaction analysis |
| Winner mean/std | per group | Stored in `FeatureEvidence` |
| Loser mean/std | per group | Stored in `FeatureEvidence` |
| Confidence score | `_compute_confidence()` | Weighted combination (effect + CI + Spearman) |

### 3.1 Confidence formula

```
confidence = w_effect  * min(1, effect_abs / (2 * min_effect))
           + w_signif  * (1 - ci_width / (2 * effect_abs + 1e-9))
           + w_consist * min(1, spearman_abs / min_spearman)
```

Weights are inherited from `MLSConfig.confidence_*_weight` (shared with Phase 2).

---

## 4. Group Definitions

| Group | Population labels (default) |
|---|---|
| Winners | `TOP_5PCT`, `TOP_10PCT` |
| Losers | `BOTTOM_5PCT`, `BOTTOM_10PCT` |
| Neutrals | all remaining labels |

Labels are controlled by `MLSConfig.dna_winner_labels` / `dna_loser_labels`.

---

## 5. Separation Directions

`SeparationDirection` (enum) has four values:

| Value | Meaning |
|---|---|
| `WINNERS_HIGHER` | winners have higher feature values |
| `WINNERS_LOWER` | losers have higher feature values |
| `NEUTRALS_HIGHER` | neutral stocks have higher values vs extremes |
| `NEUTRALS_LOWER` | neutral stocks have lower values vs extremes |

---

## 6. Characteristic Lifecycle

Lifecycle state depends on how many previous discovery reports contain the same
`(feature_name, direction)` pair:

```
n_history = 0  →  DISCOVERED
n_history = 1  →  REPLICATED
n_history = 2–3 →  VERIFIED
n_history ≥ 4  →  STABLE  (unless effect is declining > 30 % over last 3)
effect declining > 30 % →  WEAKENING
```

---

## 7. Interaction Detection

Only the **top-8** characteristics by `effect_abs` are considered as candidates.
For each pair (c1, c2):

1. Retrieve winner / loser values for both features.
2. Apply `_zscore_pooled` per feature (preserves between-group signal, removes
   scale differences).
3. Sum normalised signals → joint signal.
4. Compute `joint_d = _cohen_d(winner_joint, loser_joint)`.
5. `amplification = abs(joint_d) / max(individual_d_abs) − 1`.
6. Include only if `amplification ≥ dna_interaction_amplify` (default 0.30).

An `amplification` of 0.30 means the pair is at least 30 % more powerful together
than the stronger feature alone.

---

## 8. Market-Wide Feature Filter

Features that are constant across all symbols within a single snapshot (e.g.
VIX, PCR, regime flags) are excluded from winner-vs-loser analysis because they
carry no symbol-discriminating information:

```python
_MARKET_WIDE_FEATURES = frozenset({
    "regime_score", "regime_bull", "regime_bear", "regime_range", "regime_volatile",
    "vol_score", "vix", "vix_low", "vix_high",
    "breadth", "breadth_strong", "breadth_weak",
    "pcr", "pcr_bullish", "pcr_bearish", "pcr_neutral",
    "global_bias", "sector_flow_count", "event_count",
})
```

Features with near-zero pooled variance (`< 1e-14`) are also silently skipped.

---

## 9. Storage

| Location | `data/mls/dna/dna_YYYY-MM-DD.json` |
|---|---|
| Write strategy | `.tmp` → `os.replace()` atomic rename |
| Backup | previous file renamed to `.bak` |
| Encoding | UTF-8 JSON, human-readable indent=2 |

---

## 10. MLSConfig Phase 3 Thresholds

| Field | Default | Meaning |
|---|---|---|
| `dna_min_group_size` | 2 | Minimum winners or losers required |
| `dna_min_effect_size` | 0.30 | Minimum \|Cohen's d\| |
| `dna_min_spearman` | 0.15 | Minimum \|Spearman r\| |
| `dna_interaction_amplify` | 0.30 | Minimum joint amplification |
| `dna_bootstrap_samples` | 200 | Bootstrap CI resamples |
| `dna_winner_labels` | `("TOP_5PCT","TOP_10PCT")` | Which populations count as winners |
| `dna_loser_labels` | `("BOTTOM_5PCT","BOTTOM_10PCT")` | Which populations count as losers |

---

## 11. Thread Safety

`discover()` and all read methods are thread-safe:
- `discover()` holds `_lock` (threading.Lock) during analysis and file write.
- Read methods (`load_report`, `list_reports`, etc.) are stateless filesystem reads.
- Multiple engines with different `data_dir` paths run fully concurrently.
