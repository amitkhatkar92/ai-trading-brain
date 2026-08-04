# Point-in-Time Universe Engine — Design

**R-006 | IIOS Research Infrastructure**
**Version:** 1.0.0
**Status:** COMPLETE — 156/156 tests pass

---

## Problem Statement

Every historical replay that uses the current NIFTY500 list introduces
**survivorship bias**: delisted, merged, or removed companies are absent,
making strategies appear more profitable than they actually were.

**R-006 solves this permanently**: the Point-in-Time Universe Engine (PTUE)
becomes the sole authoritative provider of historical market universes.
No replay logic shall determine historical constituents itself.

---

## Architecture

```
PointInTimeUniverseEngine
  │
  ├── History Layer (per universe)
  │     data/ars/ptue/{UNIVERSE_NAME}/history.json
  │     Constituent records: symbol, effective_from, effective_to, reason
  │
  ├── Fallback Layer
  │     data/nifty500_universe.json (static, current snapshot)
  │     Used ONLY when no history file exists + fallback_enabled=True
  │     Every fallback logged with [PTUEFallback] tag
  │
  ├── Cache Layer
  │     Dict[(date, universe_name) -> HistoricalUniverse]
  │     Invalidated by: invalidate_cache(), reload(), add_constituent()
  │
  └── Thread Safety
        threading.RLock() guards all mutable state
        Read-only after loading — all public methods are safe to call concurrently
```

---

## Files

| File | Purpose |
|---|---|
| `autonomous_research/ptue_models.py` | Data models, errors, constants |
| `autonomous_research/ptue_config.py` | PTUEConfig |
| `autonomous_research/ptue.py` | PointInTimeUniverseEngine |
| `data/ars/ptue/NIFTY500/history.json` | NIFTY500 constituent history (bootstrapped) |
| `data/ars/ptue/NIFTY50/history.json` | NIFTY50 constituent history (bootstrapped) |
| `data/ars/ptue/NIFTY100/history.json` | NIFTY100 constituent history (bootstrapped) |

---

## Constituent History Format

```json
{
  "universe": "NIFTY500",
  "version": "1.0",
  "description": "NIFTY500 constituent history",
  "last_updated": "2026-08-04",
  "constituents": [
    { "symbol": "RELIANCE", "effective_from": "2020-01-01", "effective_to": null,         "reason": "INITIAL" },
    { "symbol": "SUZLON",   "effective_from": "2023-01-01", "effective_to": null,         "reason": "ADDED"   },
    { "symbol": "INFY",     "effective_from": "2020-01-01", "effective_to": "2022-12-31", "reason": "REMOVED" }
  ]
}
```

### Constituent Record Rules

- `effective_from` — the first date the symbol was in the universe (inclusive)
- `effective_to` — the last date the symbol was in the universe (inclusive), or `null` = still active
- `reason` — `"INITIAL"` (bootstrapped), `"ADDED"` (new entry), `"REMOVED"` (departure), or custom
- A symbol active on date D satisfies: `effective_from <= D` AND (`effective_to` is `null` OR `effective_to >= D`)

---

## Decision Logic

```
get_universe(date, universe_name)
  ├── cache hit? → return cached HistoricalUniverse
  ├── history file exists?
  │     yes → load records, filter by date, coverage=1.0, is_fallback=False
  │     no  → static fallback?
  │             yes → load nifty500_universe.json, coverage=0.5, is_fallback=True
  │                   LOG [PTUEFallback]
  │             no  → raise UniverseNotFoundError
  └── cache result, return HistoricalUniverse
```

---

## Replay Integration

The `ResearchCoordinator._exec_replay()` now:
1. Extracts `replay_date` from `study_plan.dataset_requirements[0].date_start`
2. Calls `ptue.get_universe(replay_date)` to get the exact historical universe
3. Records in `ctx`: `ptue_universe_date`, `ptue_universe_symbols`, `ptue_universe_count`, `ptue_universe_source`, `ptue_universe_is_fallback`, `ptue_universe_coverage`
4. Includes universe provenance in the research report

**Every replay report now includes:**
- Universe name and date
- Number of constituents
- Source (HISTORY_FILE or STATIC_FALLBACK)
- Coverage score
- Whether survivorship bias may be present (is_fallback=True)

---

## MLS and DNA Integration

Both the Market Learning System (MLS) and DNA Discovery should:
1. Request PTUE universe **before** loading market data for a replay date
2. Pass only the universe symbols to the data layer
3. Never hardcode the current NIFTY500 list

Example:
```python
universe = ptue.get_universe(replay_date, "NIFTY500")
symbols_for_replay = universe.symbols  # historically correct
```

---

## Backward Compatibility

When no history file exists and `fallback_enabled=True` (default):
- System falls back to the current static universe
- `HistoricalUniverse.is_fallback = True`
- `HistoricalUniverse.coverage = 0.5`
- Every query logs `[PTUEFallback]` at WARNING level

This means all existing studies continue to work. As historical constituent
files are added, the PTUE automatically uses them for new queries.

---

## Adding Future Indices

Adding a new index requires only:
1. Create `data/ars/ptue/{NEW_INDEX}/history.json` with constituent records
2. Pass `universe_name="{NEW_INDEX}"` to `get_universe()`

Zero changes to replay logic. Zero changes to research coordinator.

---

## Scientific Bias Status

| Bias | Before R-006 | After R-006 |
|---|---|---|
| Survivorship bias | Present in all replays | Eliminated when history file exists |
| Survivorship bias (fallback) | Implicit | Explicit (`is_fallback=True`, logged) |
| Look-ahead bias | Not addressed here | Not addressed here |

---

## Test Coverage

| Suite | Range | Count | Coverage |
|---|---|---|---|
| Models | T001-T025 | 25 | Constituent, errors, constants |
| get_universe (history file) | T026-T045 | 20 | Happy path, to_dict |
| Boundary dates | T046-T055 | 10 | Exact boundaries, invalid dates |
| Additions and removals | T061-T075 | 15 | history(), contains(), case-insensitive |
| Static fallback | T076-T090 | 15 | Fallback logic, disabled fallback |
| Statistics and coverage | T091-T110 | 20 | Statistics, CoverageReport |
| Cache | T111-T120 | 10 | Hit, miss, invalidate, reload |
| Bootstrap from static | T121-T130 | 10 | File creation, sub-index filter, dry_run |
| add/remove_constituent | T131-T140 | 10 | CRUD operations |
| Replay integration | T141-T150 | 10 | RC wiring, PTUE ctx in stage |
| MLS + thread safety | T151-T160 | 10 | Concurrent queries |
| Real data round-trip | T160b | 1 | Actual nifty500_universe.json |
| **Total** | | **156** | |
