# PopulationClassifier Design Document

**MLS Phase 2 — Population Classification Layer**

---

## 1. Purpose

The PopulationClassifier converts an immutable `DailyMarketSnapshot`
(produced by MarketObserver) into labeled comparison populations.
These populations are the raw material for Phase 3 DNA discovery:
the CharacteristicsEngine identifies statistical separations between
groups to find features that reliably predict performance differences.

The classifier does **not** learn, predict, or generate signals.
It only creates structured groupings.

---

## 2. Design Principles

### 2.1 Eight Independent Dimensions

Every stock receives exactly one label per classifier type.
Eight classifiers → eight labels per stock.
Multi-label membership comes from **cross-dimension combination**:
a stock can be simultaneously `TOP_5PCT` AND `SECTOR_WINNER` AND
`HIGH_LIQUIDITY` AND `REGIME_ALIGNED`.

| # | ClassifierType    | Feature Used         | Groups (n) |
|---|-------------------|----------------------|------------|
| 1 | PERFORMANCE       | mom_1d / external    | 7          |
| 2 | SECTOR            | sector_strength      | 3          |
| 3 | REGIME            | mom_5d, iv_rank, bb  | 2          |
| 4 | LIQUIDITY         | liquidity_score      | 3          |
| 5 | VOLATILITY        | hist_vol_5d          | 3          |
| 6 | MARKET_CAP        | liquidity_score      | 3          |
| 7 | VOLUME_EXPANSION  | volume_ratio_raw     | 3          |
| 8 | RELATIVE_STRENGTH | rsi                  | 3          |

Total populations per classification: **27**.

### 2.2 Exhaustive + Mutually Exclusive

Every classifier assigns **all** stocks to exactly one group.
No stock is ever in two groups of the same classifier type.
The classifier validates this invariant with `OrphanStockError`.

### 2.3 Immutability

The classifier reads only from `DailyMarketSnapshot`.
It never writes back to MarketObserver storage.
Classification results are stored in a separate directory tree.

---

## 3. Performance Classifier Detail

Performance classification uses **exclusive percentile boundaries**
computed with `int()` (floor) to avoid fractional symbol counts.

For a 20-symbol universe with default config fractions (1/5/10%):

```
n  = 20
n1  = int(0.01 * 20) = 0   -> TOP_1PCT     = [0:0]   = 0 symbols
n5  = int(0.05 * 20) = 1   -> TOP_5PCT     = [0:1]   = 1 symbol
n10 = int(0.10 * 20) = 2   -> TOP_10PCT    = [1:2]   = 1 symbol
                              NEUTRAL       = [2:18]  = 16 symbols
bn10 = 2                   -> BOTTOM_10PCT = [18:19]  = 1 symbol
bn5  = 1                   -> BOTTOM_5PCT  = [19:20] → [19:19] = 1 symbol (guarded)
bn1  = 0                   -> BOTTOM_1PCT  = [20:20]  = 0 symbols
Total = 0+1+1+16+1+1+0 = 20 ✓
```

The boundary guard `max(n10, n - bn_x)` ensures the NEUTRAL group
never goes negative when percentile slices overlap in tiny universes.

---

## 4. Regime Classifier Detail

Regime alignment is determined per market regime type:

| Regime         | Signal Feature | Condition for ALIGNED      |
|----------------|----------------|----------------------------|
| `bull_trend`   | mom_5d         | mom_5d > regime_mom_threshold (0.0) |
| `bear_market`  | mom_5d         | mom_5d < regime_mom_threshold (0.0) |
| `volatile`     | iv_rank        | iv_rank > 0.5              |
| `range_market` | bb_position    | abs(bb_position) < 0.5     |

---

## 5. Outcomes Source

`classify(snapshot, outcomes=None)` accepts an optional dict
`{symbol -> realized_return}`.

- **`outcomes=None`** (default): uses `mom_1d` from observation features
  as a proxy for realized return. `outcomes_source = "feature_proxy"`.
- **`outcomes=dict`** (provided): uses the external returns directly.
  `outcomes_source = "external"`.

This allows the system to backfill classifications with actual next-day
returns when they become available EOD, while still being able to run
intraday classifications using available feature proxies.

---

## 6. Storage Layout

```
data/
  mls/
    snapshots/          <- MarketObserver (Phase 1)
      snapshot_YYYY-MM-DD.json
    classifications/    <- PopulationClassifier (Phase 2)
      classification_YYYY-MM-DD.json
      classification_YYYY-MM-DD.bak  (previous version on overwrite)
```

Atomic write: JSON is written to `.tmp` then `os.replace()` to final path,
matching the same pattern used in Phase 1 MarketObserver.

---

## 7. Thread Safety

A `threading.Lock()` guards only the `_persist()` method.
Classification logic (`classify()`) is stateless except for the final
persist step, so concurrent calls on different dates proceed in parallel
until the lock is acquired for writing.

---

## 8. Integration Points

| Layer              | How PopulationClassifier Is Used               |
|--------------------|------------------------------------------------|
| MarketObserver     | Reads `DailyMarketSnapshot` produced by Phase 1|
| CharacteristicsEngine (Phase 3) | Reads `ClassificationResult` to find DNA |
| MasterOrchestrator | Calls `classify()` after market close          |
| Telegram `/status` | May query `statistics()` for daily summary     |

---

## 9. Configuration Reference

All thresholds are in `MLSConfig` (see `market_learning/mls_config.py`).
Phase 2 fields begin at `perf_top1_frac`.

To tune without changing source code, instantiate with a custom config:
```python
cfg = MLSConfig(rs_strong_rsi=70.0, sector_winner_threshold=0.70)
pc  = PopulationClassifier(config=cfg)
```

---

## 10. Architectural Constraints

- PopulationClassifier is a **read-only consumer** of Phase 1 snapshots.
- It does **not** depend on broker feeds, live market data, or trade state.
- It can run on historical snapshots at any time (backfill mode).
- It does **not** raise `TemporalContractViolation` — that is Phase 1's concern.
- The `OrphanStockError` guard is a defensive invariant; it should never
  trigger in practice unless a classifier has a logic bug.
