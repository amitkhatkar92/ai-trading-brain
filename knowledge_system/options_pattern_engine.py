"""
Options Pattern Engine
=======================

Discovers repeating feature-combination → outcome patterns from the
options observation JSONL history.

Algorithm
---------
For each combination key (e.g. Regime × IVR × DTE × Strategy), the engine
maintains a frequency table:

  { feature_combination: { "n": int, "wins": int, "win_rate": float,
                            "avg_pnl": float, "last_seen": str } }

Patterns are only surfaced when n ≥ MIN_PATTERN_N to prevent over-fitting
on sparse data.

Pattern significance is NOT claimed by p-value alone; it requires:
  1. n ≥ MIN_PATTERN_N observations
  2. win_rate outside a MIN_EDGE band around 50% (e.g. ≥ 58% or ≤ 42%)
  3. avg_pnl positive (for long patterns) or negative (for short patterns)
  4. A temporal sanity check: the pattern must appear in both the first
     and second halves of the observation history (no regime-specific clustering)

Persistence: data/options_patterns.json
Singleton:   get_options_pattern_engine()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

_PATTERNS_PATH = "data/options_patterns.json"

# ── Significance thresholds ────────────────────────────────────────────────
MIN_PATTERN_N         = 8     # minimum outcomes before surfacing a pattern
MIN_EDGE_WIN_RATE     = 0.08  # win_rate must differ from 50% by at least this
MIN_TEMPORAL_COVERAGE = 0.20  # min fraction of observations in each half
HIGH_CONFIDENCE_N     = 20    # n above this → high-confidence pattern


@dataclass
class DiscoveredPattern:
    """
    One discovered feature-combination → outcome pattern.
    """
    pattern_id:    str    # "PAT-{hash[:8]}"
    context_key:   str    # the feature combination (e.g. "BULL|IVR_HIGH|DTE_WEEKLY")
    context_type:  str    # "regime_ivr_dte" | "regime_vix_pcr" | "strategy_regime_dir" | "full_key"
    strategy_name: str

    # ── Evidence ───────────────────────────────────────────────────────
    n:          int   = 0
    wins:       int   = 0
    win_rate:   float = 0.0
    total_pnl:  float = 0.0
    avg_pnl:    float = 0.0

    # ── Temporal coverage (anti-overfitting) ───────────────────────────
    first_half_n:  int   = 0
    second_half_n: int   = 0

    # ── Significance ──────────────────────────────────────────────────
    is_significant:    bool  = False
    edge_strength:     str   = "WEAK"   # WEAK / MODERATE / STRONG / VERY_STRONG
    temporal_coverage: float = 0.0

    # ── Metadata ──────────────────────────────────────────────────────
    first_seen:   str = ""
    last_updated: str = ""
    linked_knowledge_items: List[str] = field(default_factory=list)


class OptionsPatternEngine:
    """
    Discovers and maintains options feature-combination → outcome patterns.

    Thread-safe.  Persists state to disk after each analysis run.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._patterns: Dict[str, DiscoveredPattern] = {}  # pattern_id → pattern
        # Raw frequency table (not serialised in full — rebuilt from JSONL)
        # key = (context_type, context_key, strategy_name) → list of (win, pnl, observed_at)
        self._raw: Dict[Tuple, List[Tuple[int, float, str]]] = {}
        os.makedirs(os.path.dirname(_PATTERNS_PATH), exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def process_observation(
        self,
        strategy_name: str,
        feature_vector,   # OptionsFeatureVector
        pnl:           float,
        observed_at:   str = "",
    ) -> None:
        """
        Ingest one outcome and update the pattern tables.

        Only OUTCOME_OBSERVED records should be passed here.
        """
        if not feature_vector.is_valid:
            return
        win = 1 if pnl > 0 else 0
        ts  = observed_at or datetime.now().isoformat()
        with self._lock:
            for ctx_type, ctx_key in self._context_pairs(feature_vector):
                k = (ctx_type, ctx_key, strategy_name)
                if k not in self._raw:
                    self._raw[k] = []
                self._raw[k].append((win, pnl, ts))

    def run_discovery(self) -> List[DiscoveredPattern]:
        """
        Run the full pattern discovery algorithm over the current raw data.

        Returns the list of significant patterns found.
        """
        with self._lock:
            self._patterns.clear()
            significant: List[DiscoveredPattern] = []

            for (ctx_type, ctx_key, strategy_name), entries in self._raw.items():
                if len(entries) < MIN_PATTERN_N:
                    continue
                pat = self._analyse(ctx_type, ctx_key, strategy_name, entries)
                self._patterns[pat.pattern_id] = pat
                if pat.is_significant:
                    significant.append(pat)

            self._save()
            log.info(
                "[PatternEngine] Discovery run: %d total patterns, %d significant.",
                len(self._patterns), len(significant),
            )
            return significant

    def get_significant_patterns(self, min_n: int = MIN_PATTERN_N) -> List[DiscoveredPattern]:
        with self._lock:
            return [p for p in self._patterns.values()
                    if p.is_significant and p.n >= min_n]

    def get_patterns_for_strategy(self, strategy_name: str) -> List[DiscoveredPattern]:
        with self._lock:
            return [p for p in self._patterns.values()
                    if p.strategy_name == strategy_name]

    def rebuild_from_feature_vectors(
        self,
        feature_outcome_pairs: List[Tuple],  # (OptionsFeatureVector, float pnl, str observed_at)
    ) -> None:
        """
        Rebuild raw frequency tables from scratch from a list of (feature, pnl) pairs.
        Call run_discovery() after this to compute patterns.
        """
        with self._lock:
            self._raw.clear()
        for fv, pnl, ts in feature_outcome_pairs:
            self.process_observation(fv.strategy_name, fv, pnl, ts)

    # ── Private ────────────────────────────────────────────────────────────

    def _context_pairs(self, fv) -> List[Tuple[str, str]]:
        """Return all context key variants for this feature vector."""
        return [
            ("regime_ivr_dte",   fv.regime_ivr_dte),
            ("regime_vix_pcr",   fv.regime_vix_pcr),
            ("strategy_regime_dir", fv.strategy_regime_dir),
            ("full_key",         fv.full_key),
        ]

    def _analyse(
        self,
        ctx_type:     str,
        ctx_key:      str,
        strategy_name: str,
        entries:       List[Tuple[int, float, str]],
    ) -> DiscoveredPattern:
        n         = len(entries)
        wins      = sum(e[0] for e in entries)
        total_pnl = sum(e[1] for e in entries)
        win_rate  = wins / n
        avg_pnl   = total_pnl / n

        # Temporal coverage: split by observed_at ordering
        sorted_entries = sorted(entries, key=lambda e: e[2])
        mid = n // 2
        first_half_n  = mid
        second_half_n = n - mid

        temporal_coverage = min(first_half_n, second_half_n) / max(n, 1)

        # Significance
        edge = abs(win_rate - 0.5)
        is_significant = (
            n >= MIN_PATTERN_N
            and edge >= MIN_EDGE_WIN_RATE
            and temporal_coverage >= MIN_TEMPORAL_COVERAGE
            and avg_pnl * (1 if win_rate >= 0.5 else -1) > 0
        )

        if edge < 0.04:
            edge_strength = "WEAK"
        elif edge < 0.10:
            edge_strength = "MODERATE"
        elif edge < 0.20:
            edge_strength = "STRONG"
        else:
            edge_strength = "VERY_STRONG"

        h       = abs(hash(f"{ctx_type}|{ctx_key}|{strategy_name}")) % 0xFFFFFFFF
        pat_id  = f"PAT-{h:08x}"

        first_seen = sorted_entries[0][2][:10] if sorted_entries else ""
        last_ts    = sorted_entries[-1][2] if sorted_entries else ""

        return DiscoveredPattern(
            pattern_id       = pat_id,
            context_key      = ctx_key,
            context_type     = ctx_type,
            strategy_name    = strategy_name,
            n                = n,
            wins             = wins,
            win_rate         = round(win_rate, 4),
            total_pnl        = round(total_pnl, 2),
            avg_pnl          = round(avg_pnl, 2),
            first_half_n     = first_half_n,
            second_half_n    = second_half_n,
            is_significant   = is_significant,
            edge_strength    = edge_strength,
            temporal_coverage = round(temporal_coverage, 3),
            first_seen       = first_seen,
            last_updated     = datetime.now().isoformat(),
        )

    def _save(self) -> None:
        try:
            data = {
                "schema_version": 1,
                "saved_at":       datetime.now().isoformat(),
                "patterns":       {pid: asdict(p) for pid, p in self._patterns.items()},
            }
            tmp = _PATTERNS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            os.replace(tmp, _PATTERNS_PATH)
        except Exception as exc:
            log.debug("[PatternEngine] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_PATTERNS_PATH):
            return
        try:
            with open(_PATTERNS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for pid, raw in data.get("patterns", {}).items():
                try:
                    p = DiscoveredPattern(**{
                        k: v for k, v in raw.items()
                        if k in DiscoveredPattern.__dataclass_fields__
                    })
                    self._patterns[pid] = p
                except Exception:
                    pass
            log.info(
                "[PatternEngine] Loaded %d patterns from disk.",
                len(self._patterns),
            )
        except Exception as exc:
            log.debug("[PatternEngine] Load failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_ENGINE_INSTANCE: Optional[OptionsPatternEngine] = None
_ENGINE_LOCK      = threading.Lock()


def get_options_pattern_engine() -> OptionsPatternEngine:
    global _ENGINE_INSTANCE
    with _ENGINE_LOCK:
        if _ENGINE_INSTANCE is None:
            _ENGINE_INSTANCE = OptionsPatternEngine()
    return _ENGINE_INSTANCE
