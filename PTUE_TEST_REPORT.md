# Point-in-Time Universe Engine — Test Report

**R-006 | IIOS Research Infrastructure**
**Test file:** `test_ptue.py`
**Result:** 156/156 PASS

---

## Summary

| Metric | Value |
|---|---|
| Total tests | 156 |
| Passed | 156 |
| Failed | 0 |

---

## Test Suites

| Suite | Range | Count | Coverage |
|---|---|---|---|
| Models | T001-T025 | 25 | Constituent fields, is_active_on(), to_dict/from_dict, errors, constants |
| get_universe (history file) | T026-T045 | 20 | Happy path, additions, removals, to_dict |
| Boundary dates | T046-T055 | 10 | Exact effective_from/to, one day before/after, early/late dates, invalid format |
| Additions and removals | T061-T075 | 15 | Before/after addition, history(), contains(), case-insensitive |
| Static fallback | T076-T090 | 15 | Fallback triggered, disabled fallback → error, empty static → error |
| Statistics and coverage | T091-T110 | 20 | UniverseStatistics fields, CoverageReport per universe |
| Cache | T111-T120 | 10 | Hit returns identical object, miss creates new, invalidate, reload, version() |
| Bootstrap from static | T121-T130 | 10 | File creation, symbol count, sub-index filter, dry_run=True no write |
| add/remove_constituent | T131-T140 | 10 | Active after add, not active before, remove sets effective_to, invalid date raises |
| Replay integration | T141-T150 | 10 | _resolve_replay_date(), RC wiring, stage.meta fields, date/source/count/fallback |
| MLS + thread safety | T151-T160 | 10 | Multi-universe contains(), 20 concurrent get_universe, 10 concurrent contains |
| Real data | T160b | 1 | Actual nifty500_universe.json bootstrap round-trip |
| **Total** | T001-T160+ | **156** | |

---

## Key Scenarios Covered

### Survivorship bias elimination
- Symbol removed from index → not in universe before its `effective_from`, not in universe after its `effective_to` ✓
- Symbol added to index → only appears from `effective_from` onwards ✓
- Early date (year 2000) → empty universe (nothing was tracked) ✓

### Boundary precision
- Symbol active on exact `effective_from` day ✓
- Symbol active on exact `effective_to` day ✓
- Symbol NOT active on `effective_from - 1 day` ✓
- Symbol NOT active on `effective_to + 1 day` ✓

### Fallback safety
- Fallback triggered when no history file ✓
- `is_fallback=True` and `coverage=0.5` for all fallback results ✓
- `[PTUEFallback]` logged at WARNING ✓
- `UniverseNotFoundError` when fallback disabled ✓

### RC replay integration
- `_resolve_replay_date()` extracts date from `dataset_requirements[0].date_start` ✓
- RC with PTUE wired: replay stage includes `ptue_date`, `ptue_source`, `ptue_count`, `ptue_is_fallback` in `stage.meta` ✓
- `stage.output_summary` includes PTUE provenance ✓
- No PTUE → replay still works (backward compatible) ✓

### Thread safety
- 20 concurrent `get_universe()` calls: 0 errors, all return same count ✓
- 10 concurrent `contains()` calls: 0 errors, all return True ✓
- Cache coherent under concurrent access ✓

### Constitutional answers
1. **Can every replay reproduce the exact historical universe?** YES — history files contain full membership timeline with effective dates.
2. **Has survivorship bias been eliminated?** YES — for universes with history files (`coverage=1.0`). Flagged but not eliminated for fallback universes.
3. **Can DNA discoveries be trusted across time?** YES — DNA analysis can now be gated on `ptue.contains(symbol, date)`.
4. **Can future indices be added without changing replay logic?** YES — add `data/ars/ptue/{NEW_INDEX}/history.json`, use `universe_name="{NEW_INDEX}"`.
