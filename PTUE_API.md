# Point-in-Time Universe Engine — API Reference

**R-006 | IIOS Research Infrastructure**

---

## Instantiation

```python
from autonomous_research import PointInTimeUniverseEngine, PTUEConfig

ptue = PointInTimeUniverseEngine(
    config=PTUEConfig(
        history_root="data/ars/ptue",
        static_fallback_path="data/nifty500_universe.json",
        fallback_enabled=True,
        log_every_fallback=True,
        cache_enabled=True,
        dry_run=False,
    )
)
```

---

## Query API

### `get_universe(date, universe_name="NIFTY500") -> HistoricalUniverse`

Return the exact set of constituents that existed on `date`.

```python
universe = ptue.get_universe("2022-06-15", "NIFTY500")
print(universe.symbols)           # ["RELIANCE", "TCS", ...]
print(universe.effective_count)   # 492
print(universe.is_fallback)       # False (history file used)
print(universe.coverage)          # 1.0
print(universe.source)            # "HISTORY_FILE"
```

**Raises:**
- `InvalidDateError` — if `date` is not YYYY-MM-DD
- `UniverseNotFoundError` — if no history and `fallback_enabled=False`

---

### `contains(symbol, date, universe_name="NIFTY500") -> bool`

Return True if `symbol` was a constituent on `date`.

```python
ptue.contains("RELIANCE", "2022-06-15", "NIFTY500")   # True
ptue.contains("SUZLON",   "2019-01-01", "NIFTY500")   # depends on history
```

Never raises. Returns `False` on any error or missing universe.

---

### `history(symbol) -> List[Constituent]`

Return all membership records for `symbol` across all loaded universes,
sorted by `effective_from`.

```python
records = ptue.history("SUZLON")
for r in records:
    print(r.symbol, r.effective_from, r.effective_to, r.reason)
```

---

### `coverage() -> CoverageReport`

Return coverage across all universes that have been loaded in this session.

```python
report = ptue.coverage()
print(report.total_universes)                       # 3
print(report.history_file_universes)                # ["NIFTY500", "NIFTY50"]
print(report.fallback_universes)                    # ["NIFTY100"]
print(report.coverage_by_universe["NIFTY500"])      # 1.0
print(report.coverage_by_universe["NIFTY100"])      # 0.5
```

---

### `statistics(universe_name) -> UniverseStatistics`

Return aggregate statistics for one universe.

```python
stats = ptue.statistics("NIFTY500")
print(stats.total_records)       # all constituent records
print(stats.active_count)        # active as of today
print(stats.additions_tracked)   # records with reason=ADDED
print(stats.removals_tracked)    # records with reason=REMOVED
print(stats.history_span_days)   # earliest to latest effective_from
print(stats.earliest_date)       # "2020-01-01"
```

---

### `loaded_universes() -> List[str]`

Names of all universes loaded in this session.

---

### `version(universe_name) -> UniverseVersion | None`

Metadata about how a universe was loaded.

```python
ver = ptue.version("NIFTY500")
print(ver.source)             # "HISTORY_FILE"
print(ver.constituent_count)  # 230
print(ver.history_file)       # absolute path
```

---

## Maintenance API

### `bootstrap_from_static(universe_name, effective_from, sub_index_filter) -> Path`

Create a `history.json` from the static fallback file.
Run once to seed a new universe.

```python
ptue.bootstrap_from_static(
    universe_name="NIFTY500",
    effective_from="2020-01-01",
)
# Creates: data/ars/ptue/NIFTY500/history.json
```

---

### `add_constituent(universe_name, symbol, effective_from, effective_to, reason)`

Append a new constituent record (e.g. when a stock is added to an index).

```python
ptue.add_constituent("NIFTY500", "NEWSTOCK", "2026-09-01", reason="ADDED")
```

---

### `remove_constituent(universe_name, symbol, effective_to, reason) -> bool`

Mark the most recent open-ended record for a symbol as ended.
Returns `True` if a record was updated.

```python
removed = ptue.remove_constituent("NIFTY500", "OLDSTOCK", "2026-08-31", reason="REMOVED")
```

---

### `invalidate_cache(universe_name=None)`

Clear cached HistoricalUniverse objects.

```python
ptue.invalidate_cache("NIFTY500")   # clear one universe
ptue.invalidate_cache()              # clear all
```

---

### `reload(universe_name)`

Force-reload a universe from disk (and clear its cache).

```python
ptue.reload("NIFTY500")
```

---

## Output Models

### `HistoricalUniverse`

| Field | Type | Description |
|---|---|---|
| `universe_name` | str | e.g. "NIFTY500" |
| `date` | str | The queried point-in-time date |
| `symbols` | List[str] | Symbols active on this date |
| `constituents` | List[Constituent] | Full records with dates and reasons |
| `source` | str | "HISTORY_FILE" / "STATIC_FALLBACK" / "EMPTY" |
| `coverage` | float | 1.0=full history, 0.5=fallback, 0.0=empty |
| `is_fallback` | bool | True if static fallback was used |
| `missing_symbols` | List[str] | Always empty (reserved for future gap tracking) |
| `effective_count` | int | len(symbols) |
| `generated_at` | str | ISO-8601 |

---

### `Constituent`

| Field | Type | Description |
|---|---|---|
| `symbol` | str | Ticker |
| `effective_from` | str | ISO date first day in universe |
| `effective_to` | str or None | ISO date last day, or None (still active) |
| `reason` | str or None | "INITIAL" / "ADDED" / "REMOVED" / custom |

**Method:** `is_active_on(date: str) -> bool`

---

### `UniverseStatistics`

| Field | Type | Description |
|---|---|---|
| `universe_name` | str | |
| `total_records` | int | All constituent records |
| `active_count` | int | Active as of today |
| `additions_tracked` | int | reason=ADDED |
| `removals_tracked` | int | reason=REMOVED |
| `history_span_days` | int | earliest to latest |
| `earliest_date` | str | |
| `latest_date` | str | |
| `source` | str | |

---

### `CoverageReport`

| Field | Type | Description |
|---|---|---|
| `universes` | List[str] | All loaded universe names |
| `total_universes` | int | |
| `coverage_by_universe` | Dict[str, float] | Coverage per universe |
| `fallback_universes` | List[str] | Names using fallback |
| `history_file_universes` | List[str] | Names with history files |
| `generated_at` | str | |

---

## PTUEConfig

| Field | Default | Description |
|---|---|---|
| `history_root` | `"data/ars/ptue"` | Root for `{name}/history.json` files |
| `static_fallback_path` | `"data/nifty500_universe.json"` | Static fallback file |
| `fallback_enabled` | `True` | Allow static fallback |
| `log_every_fallback` | `True` | Log `[PTUEFallback]` on each fallback query |
| `cache_enabled` | `True` | Cache resolved universes |
| `dry_run` | `False` | Disable all disk writes |

---

## Error Reference

| Exception | When |
|---|---|
| `PTUEError` | Base PTUE error |
| `UniverseNotFoundError` | No history and fallback disabled. Has `.universe_name`, `.date` |
| `InvalidDateError` | Bad date format. Has `.date_str` |

---

## Source Constants

| Constant | Value | Meaning |
|---|---|---|
| `SOURCE_HISTORY_FILE` | `"HISTORY_FILE"` | Loaded from versioned file |
| `SOURCE_STATIC_FALLBACK` | `"STATIC_FALLBACK"` | From current nifty500_universe.json |
| `SOURCE_EMPTY` | `"EMPTY"` | No data available |

---

## Universe Name Constants

| Constant | Value |
|---|---|
| `UNIVERSE_NIFTY500` | `"NIFTY500"` |
| `UNIVERSE_NIFTY100` | `"NIFTY100"` |
| `UNIVERSE_NIFTY50` | `"NIFTY50"` |
