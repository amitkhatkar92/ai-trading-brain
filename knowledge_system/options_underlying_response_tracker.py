"""
Options Underlying Response Tracker
======================================
DTA-001 Phase 5: Underlying → Option Leverage Research

Tracks and analyzes the relationship between underlying moves and
corresponding option price movements.

Central research question:
    "Given an underlying move of X%, what did the corresponding option do?"

For every OUTCOME_OBSERVED record this tracker computes:
    underlying_return        = (underlying_exit - underlying_entry) / underlying_entry
    option_return            = (option_exit - option_entry) / option_entry
    option_underlying_ratio  = option_return / underlying_return (if non-zero)
    option_absolute_move     = option_exit - option_entry
    underlying_absolute_move = underlying_exit - underlying_entry

These are stored per observation and stratified by context:
    (strategy, regime, ivr_band, dte_band, moneyness, direction)

The tracker maintains a persistent response database and publishes
distributional statistics (mean, median, p25, p75, p90) per context.

Research findings eventually feed:
    1. OptionsMultiContractSelector — which contract historically captured moves best
    2. OptionsKnowledgeStore       — underlying→option response as a knowledge dimension
    3. OptionsHypothesisEngine     — auto-generates leverage hypothesis per context

Persistence: data/options_underlying_response.json (atomic write)

Singleton: get_options_underlying_response_tracker()
"""

from __future__ import annotations

import json
import os
import statistics
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_PERSIST_PATH = "data/options_underlying_response.json"
_INSTANCE: Optional["OptionsUnderlyingResponseTracker"] = None
_INSTANCE_LOCK = threading.Lock()

# Minimum observations before publishing a distribution
MIN_OBS_FOR_DISTRIBUTION = 5


@dataclass
class ResponseObservation:
    """One underlying→option response pair."""
    opportunity_id:            str
    symbol:                    str
    strategy_name:             str
    observed_at:               str
    direction:                 str          # BULLISH / BEARISH

    # Underlying
    underlying_entry:          float
    underlying_exit:           float
    underlying_absolute_move:  float        # exit - entry
    underlying_pct_move:       float        # (exit-entry)/entry * 100

    # Option
    option_entry_premium:      float
    option_exit_premium:       float
    option_absolute_move:      float        # exit_prem - entry_prem
    option_pct_move:           float        # (exit-entry)/entry * 100

    # Derived
    option_underlying_ratio:   Optional[float]  # option_pct / underlying_pct
    response_score:            float            # 0-10 scale (10=maximum leverage capture)

    # Context for stratification
    regime:                    str
    ivr_band:                  str
    dte_band:                  str
    moneyness:                 str          # ITM / ATM / OTM
    delta_at_entry:            float
    iv_at_entry:               float
    option_type:               str          # CE / PE
    time_of_day:               str
    iv_source:                 str

    # Outcome quality
    was_winner:                bool
    pnl_rs:                    float


@dataclass
class ResponseDistribution:
    """Statistical distribution of option responses for a given context."""
    context_key:       str
    n:                 int
    strategy_name:     str

    # Underlying stats (%)
    underlying_mean_pct:    float
    underlying_median_pct:  float
    underlying_p25_pct:     float
    underlying_p75_pct:     float

    # Option stats (%)
    option_mean_pct:        float
    option_median_pct:      float
    option_p25_pct:         float
    option_p75_pct:         float
    option_p90_pct:         float

    # Ratio stats (option % / underlying %)
    ratio_mean:             Optional[float]
    ratio_median:           Optional[float]
    ratio_p25:              Optional[float]
    ratio_p75:              Optional[float]
    ratio_p90:              Optional[float]

    # Efficiency: how often option return > underlying return (in abs %)
    outperform_rate:        float       # fraction of observations where |option%| > |underlying%|
    best_contract_score:    float       # aggregate leverage capture score

    last_updated:           str


def get_options_underlying_response_tracker() -> "OptionsUnderlyingResponseTracker":
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = OptionsUnderlyingResponseTracker()
    return _INSTANCE


class OptionsUnderlyingResponseTracker:
    """
    Tracks the relationship between underlying moves and option price movements.

    Thread-safe.  All writes are atomic (tempfile + os.replace).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._observations: List[ResponseObservation] = []
        self._distributions: Dict[str, ResponseDistribution] = {}
        os.makedirs("data", exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def record_response(
        self,
        opportunity_id:       str,
        symbol:               str,
        strategy_name:        str,
        direction:            str,
        underlying_entry:     float,
        underlying_exit:      float,
        option_entry_premium: float,
        option_exit_premium:  float,
        pnl_rs:               float,
        regime:               str = "",
        ivr_band:             str = "",
        dte_band:             str = "",
        moneyness:            str = "ATM",
        delta_at_entry:       float = 0.5,
        iv_at_entry:          float = 0.0,
        option_type:          str = "CE",
        time_of_day:          str = "NORMAL",
        iv_source:            str = "",
        observed_at:          Optional[str] = None,
    ) -> ResponseObservation:
        """
        Record one underlying → option response observation.

        All float arithmetic is guarded against zero-division.
        """
        now = observed_at or datetime.now().isoformat()

        # Compute moves
        u_abs = underlying_exit - underlying_entry
        u_pct = (u_abs / underlying_entry * 100.0) if underlying_entry != 0 else 0.0

        o_abs = option_exit_premium - option_entry_premium
        o_pct = (o_abs / option_entry_premium * 100.0) if option_entry_premium != 0 else 0.0

        ratio = (o_pct / u_pct) if (u_pct != 0.0 and abs(u_pct) > 0.01) else None

        # Response score: how well the option captured the move
        # 10 = option moved in correct direction with ratio ≥ 2
        # 5  = correct direction, ratio ≈ 1
        # 0  = option moved against underlying
        was_winner = pnl_rs > 0
        if was_winner and ratio is not None:
            score = min(10.0, max(0.0, ratio * 5.0))
        elif was_winner:
            score = 5.0
        else:
            score = 0.0

        obs = ResponseObservation(
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy_name=strategy_name,
            observed_at=now,
            direction=direction,
            underlying_entry=underlying_entry,
            underlying_exit=underlying_exit,
            underlying_absolute_move=u_abs,
            underlying_pct_move=u_pct,
            option_entry_premium=option_entry_premium,
            option_exit_premium=option_exit_premium,
            option_absolute_move=o_abs,
            option_pct_move=o_pct,
            option_underlying_ratio=ratio,
            response_score=score,
            regime=regime,
            ivr_band=ivr_band,
            dte_band=dte_band,
            moneyness=moneyness,
            delta_at_entry=delta_at_entry,
            iv_at_entry=iv_at_entry,
            option_type=option_type,
            time_of_day=time_of_day,
            iv_source=iv_source,
            was_winner=was_winner,
            pnl_rs=pnl_rs,
        )

        with self._lock:
            self._observations.append(obs)
            ctx_key = self._context_key(strategy_name, regime, ivr_band, dte_band)
            self._update_distribution(ctx_key, strategy_name)
            self._save_locked()

        log.debug(
            "[ResponseTracker] %s %s u_pct=%.2f%% o_pct=%.2f%% ratio=%s",
            symbol, strategy_name, u_pct, o_pct,
            f"{ratio:.2f}" if ratio else "N/A",
        )
        return obs

    def get_distribution(
        self, strategy_name: str, regime: str = "", ivr_band: str = "", dte_band: str = ""
    ) -> Optional[ResponseDistribution]:
        """Return the response distribution for a given context."""
        key = self._context_key(strategy_name, regime, ivr_band, dte_band)
        with self._lock:
            return self._distributions.get(key)

    def get_best_leverage_contexts(self, min_ratio: float = 1.5) -> List[ResponseDistribution]:
        """Return distributions with mean ratio >= min_ratio (high leverage contexts)."""
        with self._lock:
            result = []
            for d in self._distributions.values():
                if d.ratio_mean is not None and d.ratio_mean >= min_ratio and d.n >= MIN_OBS_FOR_DISTRIBUTION:
                    result.append(d)
            return sorted(result, key=lambda x: x.ratio_mean or 0, reverse=True)

    def get_summary(self) -> dict:
        """Return a high-level summary for monitoring."""
        with self._lock:
            total = len(self._observations)
            winners = sum(1 for o in self._observations if o.was_winner)
            high_ratio = [o for o in self._observations if o.option_underlying_ratio and o.option_underlying_ratio > 1.5]
            return {
                "total_observations": total,
                "winner_count": winners,
                "win_rate": winners / total if total else 0.0,
                "high_leverage_count": len(high_ratio),
                "distributions_computed": len(self._distributions),
            }

    def get_all_observations(self) -> List[ResponseObservation]:
        with self._lock:
            return list(self._observations)

    # ── Internal ───────────────────────────────────────────────────────────

    def _context_key(self, strategy: str, regime: str, ivr_band: str, dte_band: str) -> str:
        return f"{strategy}|{regime}|{ivr_band}|{dte_band}"

    def _update_distribution(self, ctx_key: str, strategy_name: str) -> None:
        """Recompute the distribution for ctx_key from all matching observations."""
        matching = [
            o for o in self._observations
            if self._context_key(o.strategy_name, o.regime, o.ivr_band, o.dte_band) == ctx_key
        ]
        n = len(matching)
        if n < MIN_OBS_FOR_DISTRIBUTION:
            return  # not enough data yet

        u_pcts = [o.underlying_pct_move for o in matching]
        o_pcts = [o.option_pct_move for o in matching]
        ratios = [o.option_underlying_ratio for o in matching if o.option_underlying_ratio is not None]
        outperform = sum(1 for o in matching if abs(o.option_pct_move) > abs(o.underlying_pct_move))

        def _pct(lst: list, p: float) -> float:
            if not lst:
                return 0.0
            s = sorted(lst)
            idx = int(len(s) * p / 100)
            return s[min(idx, len(s) - 1)]

        best_score = statistics.mean([o.response_score for o in matching])

        self._distributions[ctx_key] = ResponseDistribution(
            context_key=ctx_key,
            n=n,
            strategy_name=strategy_name,
            underlying_mean_pct=statistics.mean(u_pcts),
            underlying_median_pct=statistics.median(u_pcts),
            underlying_p25_pct=_pct(u_pcts, 25),
            underlying_p75_pct=_pct(u_pcts, 75),
            option_mean_pct=statistics.mean(o_pcts),
            option_median_pct=statistics.median(o_pcts),
            option_p25_pct=_pct(o_pcts, 25),
            option_p75_pct=_pct(o_pcts, 75),
            option_p90_pct=_pct(o_pcts, 90),
            ratio_mean=statistics.mean(ratios) if ratios else None,
            ratio_median=statistics.median(ratios) if ratios else None,
            ratio_p25=_pct(ratios, 25) if ratios else None,
            ratio_p75=_pct(ratios, 75) if ratios else None,
            ratio_p90=_pct(ratios, 90) if ratios else None,
            outperform_rate=outperform / n,
            best_contract_score=best_score,
            last_updated=datetime.now().isoformat(),
        )

    def _save_locked(self) -> None:
        """Atomic write. Called with self._lock held."""
        try:
            data = {
                "observations": [
                    {k: v for k, v in vars(o).items()}
                    for o in self._observations
                ],
                "distributions": {
                    k: {f: v for f, v in vars(d).items()}
                    for k, d in self._distributions.items()
                },
                "saved_at": datetime.now().isoformat(),
            }
            tmp = _PERSIST_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, default=str, indent=2)
            os.replace(tmp, _PERSIST_PATH)
        except Exception as exc:
            log.debug("[ResponseTracker] Save error: %s", exc)

    def _load(self) -> None:
        """Load from disk on startup."""
        try:
            if not os.path.exists(_PERSIST_PATH):
                return
            with open(_PERSIST_PATH) as f:
                data = json.load(f)
            obs_raw = data.get("observations", [])
            self._observations = [ResponseObservation(**o) for o in obs_raw]
            dist_raw = data.get("distributions", {})
            self._distributions = {k: ResponseDistribution(**v) for k, v in dist_raw.items()}
            log.info(
                "[ResponseTracker] Loaded %d observations, %d distributions.",
                len(self._observations), len(self._distributions),
            )
        except Exception as exc:
            log.debug("[ResponseTracker] Load error: %s", exc)
            self._observations = []
            self._distributions = {}
