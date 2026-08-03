# Market Learning System — Phase 1: MarketObserver Design

**Status:** IMPLEMENTED  
**Date:** 2026-08-03  
**Tests:** 61/61 passing

---

## 1. Purpose

MarketObserver is the observation layer of the Market Learning System.

It captures the complete NSE universe state **before** price movement analysis.
It creates immutable daily feature snapshots that every subsequent MLS phase
depends on.

**It never performs learning, comparison, or prediction.**

---

## 2. Position in MLS Architecture

```
MasterOrchestrator (daily, 16:05 IST)
    │
    ▼
MarketObserver                 ← Phase 1 (this module)
    │ capture(snapshot)
    ▼
DailyMarketSnapshot            ← immutable persisted observation
    │
    ▼
StockClassifier                ← Phase 2 (future)
    │
    ▼
PopulationComparator           ← Phase 3 (future)
    ...
```

---

## 3. Files

| File | Role |
|------|------|
| `market_learning/mls_config.py` | All configurable thresholds |
| `market_learning/market_observer_models.py` | Typed data models and exceptions |
| `market_learning/market_observer.py` | MarketObserver class |
| `market_learning/__init__.py` | Package exports |
| `test_market_observer.py` | 61-test suite |

---

## 4. Temporal Contract (INV-01)

The most critical invariant in MLS:

```
feature_timestamp  ≤  09:15 IST  on trading day T
measured outcome   =  Close(T) vs Close(T−1)
```

**Enforcement:**

`MarketObserver._verify_temporal_contract(snapshot.timestamp)` is called
as the FIRST operation inside `capture()` before any feature extraction.

If `snapshot.timestamp.time() > time(9, 15, 0)`, the method:
1. Increments `self._violation_count` (visible via `statistics()`)
2. Raises `TemporalContractViolation` — capture is aborted

Aware datetimes (UTC) are converted to IST before the check.
Naive datetimes are interpreted as IST.

**Boundary is inclusive:** 09:15:00 is valid. 09:15:01 is a violation.

---

## 5. Feature Extraction

MarketObserver reuses the existing `FeatureExtractor` from
`edge_discovery/feature_extractor.py` without modification.

```python
symbol_features: List[SymbolFeatures] = self._fe.extract(snapshot, symbols)
```

This produces 51 features per symbol across 8 categories:
- Price Momentum (mom_1d, mom_5d, mom_10d, mom_20d)
- Volume (volume_ratio, volume_spike)
- RSI (rsi, rsi_oversold, rsi_overbought, rsi_neutral)
- MACD (macd_signal_norm, macd_bull, macd_bear)
- Bollinger Bands (bb_position, bb_upper, bb_lower)
- Volatility (hist_vol_5d, hist_vol_20d, vol_compression)
- IV / Options (iv_rank, iv_spike, iv_low)
- Market Structure (regime_score, vix, breadth, pcr, global_bias, ...)

---

## 6. MLSConfig

All algorithm thresholds live in `MLSConfig`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `feature_deadline_hour` | 9 | Temporal contract hour |
| `feature_deadline_minute` | 15 | Temporal contract minute |
| `feature_deadline_second` | 0 | Temporal contract second |
| `min_universe_size` | 10 | Abort if fewer symbols captured |
| `min_group_size` | 30 | G-ML-01: min winner/loser group size |
| `min_effect_size` | 0.50 | G-ML-02: min Cohen's d |
| `max_p_value` | 0.05 | G-ML-03: max adjusted p-value |
| `snapshot_retention_days` | 90 | Raw snapshot retention |

`MLSConfig.config_hash()` returns a 16-character SHA-256 hash of the
entire config. This is stored in every `ObservationMetadata` for audit
trail reproducibility.

---

## 7. Storage Design

```
data/mls/
└── snapshots/
    ├── snapshot_2026-08-03.json
    ├── snapshot_2026-08-03.bak   ← created on overwrite
    ├── snapshot_2026-08-04.json
    └── ...
```

**Atomic write protocol:**
1. Write to `snapshot_YYYY-MM-DD.tmp`
2. If `snapshot_YYYY-MM-DD.json` exists: copy to `.bak`
3. `os.replace(tmp, target)` — atomic rename on both Linux and Windows

All writes are protected by `threading.Lock()` in `MarketObserver`.

The `data/mls/` directory is the same Docker volume as other `data/`
files (`./data:/app/data`). No Docker changes required.

---

## 8. Output Models

### DailyMarketSnapshot

The primary output of `capture()`. Immutable once persisted.

```json
{
  "snapshot_id":       "MLS-SNAP-20260803",
  "trading_date":      "2026-08-03",
  "feature_timestamp": "2026-08-03T09:10:00",
  "regime":            "bull_trend",
  "volatility":        "medium",
  "vix":               15.0,
  "pcr":               0.9,
  "breadth":           0.6,
  "global_bias":       0.3,
  "universe_size":     20,
  "symbols":           ["NIFTY", "BANKNIFTY", ...],
  "observations":      [...],
  "metadata":          {...},
  "created_at":        "2026-08-03T16:05:12.433"
}
```

### MarketObservation

One per symbol. Contains all 51 pre-move features.

```json
{
  "symbol":            "RELIANCE",
  "feature_timestamp": "2026-08-03T09:10:00",
  "features":          {"mom_5d": 0.023, "rsi": 62.1, ...},
  "feature_count":     51
}
```

### ObservationMetadata

Audit provenance for the capture run.

```json
{
  "run_id":                     "MLS-OBS-20260803-091000",
  "temporal_contract_verified": true,
  "mls_config_hash":            "4a644495a9b80239",
  "regime":                     "bull_trend",
  "universe_size":              20,
  "feature_count":              51,
  "warnings":                   []
}
```

---

## 9. Thread Safety

- `capture()` acquires `self._lock` during the atomic write step only.
  Feature extraction runs outside the lock (pure computation, no shared state).
- `load_snapshot()` and `statistics()` are read-only and intrinsically safe.
- `list_snapshots()` reads directory entries (atomic on all target platforms).
- Verified by T61: 10 concurrent captures to 10 different dates succeed with zero corruption.

---

## 10. Failure Modes

| Failure | Behaviour |
|---------|-----------|
| `snapshot.timestamp > 09:15 IST` | Raises `TemporalContractViolation`, increments `_violation_count` |
| `universe_size < min_universe_size` | Raises `MarketObserverError` |
| Storage directory missing | Created automatically on first write |
| `load_snapshot()` on missing date | Returns `None` (not an error) |
| Data feed failure upstream | Caller decides; MarketObserver never retries |

---

## 11. Governance

- MarketObserver does **not** learn, compare, or predict.
- MarketObserver does **not** write to any ARS module.
- MarketObserver does **not** generate hypotheses.
- Every `DailyMarketSnapshot` is read-only after `_persist()`.
- The temporal contract is **not** configurable below 09:15:00 IST.
  (The field is configurable to allow earlier deadlines — e.g. 09:10 —
  but the default is the market open time.)
