# DNAConsensusEngine — Test Report (MLS Phase 4)

## Summary

| Metric | Value |
|---|---|
| **Total tests** | 90 |
| **Passed** | 90 |
| **Failed** | 0 |
| **Coverage** | All public API methods, all lifecycle states, all drift types, all math functions, thread safety |

---

## Test Groups

### T01–T04: MLSConfig Phase 4 Defaults
Verifies all 14 Phase 4 configuration fields have correct defaults.
Confirms weights sum to exactly 1.0 (within 1e-9).
Confirms individual overrides work without side-effects.

### T05–T07: Engine Instantiation
Default init, custom config, custom data directory.
Verifies `_dir` and `_lib_path` are set correctly.

### T08–T14: `update()` Structure
Return type is `ConsensusLibrary`. Library ID format `MLS-LIB-YYYYMMDD`.
`as_of_date` matches report's `trading_date`.
Multi-feature reports produce correct `all_consensus` length.
JSON file is created on disk after first update.
DriftReports are built once `evidence_count >= 2`.
`ConsensusStatistics` is present in the returned library.

### T15–T19: ConsensusDNA Fields
- `consensus_id` starts with `CON-` and is derived from `sha256(feature::direction)[:8]`.
- `direction` is correctly set from the `DNACharacteristic`.
- `evidence_count` accumulates correctly over N updates.
- `first_seen` is set on creation and never overwritten (immutable).
- `consensus_score`, `replication_frequency`, `temporal_stability`, `regime_consistency`, `sector_consistency` all remain in [0, 1].

### T20–T23: ConfidenceEvolution
- Structure: returns a list of `ConfidenceEvolution` objects, each with `points`, `trend_slope`, `trend_direction`.
- Point count matches the number of update calls.
- IMPROVING trend classification (slope > threshold).
- Direction filter (`direction="WINNERS_HIGHER"`) returns only matching entries.

### T24–T27: DriftReport
- Report structure: correct `drift_report_id` format, all four `DriftType` values present.
- All drift magnitudes in [0, 1].
- Full round-trip serialisation via `to_dict()` / `from_dict()`.

### T28–T31: DNAStability / `stable_dna()` / `retired_dna()`
- `stable_dna()` empty before any updates.
- After consistent updates, feature appears in `stable_dna()`.
- Retired features are excluded from `stable_dna()`.
- `retired_dna()` correctly identifies retired entries.

### T32–T35: ConsensusStatistics
- Type is correct.
- `total_consensus_dna`, `institutional_count`, `avg_consensus_score` are accurate.

### T36–T40: ConsensusLibrary Model
- Full round-trip (JSON → dict → reconstruct → dict matches).
- `master_consensus` contains only INSTITUTIONAL entries.
- `drift_reports` count is correct.
- `statistics` field is present in serialised dict.
- `library_id` format is `MLS-LIB-YYYYMMDD`.

### T41–T46: Lifecycle Transitions
Each state is tested in isolation:
- 1 update → `DISCOVERED`
- 2 updates → `REPLICATED`
- 5 updates → `VERIFIED`
- 10 updates → `INSTITUTIONAL` (score ≥ 0.60)
- Alternating regimes (10 updates) → `DRIFTING`
- 35-day absence → `RETIRED` (retirement sweep in next update)

### T47–T51: Consensus Score Math
- Perfect inputs (all 1.0) → score = 1.0.
- Zero inputs → score approaches 0 (only trend_score=0.5 contributes via confidence weight).
- Replication component correctly weighted.
- Positive trend slope boosts score by `confidence_weight * 0.5`.
- Over-range inputs (all 1.5, trend=100) are clamped to ≤ 1.0.

### T52–T55: Temporal Stability Math
- Single observation → 1.0.
- All same → 1.0 (zero variance).
- High variation → low stability (0.18).
- Moderate variation → near-1.0 stability (0.99).

### T56–T59: Regime Consistency Math
- 1 regime → 0.20 (`1/5`).
- 3 regimes → 0.60.
- 5 regimes → 1.00.
- Empty input → 0.0.

### T60–T63: Drift Detection Math
- Large effect shift → `statistical_drift ≈ 0.80`.
- Alternating regimes → `regime_drift = 1.00`.
- Declining observation frequency → `temporal_drift = 1.00`.
- Declining confidence → `feature_drift = 1.00`.

### T64–T67: Trend Slope (OLS)
- Perfectly positive sequence → slope = 1.0.
- Perfectly negative sequence → slope = -1.0.
- Flat sequence → slope = 0.0.
- Single point → slope = 0.0 (no slope computable).

### T68–T71: Storage
- `library.json` is created on first `update()`.
- Library is loadable after `update()` with correct `as_of_date`.
- Evidence accumulates correctly across 3 updates (`evidence_count = 3`).
- A `.bak` file is created when an existing library is overwritten.

### T72–T75: Query API
- `stable_dna()` returns features passing all three stability thresholds.
- `retired_dna()` returns only RETIRED entries.
- `confidence_history()` returns correct observation count.
- `drift_report(feature_name=...)` filters correctly.

### T76–T80: `master_library()`
- Returns `ConsensusLibrary` type.
- `master_consensus` contains only INSTITUTIONAL entries.
- `statistics` field is present.
- Returns empty library before any updates.
- `library_id` format is correct.

### T81–T86: Traceability
- `all_observations` forms a complete audit trail with correct dates.
- `regime_counts` accurately tracks per-regime observation counts.
- `first_seen` remains unchanged after 3 updates (immutable).
- `evidence_count == len(all_observations)` invariant holds.
- `consensus_id` is deterministic (same inputs → same hash).
- One `DriftReport` per feature in `drift_reports`.

### T87–T90: Thread Safety
- 8 concurrent `update()` calls to isolated engines succeed without errors.
- Idempotent update (same date, 3 concurrent calls) leaves `evidence_count = 1`.
- Concurrent read/write (update + master_library() in threads) produces no errors.
- `master_library()` can be called from 4 threads simultaneously.

---

## Notable Bugs Found and Fixed During Development

### Bug 1: `_load_store` Key Mismatch
**Symptom:** Every `update()` created a new ConsensusDNA instead of merging.
**Root cause:** `_load_store()` keyed the return dict by `consensus_id`
(`"CON-bb187eb6"`) but `update()` looked up by `_consensus_key`
(`"rsi::WINNERS_HIGHER"`). Keys never matched.
**Fix:** Changed `_load_store()` to use `_consensus_key(c.feature_name, c.direction)`.

### Bug 2: `fresh_dir()` Stale Data Pollution
**Symptom:** T18 (`first_seen` immutable) failed on second+ runs of the test suite.
**Root cause:** `fresh_dir()` used `exist_ok=True` but never cleaned the directory.
Temp directories persisted from prior runs (including runs with the broken key
mismatch), leaving stale `library.json` files. On subsequent runs, the first
`update()` found existing data and merged into the stale entry, inheriting the
wrong `first_seen`.
**Fix:** `fresh_dir()` now calls `shutil.rmtree()` before creating the directory.

### Bug 3: T22 Slope Equals Threshold
**Symptom:** `trend_direction` was `"STABLE"` instead of `"IMPROVING"`.
**Root cause:** The confidence increment `0.60 + i * 0.05` with 4 points produces
an OLS slope of exactly `0.05`, which equals `consensus_trend_declining_slope = 0.05`.
The condition `slope > thr` is `False` at equality.
**Fix:** Changed test increments to `0.50 + i * 0.10` (slope = 0.10 > 0.05).

### Bug 4: `_consensus_score` Unclamped
**Symptom:** Over-range inputs (each component 1.5) produced score = 1.45.
**Root cause:** The weighted sum was returned directly without clamping.  The
docstring stated the function returns values in [0, 1].
**Fix:** Added `min(1.0, max(0.0, raw))` at the return.
