# DNADiscoveryEngine — Test Report

**MLS Phase 3 | Test file:** `test_dna_discovery_engine.py`  
**Result: 83 / 83 passed, 0 failed**

---

## Summary

| Metric | Value |
|---|---|
| Total tests | 83 |
| Passed | 83 |
| Failed | 0 |
| Test groups | 21 |
| Approximate runtime | ~2 s |

---

## Test Groups

| # | Group | Tests | Coverage |
|---|---|---|---|
| T01–T03 | MLSConfig Phase 3 defaults | 3 | Default values, overrides, hash change |
| T04–T06 | Engine instantiation | 3 | Default init, custom config, custom data_dir |
| T07–T14 | `discover()` structure | 8 | Return type, IDs, DNA profiles, regime, characteristics, persistence |
| T15–T19 | Winner characteristics | 5 | Existence, direction, effect threshold, confidence range, membership |
| T20–T22 | Loser characteristics | 3 | Existence, direction, effect threshold |
| T23–T24 | Neutral analysis | 2 | Direction labels, n_members |
| T25–T29 | Cohen's d math | 5 | Positive/negative input, zero groups, large separation, insufficient data |
| T30–T33 | Spearman math | 4 | Perfect monotonic, anti-monotonic, constant, n<3 |
| T34–T36 | Bootstrap CI | 3 | Containment, finiteness, insufficient data |
| T37–T39 | Feature type detection | 3 | BINARY, CONTINUOUS, ORDINAL |
| T40–T41 | `FeatureEvidence` model | 2 | Round-trip serialisation, field presence |
| T42–T46 | `DNACharacteristic` model | 5 | Round-trip, char_id prefix, default lifecycle, effect_abs, feature_type |
| T47–T50 | `DNAInteraction` | 4 | Structure, amplification invariant, round-trip, feature validity |
| T51–T55 | DNA profiles | 5 | WinnerDNA/LoserDNA/NeutralDNA round-trips, n_members, population_ids |
| T56–T59 | `DiscoveryReport` | 4 | Round-trip, `get_characteristic()`, `characteristics_by_direction()`, universe_size |
| T60–T63 | Lifecycle advancement | 4 | DISCOVERED (no history), REPLICATED (1), VERIFIED (2), STABLE (4+) |
| T64–T67 | Storage | 4 | Load after discover, missing date → None, sorted list, .bak on overwrite |
| T68–T73 | Statistics | 6 | Type, counts, top features, avg_effect_size, lifecycle distribution, missing → None |
| T74–T78 | Query API | 5 | `winner_dna()`, `loser_dna()`, `neutral_dna()`, `list_characteristics(date)`, `list_characteristics(all)` |
| T79–T82 | Edge cases | 4 | `InsufficientDataError`, min_group_size=2, constant feature skipped, market-wide excluded |
| T83 | Thread safety | 1 | 8 concurrent `discover()` calls in isolated dirs — 8/8 succeed |

---

## Key Design Validation

### Synthetic fixture approach
Tests bypass `FeatureExtractor` entirely, constructing `MarketObservation` objects
with known feature values (winner rsi=75, loser rsi=25, etc.) and controlled
Gaussian variation (5 % of absolute value for continuous features, no variation for
binary features). This gives deterministic, reproducible assertions.

### Statistical math validation
Pure-Python implementations of Cohen's d, Spearman, and bootstrap CI are tested
against known inputs:
- `_cohen_d([1,2,3], [4,5,6])` → d ≈ −3.606 (negative: group a < group b)
- `_spearman([1,2,3,4,5], [1,2,3,4,5])` → 0.9999… ≈ 1.0
- Bootstrap CI on well-separated groups: d=4.38, CI=[3.51, 11.53] (seed=42)

### Lifecycle progression
Four separate engines with accumulating history (0, 1, 2, 4 previous reports) all
using identical `_WIN_FEATS` / `_LOS_FEATS` templates confirm the full
DISCOVERED → REPLICATED → VERIFIED → STABLE progression.

### Interaction invariant (T48)
Every reported interaction is verified to have `amplification >= dna_interaction_amplify`.
This is the correct invariant: the engine never reports a sub-threshold interaction.

### Thread safety (T83)
Eight threads each call `discover()` with distinct `data_dir` paths concurrently.
All 8 succeed — no races, no corrupted files.

---

## Sentinel edge cases confirmed

| Scenario | Behaviour |
|---|---|
| Zero pooled variance in Cohen's d | Returns ±1000 sentinel |
| n < 3 in Spearman | Returns 0.0 |
| Insufficient data in bootstrap | Returns (0.0, 0.0) |
| Constant feature (zero pooled var) | `_analyse_one_feature` returns None |
| Market-wide feature | Excluded before analysis |
| Group smaller than `dna_min_group_size` | Raises `InsufficientDataError` |
