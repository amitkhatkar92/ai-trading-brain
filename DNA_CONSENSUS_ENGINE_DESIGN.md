# DNAConsensusEngine — Design Document (MLS Phase 4)

## Purpose

DNAConsensusEngine transforms daily `DiscoveryReport` outputs (from Phase 3's
`DNADiscoveryEngine`) into a persistent, institutional-grade knowledge base of
market patterns.  It accumulates evidence across trading sessions, tracks
lifecycle state, detects statistical drift, and promotes the most reliable
patterns to **INSTITUTIONAL** status for downstream consumption by the trading
layers.

---

## Architectural Position

```
MarketObserver (Phase 1)
      ↓
PopulationClassifier (Phase 2)
      ↓
DNADiscoveryEngine (Phase 3)  →  DiscoveryReport (one per day)
      ↓
DNAConsensusEngine (Phase 4)  →  ConsensusLibrary (persistent, grows daily)
      ↓
[Future Phase 5] Strategy layer consumes ConsensusLibrary.master_consensus
```

Storage: `data/mls/consensus/library.json`  
Persistence: atomic `.tmp → rename` with `.bak` safety copy.

---

## Core Design Decisions

### 1. Single Persistent File

All ConsensusDNA entries live in one file.  Every `update()` call reads the
current file, merges new observations, and atomically overwrites it.  There is
no append-only log.  This keeps the storage footprint predictable and the
read-path trivial.

### 2. Keying by Feature Identity, Not by ID

Each ConsensusDNA is looked up via:

```python
key = f"{feature_name}::{direction.value}"   # e.g. "rsi::WINNERS_HIGHER"
```

The `consensus_id` (`CON-{sha256[:8]}`) is the same value but is used for
external references only.  Storing by `_consensus_key` means the in-memory
dict survives across reads/writes without identity collisions.

### 3. Fully Deterministic Lifecycle

Lifecycle state is computed from metrics alone — no manual overrides:

```
absent_days >= retirement_days  →  RETIRED
max_drift   >= drift_threshold  →  DRIFTING
count >= 10 AND trend declining →  WEAKENING
count >= 10 AND score >= 0.60  →  INSTITUTIONAL
count >= 5                      →  VERIFIED
count >= 2                      →  REPLICATED
else                            →  DISCOVERED
```

### 4. Idempotent Updates

Calling `update()` twice with the same `trading_date` is safe.  The `_merge`
method checks `existing_dates` and short-circuits if the date was already
recorded, leaving the ConsensusDNA unchanged.

### 5. Thread Safety

`update()` acquires a `threading.Lock` for the full read-merge-write cycle.
All other public methods are read-only (they call `_load_library()` which holds
no lock).

---

## Consensus Score

A weighted sum of six normalised metrics, clamped to [0, 1]:

| Component | Weight | Source |
|---|---|---|
| Replication frequency | 0.25 | count / elapsed days |
| Temporal stability | 0.20 | 1 − CV of effect_abs |
| Regime consistency | 0.20 | distinct_regimes / 5 |
| Sector consistency | 0.15 | (same as regime, Phase 4) |
| Confidence trend | 0.10 | OLS slope → [0,1] score |
| Feature persistence | 0.10 | obs in window / window |

Confidence trend conversion:
```
trend_score = clamp(0.5 + slope / (2 × threshold), 0, 1)
```

A flat slope → 0.5; strong positive → 1.0; strong negative → 0.0.

---

## Drift Detection

Four drift types are computed per ConsensusDNA when `evidence_count >= 2`:

| Type | Metric | Formula |
|---|---|---|
| STATISTICAL | `_statistical_drift` | |early_mean − late_mean| / max(|early_mean|, ε) |
| REGIME | `_regime_drift` | proportion of adjacent observations with different regime |
| TEMPORAL | `_temporal_drift` | 1 − (recent_freq / historical_freq), clamped |
| FEATURE | `_feature_drift` | |slope| / threshold, clamped |

A DriftReport is attached to the ConsensusLibrary for any ConsensusDNA with
`evidence_count >= 2`.  Drift is marked **significant** when its magnitude
exceeds `consensus_drift_threshold` (default 0.30).

---

## Module-level Pure Functions

All heavy computation lives in module-level pure functions, making them
directly testable without instantiating the engine:

```python
_trend_slope(ys)                   # OLS slope
_temporal_stability(effects)       # 1 - CV, capped [0,1]
_replication_freq(count, first, last)
_regime_consistency(regime_counts, N=5)
_feature_persistence(obs_dates, window, as_of_date)
_consensus_score(rep, temp, regime, sector, trend, pers, cfg)
_compute_consensus_state(count, score, max_drift, conf_trend, absent_days, cfg)
_compute_level(state)
_statistical_drift(effects, window)
_regime_drift(obs)
_temporal_drift(obs_dates, window, as_of_date)
_feature_drift(confidences, window, threshold)
_make_consensus_id(feature_name, direction)
_consensus_key(feature_name, direction)
_absent_days(last_seen, trading_date)
```

---

## Configuration (MLSConfig Phase 4 fields)

| Field | Default | Meaning |
|---|---|---|
| `consensus_institutional_min_count` | 10 | Evidence count to reach INSTITUTIONAL |
| `consensus_institutional_min_score` | 0.60 | Score threshold for INSTITUTIONAL |
| `consensus_retirement_absent_days` | 30 | Calendar days absent → RETIRED |
| `consensus_drift_threshold` | 0.30 | Drift magnitude to flag as significant |
| `consensus_drift_window` | 7 | Rolling window (days) for drift calculations |
| `consensus_trend_window` | 7 | OLS window for slope calculation |
| `consensus_trend_declining_slope` | 0.05 | |slope| threshold to classify trend |
| `consensus_stability_min_rep_freq` | 0.50 | Minimum rep_freq for stable_dna() |
| `consensus_stability_min_temporal` | 0.50 | Minimum temporal_stability for stable_dna() |
| `consensus_stability_min_regime` | 0.40 | Minimum regime_consistency for stable_dna() |
| `consensus_w_replication` | 0.25 | Score weight |
| `consensus_w_temporal` | 0.20 | Score weight |
| `consensus_w_regime` | 0.20 | Score weight |
| `consensus_w_sector` | 0.15 | Score weight |
| `consensus_w_confidence` | 0.10 | Score weight |
| `consensus_w_persistence` | 0.10 | Score weight |

---

## Key Invariants

1. Weights sum to exactly 1.0.
2. `consensus_score` is always in [0, 1].
3. `first_seen` is set once at `_create_new` and never overwritten.
4. `all_observations` is sorted by date and deduplicated by date.
5. `evidence_count == len(all_observations)` at all times.
6. `master_consensus` contains only INSTITUTIONAL ConsensusDNA.
7. `DriftReport` is only built when `evidence_count >= 2`.
