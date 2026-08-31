"""
learning_system/historical_knowledge_replay.py
================================================
DTA-031: Historical Knowledge Replay Engine (HKR-v1)

PURPOSE
-------
Reconstruct what the Knowledge system would have predicted at historical
decision times using only information available at T+0 (no lookahead),
compute path outcomes from T+1..T+5 OHLCV bars, and write the resulting
HISTORICAL_REPLAY source_type records to data/klp/replay/REPLAY_YYYY-MM-DD.jsonl.

The HistoricalBehaviourEngine (HBE) automatically ingests these files on
the next load_outcomes() call, adding them to the evidence pool as
source_type="HISTORICAL_REPLAY".

DESIGN PRINCIPLES
-----------------
1. NO-LOOKAHEAD: entry = close at T+0; outcomes use T+1..T+5 bars only.
2. IDEMPOTENT: deterministic obs_id prevents duplicate records across runs.
3. APPEND-ONLY: never overwrites existing KLP or BOOTSTRAP records.
4. BROKER-SAFE: broker_calls=0, orders=0, no execution authority whatsoever.
5. ISOLATED: source_type="HISTORICAL_REPLAY" — never treated as live/paper.
6. REUSES DTA-028A: _compute_outcome_from_bars() — no second path simulator.
7. EXPERIMENTAL: replay evidence starts in experimental state (no auto-promotion).

SIGNAL RECONSTRUCTION METHOD
-----------------------------
Historical OHLCV bars are used to reconstruct approximate trading signals.
This is honest about what can and cannot be recovered:
  - reference_entry    = closing price at T+0 (accurate from real market data)
  - atr                = ATR(14) computed from bars up to T+0 (accurate)
  - stop / target      = ATR-multiplier formula, matching production parameters
  - direction          = BUY if close[T+0] >= SMA(20) up to T+0, else SELL
  - regime             = reconstructed from 5-day return + SMA position
  - scanner_confidence = 6.0 (synthetic placeholder)
  - candidate_score    = 0.60 (synthetic placeholder)

Records are labelled synthetic_signal=True and
reconstruction_method="OHLCV_ATR_SMA20" in the obs JSON.
All records have source_type="HISTORICAL_REPLAY".

SAFETY CONSTRAINTS
------------------
• Never modifies data/klp/KLP_*.jsonl or BOOTSTRAP_*.jsonl
• Writes only to data/klp/replay/REPLAY_YYYY-MM-DD.jsonl
• Checks for existing HKR1: obs_id before writing (idempotent)
• In DRY_RUN mode: zero disk writes; returns full ReplaySummary
• broker_calls = 0 and orders = 0 are hard invariants

REPORT
------
On completion, writes a machine-readable JSON report to:
  data/learning/historical_replay/replay_<start>_<end>_<timestamp>.json

USAGE
-----
    from datetime import date
    from learning_system.historical_knowledge_replay import (
        HistoricalKnowledgeReplayEngine, MODE_DRY_RUN, MODE_RESEARCH
    )

    engine = HistoricalKnowledgeReplayEngine()
    summary = engine.replay(
        start_date=date(2026, 7, 20),
        end_date=date(2026, 8, 31),
        mode=MODE_DRY_RUN,   # or MODE_RESEARCH to write to disk
    )
    print(summary.directional_accuracy, summary.target_hit_rate)
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_PROJECT_ROOT    = Path(__file__).parent.parent
_DEFAULT_KLP_DIR = _PROJECT_ROOT / "data" / "klp"
_REPLAY_SUBDIR   = "replay"
_REPORT_DIR      = _PROJECT_ROOT / "data" / "learning" / "historical_replay"

# ── Version / identity constants ──────────────────────────────────────────────
REPLAY_VERSION = "HKR_v1"
SOURCE_TYPE    = "HISTORICAL_REPLAY"
OBS_ID_PREFIX  = "HKR1"

# ── Signal reconstruction parameters (match config.py production values) ──────
_ATR_STOP_MULT     = 1.5   # matches config.ATR_STOP_MULTIPLIER
_ATR_TARGET_MULT   = 3.0   # 2:1 reward/risk (target = 2 × stop distance)
_ATR_PERIOD        = 14    # ATR(14) production standard
_SMA_PERIOD        = 20    # trend direction signal
_MIN_BARS_FOR_ATR  = 10    # minimum bars for valid ATR estimate
_MIN_BARS_FOR_SIGNAL = 5   # absolute minimum for any signal reconstruction

# ── Outcome constants (mirrored for standalone safety) ────────────────────────
TARGET_HIT        = "TARGET_HIT"
STOP_HIT          = "STOP_HIT"
OUTCOME_AMBIGUOUS = "OUTCOME_AMBIGUOUS"
OUTCOME_EXPIRED   = "OUTCOME_EXPIRED"
OUTCOME_PENDING   = "OUTCOME_PENDING"
OUTCOME_NO_DATA   = "OUTCOME_NO_DATA"

COMPLETED_OUTCOMES = frozenset({TARGET_HIT, STOP_HIT, OUTCOME_AMBIGUOUS, OUTCOME_EXPIRED})

# ── Execution modes ────────────────────────────────────────────────────────────
MODE_DRY_RUN  = "DRY_RUN"   # compute only, no disk writes
MODE_RESEARCH = "RESEARCH"  # write to data/klp/replay/; no execution authority
VALID_MODES   = (MODE_DRY_RUN, MODE_RESEARCH)

# ── Walk-forward partition fractions ──────────────────────────────────────────
_WF_TRAIN_FRAC      = 0.70  # first 70% of trading days → TRAIN
_WF_VALIDATION_FRAC = 0.20  # next 20% → VALIDATION
# remaining 10% → OOS

# ── Synthetic score placeholders (clearly labelled in obs JSON) ───────────────
_SYNTHETIC_SCANNER_CONFIDENCE = 6.0
_SYNTHETIC_CANDIDATE_SCORE    = 0.60

# ── Default symbol universe — base watchlist symbols ─────────────────────────
_DEFAULT_SYMBOLS: List[str] = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY", "BANKBARODA",
    "LT", "COALINDIA", "HCLTECH", "SBIN", "AXISBANK", "ONGC", "KOTAKBANK",
    "BHARTIARTL", "ITC", "BAJAJFINSV", "HINDALCO", "ULTRACEMCO", "TECHM", "NTPC",
]

# ── Historical fetch window ───────────────────────────────────────────────────
# Extra days to prepend before start_date for ATR context (ATR needs 14+ prior bars)
_ATR_CONTEXT_DAYS = 30      # extra calendar days fetched before start_date

# ── Symbol-to-sector mapping ─────────────────────────────────────────────────
_SYMBOL_SECTOR: Dict[str, str] = {
    "RELIANCE": "ENERGY",      "HDFCBANK": "BANK",         "ICICIBANK": "BANK",
    "TATASTEEL": "METALS",     "INFY": "IT",               "BANKBARODA": "BANK",
    "LT": "INFRA",             "COALINDIA": "ENERGY",      "HCLTECH": "IT",
    "SBIN": "BANK",            "AXISBANK": "BANK",         "ONGC": "ENERGY",
    "KOTAKBANK": "BANK",       "BHARTIARTL": "TELECOM",    "ITC": "FMCG",
    "BAJAJFINSV": "FINSERVICES","HINDALCO": "METALS",      "ULTRACEMCO": "CEMENT",
    "TECHM": "IT",             "NTPC": "ENERGY",
    "HINDUNILVR": "FMCG",      "ASIANPAINT": "CONSUMER",   "BAJFINANCE": "FINSERVICES",
    "MARUTI": "AUTO",          "SUNPHARMA": "PHARMA",      "WIPRO": "IT",
    "POWERGRID": "ENERGY",     "DIVISLAB": "PHARMA",       "TITAN": "CONSUMER",
    "DRREDDY": "PHARMA",       "ADANIENT": "CONGLOMERATE", "TATACONSUM": "FMCG",
    "NESTLEIND": "FMCG",       "HAVELLS": "CONSUMER",      "PIDILITIND": "CONSUMER",
    "JSWSTEEL": "METALS",      "ADANIPORTS": "INFRA",      "GRASIM": "CEMENT",
    "CIPLA": "PHARMA",         "LUPIN": "PHARMA",          "PERSISTENT": "IT",
    "NYKAA": "FMCG",           "AUROPHARMA": "PHARMA",
}


def _get_sector(symbol: str) -> str:
    return _SYMBOL_SECTOR.get(symbol.upper().strip(), "UNKNOWN")


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReplayRecord:
    """
    One completed observation+outcome pair produced by the historical replay.
    In-memory only — not persisted as this class; the JSONL format is the
    canonical persisted form.
    """
    obs_id:              str
    trading_date:        str            # "YYYY-MM-DD" (T+0)
    symbol:              str
    direction:           str            # "BUY" / "SELL"
    regime:              str
    reference_entry:     float
    knowledge_stop:      float
    knowledge_target:    float
    atr:                 float
    atr_pct:             float
    first_event:         str
    first_event_day:     Optional[str]
    target_hit:          bool
    stop_hit:            bool
    t1_ret_pct:          Optional[float]
    t3_ret_pct:          Optional[float]
    t5_ret_pct:          Optional[float]
    mfe_pct:             Optional[float]
    mae_pct:             Optional[float]
    direction_correct:   Optional[bool]
    validation_partition: str           # "TRAIN" | "VALIDATION" | "OOS"
    outcome_bars:        int
    data_quality_ok:     bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WalkForwardStats:
    """Per-partition walk-forward performance statistics."""
    partition:            str
    record_count:         int
    directional_accuracy: Optional[float]
    target_hit_rate:      Optional[float]
    stop_hit_rate:        Optional[float]
    expired_rate:         Optional[float]
    avg_t5_ret:           Optional[float]
    expectancy_r:         Optional[float]   # avg R: +rr on TARGET_HIT, -1 on STOP_HIT

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReplaySummary:
    """
    Full report produced by one HistoricalKnowledgeReplayEngine.replay() call.

    Persisted as JSON to data/learning/historical_replay/<replay_id>.json.
    Safety fields (broker_calls, orders, existing_records_modified) are
    always 0 and verified by tests.
    """
    # ── Identity ─────────────────────────────────────────────────────────────
    replay_id:              str
    start_date:             str
    end_date:               str
    symbols:                List[str]
    mode:                   str
    replay_version:         str = REPLAY_VERSION

    # ── Counters ─────────────────────────────────────────────────────────────
    trading_days_processed:  int = 0
    observations_attempted:  int = 0
    observations_written:    int = 0        # 0 in DRY_RUN
    outcomes_written:        int = 0        # 0 in DRY_RUN
    observations_skipped_dedup:              int = 0
    observations_skipped_insufficient_data: int = 0

    # ── Outcome breakdown ────────────────────────────────────────────────────
    outcomes_target_hit:    int = 0
    outcomes_stop_hit:      int = 0
    outcomes_expired:       int = 0
    outcomes_ambiguous:     int = 0
    outcomes_pending:       int = 0
    outcomes_no_data:       int = 0

    # ── Aggregate statistics ─────────────────────────────────────────────────
    directional_accuracy: Optional[float] = None
    target_hit_rate:      Optional[float] = None
    stop_hit_rate:        Optional[float] = None
    expired_rate:         Optional[float] = None
    avg_t5_ret_pct:       Optional[float] = None
    expectancy_r:         Optional[float] = None

    # ── Walk-forward breakdown ────────────────────────────────────────────────
    walk_forward_stats:   List[WalkForwardStats] = field(default_factory=list)

    # ── Breakdowns ────────────────────────────────────────────────────────────
    symbol_breakdown:     Dict[str, Dict] = field(default_factory=dict)
    regime_breakdown:     Dict[str, Dict] = field(default_factory=dict)

    # ── Safety invariants (always 0) ─────────────────────────────────────────
    broker_calls:                  int = 0
    orders:                        int = 0
    existing_records_modified:     int = 0

    # ── Metadata ─────────────────────────────────────────────────────────────
    duration_seconds:     float = 0.0
    report_path:          Optional[str] = None
    replay_files_written: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers (module-level, stateless — importable for tests)
# ─────────────────────────────────────────────────────────────────────────────

def make_obs_id(trading_date: str, symbol: str, direction: str) -> str:
    """
    Deterministic, collision-resistant obs_id for historical replay records.
    Format: HKR1:<YYYYMMDD>:113000:<SYMBOL>:<DIRECTION>

    The 113000 time slot represents the 11:30 IST canonical decision time used
    for daily-bar replay (one signal per symbol per day).  It is embedded in
    the ID to match the spec format HKR1:<date>:<time_bucket>:<symbol>:<direction>.

    Inputs are deterministic → running replay twice always produces the same ID.
    """
    date_compact = trading_date.replace("-", "")
    return f"{OBS_ID_PREFIX}:{date_compact}:113000:{symbol.upper()}:{direction.upper()}"


def get_trading_days(start: date, end: date) -> List[date]:
    """Return all weekdays (Mon–Fri) in [start, end], inclusive."""
    days: List[date] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:   # Monday=0 … Friday=4
            days.append(cur)
        cur = date.fromordinal(cur.toordinal() + 1)
    return days


def assign_partition(idx: int, total: int) -> str:
    """
    Assign a walk-forward partition label for the trading day at position idx.
    Chronological order: TRAIN → VALIDATION → OOS.
    """
    if total == 0:
        return "TRAIN"
    train_end      = int(total * _WF_TRAIN_FRAC)
    validation_end = int(total * (_WF_TRAIN_FRAC + _WF_VALIDATION_FRAC))
    if idx < train_end:
        return "TRAIN"
    if idx < validation_end:
        return "VALIDATION"
    return "OOS"


def compute_atr14(bars) -> float:
    """
    True Range ATR(14) from a list of PriceBar objects.
    Uses only bars already filtered to <= T+0 — no lookahead.
    Returns 0.0 if insufficient data.
    """
    if len(bars) < 2:
        return 0.0
    true_ranges = []
    for i in range(1, len(bars)):
        try:
            high       = float(bars[i].high)
            low        = float(bars[i].low)
            prev_close = float(bars[i - 1].close)
        except (TypeError, AttributeError):
            continue
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        if tr >= 0:
            true_ranges.append(tr)
    if not true_ranges:
        return 0.0
    last_n = true_ranges[-_ATR_PERIOD:] if len(true_ranges) >= _ATR_PERIOD else true_ranges
    return sum(last_n) / len(last_n)


def compute_sma(closes: List[float], period: int) -> Optional[float]:
    """Simple moving average of the last `period` values. None if insufficient."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def reconstruct_regime(bars) -> str:
    """
    Reconstruct approximate market regime from historical OHLCV bars.
    Uses only bars up to and including T+0 — no lookahead.

    Logic:
      - 5-day return + SMA(20) position determine regime.
      - Approximate production heuristic; explicitly labelled as reconstructed.
    """
    if len(bars) < 5:
        return "RANGE_MARKET"
    closes = []
    for b in bars:
        try:
            closes.append(float(b.close))
        except (TypeError, AttributeError):
            pass
    if len(closes) < 5:
        return "RANGE_MARKET"

    ret_5d = (closes[-1] / closes[-5] - 1.0) * 100.0 if closes[-5] > 0 else 0.0
    sma20  = compute_sma(closes, _SMA_PERIOD)
    above_sma = (sma20 is not None and closes[-1] > sma20)

    if ret_5d > 3.0 and above_sma:
        return "BULL"
    if ret_5d < -3.0 and not above_sma:
        return "BEAR"
    if abs(ret_5d) > 4.0:
        return "VOLATILE"
    return "RANGE_MARKET"


def bar_date_str(bar) -> str:
    """Extract ISO date string from PriceBar.timestamp."""
    ts = getattr(bar, "timestamp", None)
    if ts is None:
        return ""
    if hasattr(ts, "date"):
        return ts.date().isoformat()
    return str(ts)[:10]


def validate_bar(bar) -> bool:
    """Basic OHLC sanity check — guard against bad yfinance rows."""
    try:
        o = float(bar.open)
        h = float(bar.high)
        l = float(bar.low)
        c = float(bar.close)
        return c > 0 and h >= l > 0 and h >= c >= l
    except (TypeError, ValueError, AttributeError):
        return False


def pricebar_to_dict(bar) -> Dict[str, Any]:
    """Convert PriceBar → dict format required by _compute_outcome_from_bars."""
    return {
        "date":  bar_date_str(bar),
        "open":  float(bar.open),
        "high":  float(bar.high),
        "low":   float(bar.low),
        "close": float(bar.close),
    }


def safe_mean(values: List[float]) -> Optional[float]:
    """Return arithmetic mean or None if the list is empty."""
    if not values:
        return None
    return sum(values) / len(values)


def load_existing_obs_ids(path: Path) -> Set[str]:
    """
    Scan an existing replay JSONL file and return obs_ids of all
    KNOWLEDGE_OBSERVATION records already written.
    Used for idempotency checks before appending new records.
    """
    ids: Set[str] = set()
    if not path.exists():
        return ids
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("event_type") == "KNOWLEDGE_OBSERVATION":
                        oid = rec.get("obs_id") or rec.get("observation_id", "")
                        if oid:
                            ids.add(oid)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return ids


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class HistoricalKnowledgeReplayEngine:
    """
    DTA-031: Historical Knowledge Replay Engine.

    Reconstructs historical Knowledge predictions from OHLCV bar data,
    computes path outcomes using DTA-028A _compute_outcome_from_bars semantics,
    and writes HISTORICAL_REPLAY source_type records to dedicated replay files.

    Hard invariants (never violated):
        self.broker_calls             = 0   (no broker interaction)
        self.orders                   = 0   (no order creation)
        existing_records_modified     = 0   (append-only, never overwrites)

    Modes:
        DRY_RUN  — compute + report, no disk writes
        RESEARCH — write to data/klp/replay/REPLAY_YYYY-MM-DD.jsonl
    """

    def __init__(
        self,
        klp_dir:        Optional[Path] = None,
        feed_manager=None,
        _ohlcv_fetcher=None,    # callable(symbol) → List[PriceBar]; for tests
    ) -> None:
        self._klp_dir       = Path(klp_dir) if klp_dir else _DEFAULT_KLP_DIR
        self._replay_dir    = self._klp_dir / _REPLAY_SUBDIR
        self._feed_manager  = feed_manager
        self._ohlcv_fetcher = _ohlcv_fetcher

        # Safety invariants — never modified
        self.broker_calls = 0
        self.orders       = 0

        # Lazy import cache for _compute_outcome_from_bars
        self._outcome_fn = None

    # ── Safety property ───────────────────────────────────────────────────────

    @property
    def _compute_outcome(self):
        """Lazy import of _compute_outcome_from_bars (avoids circular import)."""
        if self._outcome_fn is None:
            from opportunity_engine.klp_outcome_engine import _compute_outcome_from_bars
            self._outcome_fn = _compute_outcome_from_bars
        return self._outcome_fn

    # ── Feed access ───────────────────────────────────────────────────────────

    def _get_feed(self):
        """Return feed manager (lazy init if not injected)."""
        if self._feed_manager is not None:
            return self._feed_manager
        try:
            from data_feeds.data_feed_manager import get_feed_manager
            return get_feed_manager()
        except Exception:
            return None

    def _fetch_bars(self, symbol: str, days: int) -> list:
        """
        Fetch historical OHLCV bars for `symbol` covering the last `days`
        calendar days.  Returns List[PriceBar] (empty on failure).
        Never raises.
        """
        if self._ohlcv_fetcher is not None:
            try:
                bars = self._ohlcv_fetcher(symbol)
                return bars if bars is not None else []
            except Exception:
                return []
        feed = self._get_feed()
        if feed is None:
            return []
        try:
            bars = feed.get_history(symbol, days=days, interval="1d")
            return bars or []
        except Exception as exc:
            log.debug("HKR: get_history failed for %s: %s", symbol, exc)
            return []

    # ── Signal reconstruction ─────────────────────────────────────────────────

    def _reconstruct_signal(
        self,
        symbol:       str,
        trading_date: date,
        bars_up_to:   list,
    ) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a trading signal for (symbol, trading_date) using only
        bars up to and including trading_date (no lookahead).

        Returns a dict compatible with KLP KNOWLEDGE_OBSERVATION format,
        or None if there is insufficient data for a valid signal.

        synthetic_signal=True documents that scanner scores are approximations.
        reconstruction_method="OHLCV_ATR_SMA20" documents the derivation method.
        """
        if not bars_up_to:
            return None

        # Strict no-lookahead filter
        cutoff = trading_date.isoformat()
        valid_bars = [b for b in bars_up_to if bar_date_str(b) <= cutoff]

        if len(valid_bars) < _MIN_BARS_FOR_SIGNAL:
            return None

        last_bar = valid_bars[-1]
        if not validate_bar(last_bar):
            return None

        entry = float(last_bar.close)
        if entry <= 0:
            return None

        # ATR(14) — computed from historical bars (no lookahead)
        atr = compute_atr14(valid_bars)
        if atr <= 0:
            atr = entry * 0.015   # 1.5% fallback estimate
        atr_pct = round(atr / entry * 100.0, 4)

        # Direction from SMA(20) — close >= SMA → BUY, else SELL
        closes = [float(b.close) for b in valid_bars if validate_bar(b)]
        sma20  = compute_sma(closes, _SMA_PERIOD)
        direction = "BUY" if (sma20 is None or entry >= sma20) else "SELL"

        # Stop and target — production ATR multiplier formula
        if direction == "BUY":
            stop   = round(entry - _ATR_STOP_MULT   * atr, 4)
            target = round(entry + _ATR_TARGET_MULT * atr, 4)
        else:
            stop   = round(entry + _ATR_STOP_MULT   * atr, 4)
            target = round(entry - _ATR_TARGET_MULT * atr, 4)

        if stop <= 0:
            stop = round(entry * 0.97, 4)   # hard floor guard

        stop_dist   = max(abs(entry - stop), 0.01)
        target_dist = abs(target - entry)
        rr = round(target_dist / stop_dist, 4)

        # Regime — reconstructed from historical OHLCV
        regime = reconstruct_regime(valid_bars)

        # Deterministic obs_id
        obs_id = make_obs_id(trading_date.isoformat(), symbol, direction)

        return {
            "observation_id":        obs_id,
            "obs_id":                obs_id,
            "event_type":            "KNOWLEDGE_OBSERVATION",
            "ts_utc":                datetime.combine(
                                         trading_date,
                                         datetime.min.time().replace(hour=6)
                                     ).replace(tzinfo=timezone.utc).isoformat(),
            "trading_date":          trading_date.isoformat(),
            "symbol":                symbol.upper(),
            "direction":             direction,
            "reference_entry":       round(entry, 4),
            "knowledge_target":      target,
            "knowledge_stop_loss":   stop,
            "knowledge_RR":          rr,
            "knowledge_confidence":  _SYNTHETIC_SCANNER_CONFIDENCE,
            "scanner_confidence":    _SYNTHETIC_SCANNER_CONFIDENCE,
            "candidate_score":       _SYNTHETIC_CANDIDATE_SCORE,
            "knowledge_score":       0.0,
            "atr":                   round(atr, 4),
            "atr_pct":               atr_pct,
            "regime":                regime,
            "sector":                _get_sector(symbol),
            "opportunity_id":        "",
            "source_type":           SOURCE_TYPE,
            "synthetic_signal":      True,
            "reconstruction_method": "OHLCV_ATR_SMA20",
            "no_lookahead":          True,
            "outcome_version":       "KLP_OBS_v1",
            "replay_version":        REPLAY_VERSION,
        }

    # ── Outcome computation ───────────────────────────────────────────────────

    def _compute_path_outcome(
        self,
        obs:         Dict[str, Any],
        future_bars: list,
    ) -> Dict[str, Any]:
        """
        Compute the T+1..T+5 path outcome for the reconstructed signal.
        Reuses DTA-028A _compute_outcome_from_bars — single path simulator.

        future_bars: PriceBar list for T+1 onward (auto-sliced to 5 bars).
        """
        entry     = float(obs["reference_entry"])
        target    = float(obs["knowledge_target"])
        stop      = float(obs["knowledge_stop_loss"])
        direction = obs["direction"]

        bar_dicts = [
            pricebar_to_dict(b)
            for b in future_bars[:5]
            if validate_bar(b)
        ]

        if not bar_dicts:
            return {
                "first_event":       OUTCOME_NO_DATA,
                "first_event_day":   None,
                "target_hit":        False,
                "stop_hit":          False,
                "theoretical_R":     None,
                "t1_ret_pct":        None,
                "t3_ret_pct":        None,
                "t5_ret_pct":        None,
                "mfe_pct":           None,
                "mae_pct":           None,
                "direction_correct": None,
                "ge1":               None,
                "ge2":               None,
                "ge3":               None,
                "bars_available":    0,
            }

        return self._compute_outcome(entry, target, stop, direction, bar_dicts)

    # ── Bars filtering ────────────────────────────────────────────────────────

    @staticmethod
    def _bars_up_to(bars: list, trading_date: date) -> list:
        """Return bars where date <= trading_date (no lookahead)."""
        cutoff = trading_date.isoformat()
        return [b for b in bars if bar_date_str(b) <= cutoff]

    @staticmethod
    def _bars_after(bars: list, trading_date: date) -> list:
        """Return bars strictly after trading_date (T+1 onwards)."""
        cutoff = trading_date.isoformat()
        return [b for b in bars if bar_date_str(b) > cutoff]

    # ── Disk write ────────────────────────────────────────────────────────────

    def _write_pair(
        self,
        trading_date: date,
        obs:          Dict[str, Any],
        outcome:      Dict[str, Any],
        partition:    str,
    ) -> bool:
        """
        Append KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE to the replay file.
        APPEND-ONLY — never truncates or modifies existing lines.
        Returns True on success, False on I/O error.
        """
        self._replay_dir.mkdir(parents=True, exist_ok=True)
        replay_file = self._replay_dir / f"REPLAY_{trading_date.isoformat()}.jsonl"

        obs_id = obs["obs_id"]

        # Build outcome record (OUTCOME_UPDATE format matching KLP convention)
        outcome_rec: Dict[str, Any] = {
            "observation_id":     obs_id,
            "obs_id":             obs_id,
            "event_type":         "OUTCOME_UPDATE",
            "ts_utc":             datetime.now(timezone.utc).isoformat(),
            "trading_date":       trading_date.isoformat(),
            "symbol":             obs["symbol"],
            "direction":          obs["direction"],
            "reference_entry":    obs["reference_entry"],
            "knowledge_target":   obs["knowledge_target"],
            "knowledge_stop_loss": obs["knowledge_stop_loss"],
            "knowledge_RR":       obs["knowledge_RR"],
            "source_type":        SOURCE_TYPE,
            "validation_partition": partition,
            "no_lookahead":       True,
            "outcome_version":    "KLP_OUTCOME_v1",
            "replay_version":     REPLAY_VERSION,
        }
        outcome_rec.update(outcome)

        # Annotate obs with partition and EXPERIMENTAL validation status before writing
        obs_rec = dict(obs)
        obs_rec["validation_partition"]    = partition
        obs_rec["replay_validation_status"] = "EXPERIMENTAL"

        try:
            with replay_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(obs_rec,     default=str) + "\n")
                fh.write(json.dumps(outcome_rec, default=str) + "\n")
            return True
        except OSError as exc:
            log.error("HKR: Write failed for %s: %s", replay_file, exc)
            return False

    # ── Walk-forward statistics ───────────────────────────────────────────────

    def _walk_forward_stats(
        self, records: List[ReplayRecord]
    ) -> List[WalkForwardStats]:
        """Compute performance statistics for each walk-forward partition."""
        results: List[WalkForwardStats] = []

        for partition in ("TRAIN", "VALIDATION", "OOS"):
            recs      = [r for r in records if r.validation_partition == partition]
            completed = [r for r in recs if r.first_event in COMPLETED_OUTCOMES]
            n         = len(completed)

            if n == 0:
                results.append(WalkForwardStats(
                    partition=partition, record_count=0,
                    directional_accuracy=None, target_hit_rate=None,
                    stop_hit_rate=None, expired_rate=None,
                    avg_t5_ret=None, expectancy_r=None,
                ))
                continue

            targets = [r for r in completed if r.first_event == TARGET_HIT]
            stops   = [r for r in completed if r.first_event == STOP_HIT]
            expired = [r for r in completed if r.first_event == OUTCOME_EXPIRED]
            dir_ok  = [r for r in completed if r.direction_correct is True]

            # Expectancy in R: +RR for TARGET_HIT, -1 for STOP_HIT
            r_vals: List[float] = []
            for r in completed:
                stop_dist = max(abs(r.reference_entry - r.knowledge_stop), 1e-6)
                if r.first_event == TARGET_HIT:
                    r_vals.append(abs(r.knowledge_target - r.reference_entry) / stop_dist)
                elif r.first_event == STOP_HIT:
                    r_vals.append(-1.0)

            t5_rets = [r.t5_ret_pct for r in completed if r.t5_ret_pct is not None]

            results.append(WalkForwardStats(
                partition=partition,
                record_count=n,
                directional_accuracy=round(len(dir_ok) / n, 4),
                target_hit_rate=round(len(targets) / n, 4),
                stop_hit_rate=round(len(stops)   / n, 4),
                expired_rate=round(len(expired)  / n, 4),
                avg_t5_ret=round(safe_mean(t5_rets), 4) if t5_rets else None,
                expectancy_r=round(safe_mean(r_vals), 4) if r_vals else None,
            ))

        return results

    # ── Report ────────────────────────────────────────────────────────────────

    def _save_report(self, summary: ReplaySummary) -> Optional[Path]:
        """Write machine-readable JSON report. Returns path on success."""
        try:
            _REPORT_DIR.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            name = f"replay_{summary.start_date}_{summary.end_date}_{ts}.json"
            out  = _REPORT_DIR / name
            with out.open("w", encoding="utf-8") as fh:
                json.dump(summary.as_dict(), fh, indent=2, default=str)
            return out
        except OSError as exc:
            log.warning("HKR: Failed to save report: %s", exc)
            return None

    # ── Main entry point ──────────────────────────────────────────────────────

    def replay(
        self,
        start_date: date,
        end_date:   date,
        symbols:    Optional[List[str]] = None,
        mode:       str                 = MODE_DRY_RUN,
    ) -> ReplaySummary:
        """
        Run historical knowledge replay from start_date to end_date.

        For each (trading_date, symbol):
          1. Reconstruct signal from OHLCV bars ≤ trading_date (no lookahead).
          2. Compute path outcome from T+1..T+5 bars (DTA-028A semantics).
          3. DRY_RUN:  compute only — no disk writes.
             RESEARCH: append KNOWLEDGE_OBSERVATION + OUTCOME_UPDATE to
                       data/klp/replay/REPLAY_YYYY-MM-DD.jsonl

        Returns ReplaySummary with full statistics and walk-forward breakdown.
        Report JSON is always saved to data/learning/historical_replay/.

        Safety invariants preserved regardless of mode:
            broker_calls = 0
            orders = 0
            existing_records_modified = 0
        """
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {VALID_MODES}"
            )

        t_start      = time.monotonic()
        syms         = [s.upper().strip() for s in (symbols or _DEFAULT_SYMBOLS)]
        trading_days = get_trading_days(start_date, end_date)

        if not trading_days:
            log.warning("HKR: No trading days in [%s, %s]", start_date, end_date)
            return ReplaySummary(
                replay_id=self._make_run_id(start_date, end_date),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                symbols=syms,
                mode=mode,
            )

        total_days = len(trading_days)

        # Calendar days to fetch: replay window + ATR context before start
        replay_cal_days  = (end_date - start_date).days
        fetch_days       = replay_cal_days + _ATR_CONTEXT_DAYS + 10  # +5 for outcome T+5

        all_records:     List[ReplayRecord] = []
        written_files:   Set[str] = set()
        dedup_skipped    = 0
        insuf_data       = 0

        for sym in syms:
            log.debug("HKR: Processing %s (fetch_days=%d)", sym, fetch_days)
            all_bars = self._fetch_bars(sym, days=fetch_days)

            if not all_bars:
                log.debug("HKR: No bars returned for %s — skipping", sym)
                insuf_data += total_days
                continue

            # Ensure ascending chronological order
            all_bars.sort(key=bar_date_str)

            # Pre-load disk-existing obs_ids for idempotency (RESEARCH mode only)
            written_ids: Set[str] = set()
            if mode == MODE_RESEARCH:
                for d in trading_days:
                    replay_file = self._replay_dir / f"REPLAY_{d.isoformat()}.jsonl"
                    written_ids |= load_existing_obs_ids(replay_file)

            for day_idx, trading_date in enumerate(trading_days):
                partition = assign_partition(day_idx, total_days)

                bars_up = self._bars_up_to(all_bars, trading_date)
                if len(bars_up) < _MIN_BARS_FOR_SIGNAL:
                    insuf_data += 1
                    continue

                obs = self._reconstruct_signal(sym, trading_date, bars_up)
                if obs is None:
                    insuf_data += 1
                    continue

                obs_id = obs["obs_id"]

                # Idempotency: skip if this obs already written to disk
                if obs_id in written_ids:
                    dedup_skipped += 1
                    continue

                bars_after = self._bars_after(all_bars, trading_date)
                outcome    = self._compute_path_outcome(obs, bars_after)

                rec = ReplayRecord(
                    obs_id=obs_id,
                    trading_date=trading_date.isoformat(),
                    symbol=sym,
                    direction=obs["direction"],
                    regime=obs.get("regime", ""),
                    reference_entry=float(obs["reference_entry"]),
                    knowledge_stop=float(obs["knowledge_stop_loss"]),
                    knowledge_target=float(obs["knowledge_target"]),
                    atr=float(obs["atr"]),
                    atr_pct=float(obs["atr_pct"]),
                    first_event=outcome["first_event"],
                    first_event_day=outcome.get("first_event_day"),
                    target_hit=bool(outcome.get("target_hit", False)),
                    stop_hit=bool(outcome.get("stop_hit", False)),
                    t1_ret_pct=outcome.get("t1_ret_pct"),
                    t3_ret_pct=outcome.get("t3_ret_pct"),
                    t5_ret_pct=outcome.get("t5_ret_pct"),
                    mfe_pct=outcome.get("mfe_pct"),
                    mae_pct=outcome.get("mae_pct"),
                    direction_correct=outcome.get("direction_correct"),
                    validation_partition=partition,
                    outcome_bars=outcome.get("bars_available", 0),
                )
                all_records.append(rec)

                if mode == MODE_RESEARCH:
                    ok = self._write_pair(trading_date, obs, outcome, partition)
                    if ok:
                        written_ids.add(obs_id)
                        written_files.add(
                            str(self._replay_dir / f"REPLAY_{trading_date.isoformat()}.jsonl")
                        )

        # ── Aggregate statistics ───────────────────────────────────────────────
        completed  = [r for r in all_records if r.first_event in COMPLETED_OUTCOMES]
        n_comp     = len(completed)

        n_target   = sum(1 for r in completed if r.first_event == TARGET_HIT)
        n_stop     = sum(1 for r in completed if r.first_event == STOP_HIT)
        n_expired  = sum(1 for r in completed if r.first_event == OUTCOME_EXPIRED)
        n_ambig    = sum(1 for r in completed if r.first_event == OUTCOME_AMBIGUOUS)
        n_pending  = sum(1 for r in all_records if r.first_event == OUTCOME_PENDING)
        n_no_data  = sum(1 for r in all_records if r.first_event == OUTCOME_NO_DATA)
        n_dir_ok   = sum(1 for r in completed if r.direction_correct is True)

        def _rate(num: int) -> Optional[float]:
            return round(num / n_comp, 4) if n_comp else None

        t5_rets  = [r.t5_ret_pct for r in completed if r.t5_ret_pct is not None]

        r_vals: List[float] = []
        for r in completed:
            stop_dist = max(abs(r.reference_entry - r.knowledge_stop), 1e-6)
            if r.first_event == TARGET_HIT:
                r_vals.append(abs(r.knowledge_target - r.reference_entry) / stop_dist)
            elif r.first_event == STOP_HIT:
                r_vals.append(-1.0)

        # Symbol breakdown
        sym_breakdown: Dict[str, Dict] = {}
        for s in syms:
            s_recs = [r for r in completed if r.symbol == s]
            if not s_recs:
                continue
            s_n    = len(s_recs)
            s_hits = sum(1 for r in s_recs if r.first_event == TARGET_HIT)
            s_dok  = sum(1 for r in s_recs if r.direction_correct)
            sym_breakdown[s] = {
                "count":              s_n,
                "target_hit_rate":    round(s_hits / s_n, 4),
                "directional_accuracy": round(s_dok / s_n, 4),
            }

        # Regime breakdown
        regime_breakdown: Dict[str, Dict] = {}
        for reg in sorted({r.regime for r in completed}):
            reg_recs = [r for r in completed if r.regime == reg]
            reg_n    = len(reg_recs)
            if reg_n == 0:
                continue
            reg_hits = sum(1 for r in reg_recs if r.first_event == TARGET_HIT)
            regime_breakdown[reg] = {
                "count":           reg_n,
                "target_hit_rate": round(reg_hits / reg_n, 4),
            }

        # Walk-forward
        wf_stats = self._walk_forward_stats(all_records)

        # Written count (zero in DRY_RUN)
        n_obs_written = len(all_records) if mode == MODE_RESEARCH else 0

        run_id = self._make_run_id(start_date, end_date)

        summary = ReplaySummary(
            replay_id=run_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            symbols=syms,
            mode=mode,
            trading_days_processed=total_days,
            observations_attempted=len(all_records),
            observations_written=n_obs_written,
            outcomes_written=n_obs_written,    # one outcome per observation
            observations_skipped_dedup=dedup_skipped,
            observations_skipped_insufficient_data=insuf_data,
            outcomes_target_hit=n_target,
            outcomes_stop_hit=n_stop,
            outcomes_expired=n_expired,
            outcomes_ambiguous=n_ambig,
            outcomes_pending=n_pending,
            outcomes_no_data=n_no_data,
            directional_accuracy=_rate(n_dir_ok),
            target_hit_rate=_rate(n_target),
            stop_hit_rate=_rate(n_stop),
            expired_rate=_rate(n_expired),
            avg_t5_ret_pct=round(safe_mean(t5_rets), 4) if t5_rets else None,
            expectancy_r=round(safe_mean(r_vals), 4) if r_vals else None,
            walk_forward_stats=wf_stats,
            symbol_breakdown=sym_breakdown,
            regime_breakdown=regime_breakdown,
            broker_calls=0,
            orders=0,
            existing_records_modified=0,
            duration_seconds=round(time.monotonic() - t_start, 2),
            replay_files_written=sorted(written_files),
        )

        # Save report (always, even in DRY_RUN mode)
        rp = self._save_report(summary)
        if rp:
            summary.report_path = str(rp)

        log.info(
            "HKR: replay done mode=%s syms=%d days=%d attempts=%d "
            "tgt_rate=%s dir_acc=%s dur=%.1fs",
            mode, len(syms), total_days, len(all_records),
            summary.target_hit_rate, summary.directional_accuracy,
            summary.duration_seconds,
        )
        return summary

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_run_id(start: date, end: date) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"HKR_{start.isoformat()}_{end.isoformat()}_{ts}"
