"""
ptue.py — Point-in-Time Universe Engine.

IIOS Research Infrastructure — R-006.

The PTUE is the authoritative provider of historical market universes.
No replay logic shall determine historical constituents itself.

The engine is read-only and thread-safe.  Every fallback is logged.

Usage
-----
    from autonomous_research import PointInTimeUniverseEngine, PTUEConfig

    ptue = PointInTimeUniverseEngine(config=PTUEConfig())

    universe = ptue.get_universe("2022-06-15", "NIFTY500")
    print(universe.symbols)           # exactly those active on 2022-06-15
    print(universe.effective_count)   # e.g. 492
    print(universe.is_fallback)       # False if history file was used

    present = ptue.contains("RELIANCE", "2022-06-15", "NIFTY500")  # True/False

    sym_hist = ptue.history("SUZLON")   # all membership records for SUZLON
    cov = ptue.coverage()               # CoverageReport across all universes
    stats = ptue.statistics("NIFTY500") # UniverseStatistics
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, date as _date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ptue_config import PTUEConfig
from .ptue_models import (
    _COVERAGE_EMPTY,
    _COVERAGE_HISTORY_FILE,
    _COVERAGE_STATIC_FALLBACK,
    SOURCE_EMPTY,
    SOURCE_HISTORY_FILE,
    SOURCE_STATIC_FALLBACK,
    Constituent,
    CoverageReport,
    HistoricalUniverse,
    InvalidDateError,
    PTUEError,
    UniverseNotFoundError,
    UniverseStatistics,
    UniverseVersion,
    _now_iso,
)

log = logging.getLogger(__name__)

_TODAY = datetime.utcnow().strftime("%Y-%m-%d")


def _validate_date(date_str: str) -> str:
    """Validate and normalise to YYYY-MM-DD.  Raises InvalidDateError if bad."""
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return d.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        raise InvalidDateError(date_str)


class PointInTimeUniverseEngine:
    """Authoritative provider of historical market universes.

    Thread-safe.  All public methods acquire a shared lock.
    History data is loaded lazily per universe on first request.

    Parameters
    ----------
    config : PTUEConfig | None
        Configuration; uses defaults if None.
    """

    def __init__(self, config: Optional[PTUEConfig] = None) -> None:
        self._config = config or PTUEConfig()
        self._lock   = threading.RLock()

        # universe_name -> list of Constituent (full history)
        self._history: Dict[str, List[Constituent]] = {}

        # universe_name -> UniverseVersion (metadata)
        self._versions: Dict[str, UniverseVersion] = {}

        # cache: (date, universe_name) -> HistoricalUniverse
        self._cache: Dict[Tuple[str, str], HistoricalUniverse] = {}

        log.info(
            "[PTUE] Initialised. history_root=%s fallback=%s cache=%s dry_run=%s",
            self._config.history_root,
            self._config.fallback_enabled,
            self._config.cache_enabled,
            self._config.dry_run,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Primary query API
    # ═══════════════════════════════════════════════════════════════════════

    def get_universe(
        self,
        date:          str,
        universe_name: str = "NIFTY500",
    ) -> HistoricalUniverse:
        """Return the exact set of constituents that existed on *date*.

        Parameters
        ----------
        date : str
            Point-in-time date "YYYY-MM-DD".
        universe_name : str
            One of: "NIFTY500", "NIFTY100", "NIFTY50", or a custom name.

        Returns
        -------
        HistoricalUniverse
            Contains the constituent list, source, coverage, and is_fallback flag.

        Raises
        ------
        InvalidDateError
            If *date* is not a valid ISO date.
        UniverseNotFoundError
            If no history and fallback is disabled.
        """
        date = _validate_date(date)
        cache_key = (date, universe_name)

        with self._lock:
            if self._config.cache_enabled and cache_key in self._cache:
                return self._cache[cache_key]

            self._ensure_loaded(universe_name)

            records = self._history.get(universe_name, [])
            version = self._versions.get(universe_name)
            source  = version.source if version else SOURCE_EMPTY

            if not records and source == SOURCE_EMPTY:
                raise UniverseNotFoundError(universe_name, date)

            active = [c for c in records if c.is_active_on(date)]

            if source == SOURCE_HISTORY_FILE:
                coverage = _COVERAGE_HISTORY_FILE
            elif source == SOURCE_STATIC_FALLBACK:
                coverage = _COVERAGE_STATIC_FALLBACK
            else:
                coverage = _COVERAGE_EMPTY

            is_fallback = (source == SOURCE_STATIC_FALLBACK)

            universe = HistoricalUniverse(
                universe_name=universe_name,
                date=date,
                symbols=[c.symbol for c in active],
                constituents=active,
                source=source,
                coverage=coverage,
                is_fallback=is_fallback,
                missing_symbols=[],
                effective_count=len(active),
                generated_at=_now_iso(),
            )

            if self._config.cache_enabled:
                self._cache[cache_key] = universe

            return universe

    def contains(
        self,
        symbol:        str,
        date:          str,
        universe_name: str = "NIFTY500",
    ) -> bool:
        """Return True if *symbol* was a constituent on *date*.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. "RELIANCE").
        date : str
            Point-in-time date "YYYY-MM-DD".
        universe_name : str
            Universe to query.

        Returns
        -------
        bool
        """
        try:
            universe = self.get_universe(date, universe_name)
            return symbol.upper() in {s.upper() for s in universe.symbols}
        except (UniverseNotFoundError, InvalidDateError):
            return False

    def history(self, symbol: str) -> List[Constituent]:
        """Return all membership records for *symbol* across all loaded universes.

        Parameters
        ----------
        symbol : str
            Ticker symbol.

        Returns
        -------
        List[Constituent]
            All constituent records for this symbol (may span multiple universes).
        """
        sym_upper = symbol.upper()
        results: List[Constituent] = []
        with self._lock:
            for records in self._history.values():
                for c in records:
                    if c.symbol.upper() == sym_upper:
                        results.append(c)
        return sorted(results, key=lambda c: c.effective_from)

    def coverage(self) -> CoverageReport:
        """Return a coverage report across all loaded universe histories.

        Returns
        -------
        CoverageReport
        """
        with self._lock:
            names      = sorted(self._versions.keys())
            by_universe: Dict[str, float] = {}
            fallbacks:   List[str]        = []
            history_files: List[str]      = []

            for name in names:
                ver = self._versions[name]
                if ver.source == SOURCE_HISTORY_FILE:
                    by_universe[name] = _COVERAGE_HISTORY_FILE
                    history_files.append(name)
                elif ver.source == SOURCE_STATIC_FALLBACK:
                    by_universe[name] = _COVERAGE_STATIC_FALLBACK
                    fallbacks.append(name)
                else:
                    by_universe[name] = _COVERAGE_EMPTY

        return CoverageReport(
            universes=names,
            total_universes=len(names),
            coverage_by_universe=by_universe,
            fallback_universes=fallbacks,
            history_file_universes=history_files,
            generated_at=_now_iso(),
        )

    def statistics(self, universe_name: str) -> UniverseStatistics:
        """Return aggregate statistics for a single universe.

        Parameters
        ----------
        universe_name : str

        Returns
        -------
        UniverseStatistics
        """
        with self._lock:
            self._ensure_loaded(universe_name)
            records = self._history.get(universe_name, [])
            version = self._versions.get(universe_name)
            source  = version.source if version else SOURCE_EMPTY

        today     = _TODAY
        active    = [c for c in records if c.is_active_on(today)]
        additions = [c for c in records if c.reason == "ADDED"]
        removals  = [c for c in records if c.reason == "REMOVED"]

        dates = [c.effective_from for c in records if c.effective_from]
        earliest = min(dates) if dates else None
        latest   = max(dates) if dates else None
        span     = 0
        if earliest and latest:
            try:
                span = (
                    datetime.strptime(latest, "%Y-%m-%d")
                    - datetime.strptime(earliest, "%Y-%m-%d")
                ).days
            except ValueError:
                span = 0

        return UniverseStatistics(
            universe_name=universe_name,
            total_records=len(records),
            active_count=len(active),
            additions_tracked=len(additions),
            removals_tracked=len(removals),
            history_span_days=span,
            earliest_date=earliest,
            latest_date=latest,
            source=source,
        )

    def loaded_universes(self) -> List[str]:
        """Return the names of all universes that have been loaded."""
        with self._lock:
            return sorted(self._versions.keys())

    def version(self, universe_name: str) -> Optional[UniverseVersion]:
        """Return the UniverseVersion metadata for a loaded universe."""
        with self._lock:
            return self._versions.get(universe_name)

    def invalidate_cache(self, universe_name: Optional[str] = None) -> None:
        """Clear the query cache.

        Parameters
        ----------
        universe_name : str | None
            If given, only clear cache entries for that universe.
            If None, clear all cached entries.
        """
        with self._lock:
            if universe_name is None:
                self._cache.clear()
            else:
                to_del = [k for k in self._cache if k[1] == universe_name]
                for k in to_del:
                    del self._cache[k]

    def reload(self, universe_name: str) -> None:
        """Force-reload a universe from disk (clears cached version too)."""
        with self._lock:
            self._history.pop(universe_name, None)
            self._versions.pop(universe_name, None)
            self.invalidate_cache(universe_name)
            self._ensure_loaded(universe_name)

    # ═══════════════════════════════════════════════════════════════════════
    # Bootstrap helper
    # ═══════════════════════════════════════════════════════════════════════

    def bootstrap_from_static(
        self,
        universe_name:   str = "NIFTY500",
        effective_from:  str = "2020-01-01",
        sub_index_filter: Optional[str] = None,
    ) -> Path:
        """Create a history.json for *universe_name* from the static fallback file.

        Writes to ``{history_root}/{universe_name}/history.json``.
        Skips write if dry_run=True.

        Parameters
        ----------
        universe_name : str
            Target universe name ("NIFTY500", "NIFTY100", "NIFTY50", etc.)
        effective_from : str
            ISO date to assign as effective_from for all bootstrapped records.
        sub_index_filter : str | None
            If set, only symbols whose ``index`` field matches this value are
            included.  E.g. "NIFTY50" to bootstrap only the 50-stock sub-index.

        Returns
        -------
        Path
            Path of the written (or would-be written) history file.
        """
        static_path = Path(self._config.static_fallback_path)
        out_path    = Path(self._config.history_root) / universe_name / "history.json"

        symbols = self._load_static_file()
        if sub_index_filter:
            # Match index field if present; keep all when field is absent
            symbols = [
                s for s in symbols
                if s.get("index", "") == sub_index_filter
                   or s.get("index", "") == ""
            ]
            # If filter produced nothing, keep all (lenient)
            if not symbols:
                symbols = self._load_static_file()

        constituents = [
            {"symbol": s["symbol"], "effective_from": effective_from,
             "effective_to": None, "reason": "INITIAL"}
            for s in symbols
        ]
        payload = {
            "universe":    universe_name,
            "version":     "1.0",
            "description": f"Bootstrapped from static universe on {_TODAY}",
            "last_updated": _TODAY,
            "constituents": constituents,
        }

        if not self._config.dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            log.info("[PTUE] Bootstrap written: %s (%d symbols)", out_path, len(constituents))

            with self._lock:
                # Invalidate so next query reloads from the new file
                self._history.pop(universe_name, None)
                self._versions.pop(universe_name, None)
                self.invalidate_cache(universe_name)

        return out_path

    def add_constituent(
        self,
        universe_name:  str,
        symbol:         str,
        effective_from: str,
        effective_to:   Optional[str] = None,
        reason:         str = "ADDED",
    ) -> None:
        """Append a new constituent record to an in-memory history and persist.

        Caller is responsible for ensuring no duplicate overlapping records.

        Parameters
        ----------
        universe_name : str
        symbol : str
        effective_from : str
        effective_to : str | None
        reason : str
        """
        effective_from = _validate_date(effective_from)
        if effective_to:
            effective_to = _validate_date(effective_to)

        new_record = Constituent(
            symbol=symbol.upper(),
            effective_from=effective_from,
            effective_to=effective_to,
            reason=reason,
        )

        with self._lock:
            self._ensure_loaded(universe_name)
            if universe_name not in self._history:
                self._history[universe_name] = []
            self._history[universe_name].append(new_record)
            self.invalidate_cache(universe_name)

            if not self._config.dry_run:
                self._persist_history(universe_name)

    def remove_constituent(
        self,
        universe_name: str,
        symbol:        str,
        effective_to:  str,
        reason:        str = "REMOVED",
    ) -> bool:
        """Mark the most recent open-ended record for *symbol* as ended on *effective_to*.

        Returns True if a record was updated, False if no active record was found.
        """
        effective_to = _validate_date(effective_to)
        sym_upper    = symbol.upper()

        with self._lock:
            self._ensure_loaded(universe_name)
            records = self._history.get(universe_name, [])
            updated = False
            for c in reversed(records):
                if c.symbol.upper() == sym_upper and c.effective_to is None:
                    c.effective_to = effective_to
                    c.reason       = reason
                    updated        = True
                    break

            if updated:
                self.invalidate_cache(universe_name)
                if not self._config.dry_run:
                    self._persist_history(universe_name)

        return updated

    # ═══════════════════════════════════════════════════════════════════════
    # Internal loading
    # ═══════════════════════════════════════════════════════════════════════

    def _ensure_loaded(self, universe_name: str) -> None:
        """Load universe history if not already in memory.  Caller holds lock."""
        if universe_name in self._history:
            return

        loaded = self._try_load_history_file(universe_name)
        if not loaded:
            loaded = self._try_static_fallback(universe_name)
        if not loaded:
            # Mark as empty — no data, no fallback
            self._history[universe_name]  = []
            self._versions[universe_name] = UniverseVersion(
                universe_name=universe_name,
                version="0",
                loaded_at=_now_iso(),
                source=SOURCE_EMPTY,
                constituent_count=0,
                history_file=None,
            )

    def _try_load_history_file(self, universe_name: str) -> bool:
        """Attempt to load from {history_root}/{universe_name}/history.json."""
        hist_path = Path(self._config.history_root) / universe_name / "history.json"
        if not hist_path.exists():
            return False

        try:
            raw = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("[PTUE] Could not parse %s: %s", hist_path, exc)
            return False

        records_raw = raw.get("constituents", [])
        records = []
        for d in records_raw:
            try:
                records.append(Constituent.from_dict(d))
            except (KeyError, TypeError, ValueError) as exc:
                log.debug("[PTUE] Skipping bad record in %s: %s", hist_path, exc)

        version_str = str(raw.get("version", "1.0"))
        self._history[universe_name]  = records
        self._versions[universe_name] = UniverseVersion(
            universe_name=universe_name,
            version=version_str,
            loaded_at=_now_iso(),
            source=SOURCE_HISTORY_FILE,
            constituent_count=len(records),
            history_file=str(hist_path.resolve()),
        )
        log.info(
            "[PTUE] Loaded history for %s: %d records from %s",
            universe_name, len(records), hist_path,
        )
        return True

    def _try_static_fallback(self, universe_name: str) -> bool:
        """Fall back to the static nifty500_universe.json if allowed."""
        if not self._config.fallback_enabled:
            return False

        symbols = self._load_static_file()
        if not symbols:
            return False

        # For sub-indices we only use NIFTY50 index-tagged symbols
        if universe_name == "NIFTY50":
            sub = [s for s in symbols if s.get("index", "") == "NIFTY50"]
            if sub:
                symbols = sub

        records = [
            Constituent(
                symbol=s["symbol"].upper(),
                effective_from="2020-01-01",
                effective_to=None,
                reason="INITIAL",
            )
            for s in symbols
            if "symbol" in s
        ]

        self._history[universe_name]  = records
        self._versions[universe_name] = UniverseVersion(
            universe_name=universe_name,
            version="STATIC",
            loaded_at=_now_iso(),
            source=SOURCE_STATIC_FALLBACK,
            constituent_count=len(records),
            history_file=None,
        )

        if self._config.log_every_fallback:
            log.warning(
                "[PTUEFallback] No history file for universe '%s'. "
                "Falling back to static universe (%d symbols). "
                "Results may contain survivorship bias.",
                universe_name, len(records),
            )
        return True

    def _load_static_file(self) -> List[Dict[str, Any]]:
        """Load the static nifty500_universe.json.  Returns [] on failure."""
        static_path = Path(self._config.static_fallback_path)
        if not static_path.exists():
            log.debug("[PTUE] Static fallback file not found: %s", static_path)
            return []
        try:
            raw = json.loads(static_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
            return []
        except Exception as exc:
            log.warning("[PTUE] Could not load static fallback %s: %s", static_path, exc)
            return []

    def _persist_history(self, universe_name: str) -> None:
        """Write the in-memory history for *universe_name* back to disk."""
        out_path = Path(self._config.history_root) / universe_name / "history.json"
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            records   = self._history.get(universe_name, [])
            version   = self._versions.get(universe_name)
            payload   = {
                "universe":    universe_name,
                "version":     version.version if version else "1.0",
                "description": f"PTUE managed history for {universe_name}",
                "last_updated": _TODAY,
                "constituents": [c.to_dict() for c in records],
            }
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("[PTUE] Persist failed for %s: %s", universe_name, exc)
