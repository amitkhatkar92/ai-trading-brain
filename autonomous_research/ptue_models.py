"""
ptue_models.py — Point-in-Time Universe Engine data models.

IIOS Research Infrastructure — R-006.

Every historical lookup returns a HistoricalUniverse that documents exactly
which symbols existed on the queried date, the source of that information,
and whether a fallback was used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ─── Constituent ─────────────────────────────────────────────────────────────

@dataclass
class Constituent:
    """One membership record in a universe constituent history.

    A constituent is active on any date D where::

        effective_from <= D <= effective_to   (or effective_to is None = still active)
    """
    symbol:         str
    effective_from: str            # ISO date "YYYY-MM-DD"
    effective_to:   Optional[str]  # ISO date or None (still active)
    reason:         Optional[str]  # "INITIAL" | "ADDED" | "REMOVED" | custom

    def is_active_on(self, date_str: str) -> bool:
        """Return True if this constituent was active on *date_str*."""
        return (
            self.effective_from <= date_str
            and (self.effective_to is None or self.effective_to >= date_str)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":         self.symbol,
            "effective_from": self.effective_from,
            "effective_to":   self.effective_to,
            "reason":         self.reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Constituent":
        return cls(
            symbol=d["symbol"],
            effective_from=d.get("effective_from", "2000-01-01"),
            effective_to=d.get("effective_to"),
            reason=d.get("reason"),
        )


# ─── UniverseVersion ─────────────────────────────────────────────────────────

@dataclass
class UniverseVersion:
    """Metadata about a loaded universe constituent history."""
    universe_name:     str
    version:           str             # e.g. "1.0"
    loaded_at:         str             # ISO-8601
    source:            str             # "HISTORY_FILE" | "STATIC_FALLBACK" | "EMPTY"
    constituent_count: int             # total records (not just active today)
    history_file:      Optional[str]   # absolute path if loaded from file

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universe_name":     self.universe_name,
            "version":           self.version,
            "loaded_at":         self.loaded_at,
            "source":            self.source,
            "constituent_count": self.constituent_count,
            "history_file":      self.history_file,
        }


# ─── HistoricalUniverse ───────────────────────────────────────────────────────

@dataclass
class HistoricalUniverse:
    """The exact market universe that existed on a specific historical date.

    This is the primary output of the Point-in-Time Universe Engine.
    """
    universe_name:   str
    date:            str            # the queried point-in-time date "YYYY-MM-DD"
    symbols:         List[str]      # symbols active on this date
    constituents:    List[Constituent]  # full records (symbol + dates + reason)
    source:          str            # "HISTORY_FILE" | "STATIC_FALLBACK" | "EMPTY"
    coverage:        float          # 0.0-1.0  (1.0 = complete historical data)
    is_fallback:     bool           # True if static fallback was used
    missing_symbols: List[str]      # symbols expected but not in history
    effective_count: int            # len(symbols)
    generated_at:    str            # ISO-8601 when this object was built

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universe_name":   self.universe_name,
            "date":            self.date,
            "symbols":         self.symbols,
            "constituents":    [c.to_dict() for c in self.constituents],
            "source":          self.source,
            "coverage":        round(self.coverage, 4),
            "is_fallback":     self.is_fallback,
            "missing_symbols": self.missing_symbols,
            "effective_count": self.effective_count,
            "generated_at":    self.generated_at,
        }


# ─── UniverseStatistics ──────────────────────────────────────────────────────

@dataclass
class UniverseStatistics:
    """Aggregate statistics about the history of a single universe."""
    universe_name:        str
    total_records:        int      # all constituent records (active + removed)
    active_count:         int      # active as of today
    additions_tracked:    int      # records with reason=ADDED
    removals_tracked:     int      # records with reason=REMOVED
    history_span_days:    int      # earliest to latest effective_from
    earliest_date:        Optional[str]
    latest_date:          Optional[str]
    source:               str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universe_name":     self.universe_name,
            "total_records":     self.total_records,
            "active_count":      self.active_count,
            "additions_tracked": self.additions_tracked,
            "removals_tracked":  self.removals_tracked,
            "history_span_days": self.history_span_days,
            "earliest_date":     self.earliest_date,
            "latest_date":       self.latest_date,
            "source":            self.source,
        }


# ─── CoverageReport ──────────────────────────────────────────────────────────

@dataclass
class CoverageReport:
    """Coverage assessment across all loaded universe histories."""
    universes:            List[str]
    total_universes:      int
    coverage_by_universe: Dict[str, float]   # universe_name -> coverage 0.0-1.0
    fallback_universes:   List[str]          # universes using static fallback
    history_file_universes: List[str]        # universes with history files
    generated_at:         str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universes":              self.universes,
            "total_universes":        self.total_universes,
            "coverage_by_universe":   self.coverage_by_universe,
            "fallback_universes":     self.fallback_universes,
            "history_file_universes": self.history_file_universes,
            "generated_at":           self.generated_at,
        }


# ─── Errors ───────────────────────────────────────────────────────────────────

class PTUEError(Exception):
    """Base PTUE error."""


class UniverseNotFoundError(PTUEError):
    """Raised when the requested universe has no history and fallback is disabled."""

    def __init__(self, universe_name: str, date: str) -> None:
        self.universe_name = universe_name
        self.date          = date
        super().__init__(f"No universe data for '{universe_name}' on {date}")


class InvalidDateError(PTUEError):
    """Raised when the provided date string is not a valid ISO date."""

    def __init__(self, date_str: str) -> None:
        self.date_str = date_str
        super().__init__(f"Invalid date: '{date_str}' — expected YYYY-MM-DD")


# ─── Known universe names ─────────────────────────────────────────────────────

UNIVERSE_NIFTY500 = "NIFTY500"
UNIVERSE_NIFTY100 = "NIFTY100"
UNIVERSE_NIFTY50  = "NIFTY50"
KNOWN_UNIVERSES   = (UNIVERSE_NIFTY500, UNIVERSE_NIFTY100, UNIVERSE_NIFTY50)

# Coverage assigned to each source type
SOURCE_HISTORY_FILE     = "HISTORY_FILE"
SOURCE_STATIC_FALLBACK  = "STATIC_FALLBACK"
SOURCE_EMPTY            = "EMPTY"

_COVERAGE_HISTORY_FILE    = 1.0
_COVERAGE_STATIC_FALLBACK = 0.5
_COVERAGE_EMPTY           = 0.0
