"""
opportunity_engine/klp_outcome_engine.py
==========================================
KLP Outcome Engine  —  KLP-002

PURPOSE
-------
Fill outcome fields for pending KLP KNOWLEDGE_OBSERVATION records by
computing the theoretical trade outcome from daily OHLCV price data.

For each observation that has reference_entry/knowledge_target/knowledge_stop_loss
set and at least T+1 data available:

  1. Resolve NSE ticker for yfinance
  2. Fetch T+1 .. T+5 daily OHLCV bars (no intraday — daily resolution only)
  3. Compute target_hit, stop_hit, first_event, theoretical_R
  4. Compute MFE, MAE over T+1..T+5 horizon
  5. Compute T+1, T+3, T+5 return (%) vs reference_entry
  6. Write OUTCOME_UPDATE record (append-only, keyed by obs_id)

OUTCOME STATUSES (first_event field)
-------------------------------------
  TARGET_HIT        — target reached before stop (or alone)
  STOP_HIT          — stop reached before target (or alone)
  OUTCOME_AMBIGUOUS — target and stop both reachable on the same bar
                      (intrabar order cannot be established from daily OHLCV)
  OUTCOME_EXPIRED   — T+5 passed; neither target nor stop reached
  OUTCOME_PENDING   — T+1 is today or future; no data yet
  OUTCOME_NO_DATA   — yfinance returned no data for this symbol/period

LOOK-AHEAD RULES
----------------
• Entry = reference_entry (frozen at scan time — never the T+1 open)
• Target and stop are frozen values from the original KNOWLEDGE_OBSERVATION
• Outcome is evaluated ONLY from T+1 bars onward
• T+0 close / high / low are NOT used for outcome computation

CONTRACT
--------
• Never raises — all public methods swallow exceptions
• Never modifies existing KLP records
• Append-only OUTCOME_UPDATE records with no_lookahead=True
• Dedup: one OUTCOME_UPDATE per obs_id per session
• broker_calls = 0, orders = 0, portfolio_changes = 0
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ── Default data directory ────────────────────────────────────────────────────
_DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "klp"

# ── Horizon ───────────────────────────────────────────────────────────────────
_OUTCOME_HORIZON_DAYS = 5   # T+1 .. T+5

# ── Session-level dedup set ───────────────────────────────────────────────────
_OUTCOMES_WRITTEN_THIS_SESSION: Set[str] = set()
_DEDUP_LOCK = threading.Lock()

# ── Outcome status constants ──────────────────────────────────────────────────
TARGET_HIT        = "TARGET_HIT"
STOP_HIT          = "STOP_HIT"
OUTCOME_AMBIGUOUS = "OUTCOME_AMBIGUOUS"
OUTCOME_EXPIRED   = "OUTCOME_EXPIRED"
OUTCOME_PENDING   = "OUTCOME_PENDING"
OUTCOME_NO_DATA   = "OUTCOME_NO_DATA"


class KLPOutcomeEngine:
    """
    Processes pending KLP observations and fills outcome fields.

    Usage:
        engine = KLPOutcomeEngine()
        result = engine.fill_pending_outcomes(["2026-08-19", "2026-08-20"])
        # {"processed": N, "skipped_pending": M, "skipped_no_data": K}

    For testing, inject a _ohlcv_fetcher callable:
        def mock_fetch(symbol, trading_date): return [{"date":..., "open":..., ...}, ...]
        engine = KLPOutcomeEngine(_ohlcv_fetcher=mock_fetch)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        _ohlcv_fetcher=None,
    ) -> None:
        self._data_dir     = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._ohlcv_fetcher = _ohlcv_fetcher or _fetch_ohlcv_yfinance
        self._outcomes_written: Set[str] = set()   # instance-scoped dedup
        self._outcomes_written: Set[str] = set()   # instance-level dedup

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def fill_pending_outcomes(
        self,
        dates: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process all KLP files for the given dates (default: last 7 days).
        Returns summary stats.  Never raises.
        """
        try:
            return self._fill_impl(dates)
        except Exception as exc:
            return {"processed": 0, "error": str(exc)}

    def get_pending_count(
        self,
        date_str: Optional[str] = None,
    ) -> int:
        """
        Count KNOWLEDGE_OBSERVATION records without outcome data for date_str.
        Never raises.
        """
        try:
            if date_str is None:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            obs = self._load_pending_obs(date_str)
            return len(obs)
        except Exception:
            return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Implementation
    # ─────────────────────────────────────────────────────────────────────────

    def _fill_impl(self, dates: Optional[List[str]]) -> Dict[str, Any]:
        if dates is None:
            today = date.today()
            dates = [str(today - timedelta(days=i)) for i in range(1, 8)]

        summary = {
            "processed":         0,
            "skipped_pending":   0,
            "skipped_no_data":   0,
            "skipped_dedup":     0,
            "error":             None,
        }

        for date_str in dates:
            pending = self._load_pending_obs(date_str)
            for obs in pending:
                obs_id = obs.get("obs_id", "")
                if obs_id in self._outcomes_written:
                    summary["skipped_dedup"] += 1
                    continue

                result = self._compute_outcome(obs)
                if result["first_event"] == OUTCOME_PENDING:
                    summary["skipped_pending"] += 1
                    continue
                if result["first_event"] == OUTCOME_NO_DATA:
                    summary["skipped_no_data"] += 1
                    continue

                rec = self._build_outcome_record(obs, result)
                self._write_record(rec, date_str)

                with _DEDUP_LOCK:
                    _OUTCOMES_WRITTEN_THIS_SESSION.add(obs_id)
                self._outcomes_written.add(obs_id)
                summary["processed"] += 1

        return summary

    def _load_pending_obs(self, date_str: str) -> List[Dict[str, Any]]:
        """Return KNOWLEDGE_OBSERVATION records with null outcome fields."""
        klp_file = self._data_dir / f"KLP_{date_str}.jsonl"
        if not klp_file.exists():
            return []

        # Collect obs_ids that already have outcomes
        completed_obs_ids: Set[str] = set()
        all_obs: List[Dict[str, Any]] = []

        with klp_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                et = rec.get("event_type", "")
                if et == "OUTCOME_UPDATE":
                    completed_obs_ids.add(rec.get("obs_id", ""))
                elif et == "KNOWLEDGE_OBSERVATION":
                    all_obs.append(rec)

        # Return observations without outcomes that have valid price data
        pending = []
        for obs in all_obs:
            if obs.get("obs_id") in completed_obs_ids:
                continue
            if not obs.get("reference_entry"):
                continue
            if not obs.get("knowledge_target") and not obs.get("knowledge_stop_loss"):
                continue
            pending.append(obs)
        return pending

    def _compute_outcome(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute outcome fields for a single pending observation.
        Returns a dict with outcome fields (never raises).
        """
        trading_date = obs.get("trading_date", "")
        symbol       = (obs.get("symbol") or "").strip()
        direction    = (obs.get("direction") or "BUY").upper()
        entry        = float(obs.get("reference_entry") or 0.0)
        target       = obs.get("knowledge_target")
        stop         = obs.get("knowledge_stop_loss")

        target_f = float(target) if target else None
        stop_f   = float(stop)   if stop   else None

        # Check if T+1 is available (trading_date must be in the past)
        try:
            td = date.fromisoformat(trading_date)
            if td >= date.today():
                return {"first_event": OUTCOME_PENDING}
        except Exception:
            return {"first_event": OUTCOME_NO_DATA}

        # Fetch OHLCV bars
        try:
            bars = self._ohlcv_fetcher(symbol, trading_date)
        except Exception:
            return {"first_event": OUTCOME_NO_DATA}

        if not bars:
            return {"first_event": OUTCOME_NO_DATA}

        bars = bars[:_OUTCOME_HORIZON_DAYS]

        # ── Outcome logic ─────────────────────────────────────────────────
        result = _compute_outcome_from_bars(
            entry=entry,
            target=target_f,
            stop=stop_f,
            direction=direction,
            bars=bars,
        )
        return result

    def _build_outcome_record(
        self,
        obs: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> Dict[str, Any]:
        now_utc  = datetime.now(timezone.utc)
        date_str = obs.get("trading_date", now_utc.strftime("%Y-%m-%d"))
        return {
            "obs_id":              obs.get("obs_id", ""),
            "event_type":          "OUTCOME_UPDATE",
            "ts_utc":              now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trading_date":        date_str,
            "symbol":              obs.get("symbol", ""),
            "direction":           obs.get("direction", ""),
            "reference_entry":     obs.get("reference_entry"),
            "knowledge_target":    obs.get("knowledge_target"),
            "knowledge_stop_loss": obs.get("knowledge_stop_loss"),
            "knowledge_RR":        obs.get("knowledge_RR"),
            # ── Computed outcomes ─────────────────────────────────────────
            "first_event":         outcome.get("first_event"),
            "first_event_day":     outcome.get("first_event_day"),
            "target_hit":          outcome.get("target_hit"),
            "stop_hit":            outcome.get("stop_hit"),
            "theoretical_R":       outcome.get("theoretical_R"),
            "t1_ret_pct":          outcome.get("t1_ret_pct"),
            "t3_ret_pct":          outcome.get("t3_ret_pct"),
            "t5_ret_pct":          outcome.get("t5_ret_pct"),
            "mfe_pct":             outcome.get("mfe_pct"),
            "mae_pct":             outcome.get("mae_pct"),
            "direction_correct":   outcome.get("direction_correct"),
            "ge1":                 outcome.get("ge1"),
            "ge2":                 outcome.get("ge2"),
            "ge3":                 outcome.get("ge3"),
            "bars_available":      outcome.get("bars_available", 0),
            "outcome_version":     "KLP_OUTCOME_v1",
            "no_lookahead":        True,
        }

    def _write_record(self, rec: Dict[str, Any], date_str: str) -> None:
        """Append record to date's KLP JSONL file.  Never raises."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            out_path = self._data_dir / f"KLP_{date_str}.jsonl"
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False))
                fh.write("\n")
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Core outcome computation  (pure function — no I/O, fully testable)
# ─────────────────────────────────────────────────────────────────────────────

def compute_outcome_from_bars(
    entry: float,
    target: Optional[float],
    stop: Optional[float],
    direction: str,
    bars: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Public alias (testable entry point) for `_compute_outcome_from_bars`.
    bars: list of {"date", "open", "high", "low", "close"} dicts, T+1 first.
    """
    return _compute_outcome_from_bars(entry, target, stop, direction, bars)


def _compute_outcome_from_bars(
    entry: float,
    target: Optional[float],
    stop: Optional[float],
    direction: str,
    bars: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute outcome fields from pre-fetched OHLCV bars.

    bars: list of {"date", "open", "high", "low", "close"}, T+1 first.
    entry: reference_entry (frozen at scan time).
    direction: "BUY" or "SELL"/"SHORT" — determines favourable direction.

    Returns dict with:
      first_event, first_event_day, target_hit, stop_hit, theoretical_R,
      t1_ret_pct, t3_ret_pct, t5_ret_pct, mfe_pct, mae_pct,
      direction_correct, ge1, ge2, ge3, bars_available
    """
    is_long = direction == "BUY"
    out: Dict[str, Any] = {
        "first_event":     OUTCOME_PENDING,
        "first_event_day": None,
        "target_hit":      False,
        "stop_hit":        False,
        "theoretical_R":   None,
        "t1_ret_pct":      None,
        "t3_ret_pct":      None,
        "t5_ret_pct":      None,
        "mfe_pct":         None,
        "mae_pct":         None,
        "direction_correct": None,
        "ge1":             None,
        "ge2":             None,
        "ge3":             None,
        "bars_available":  len(bars),
    }

    if not bars or entry <= 0:
        out["first_event"] = OUTCOME_NO_DATA
        return out

    # ── T+N return calculations ────────────────────────────────────────────
    def ret_at(n: int) -> Optional[float]:
        if n <= len(bars):
            c = float(bars[n - 1]["close"])
            return round((c / entry - 1.0) * 100.0, 4)
        return None

    out["t1_ret_pct"] = ret_at(1)
    out["t3_ret_pct"] = ret_at(3)
    out["t5_ret_pct"] = ret_at(5)

    t1 = out["t1_ret_pct"]
    if t1 is not None:
        fav = t1 > 0 if is_long else t1 < 0
        out["direction_correct"] = fav
        out["ge1"] = abs(t1) >= 1.0 and fav
        out["ge2"] = abs(t1) >= 2.0 and fav
        out["ge3"] = abs(t1) >= 3.0 and fav

    # ── MFE / MAE ─────────────────────────────────────────────────────────
    highs = [float(b["high"]) for b in bars]
    lows  = [float(b["low"])  for b in bars]

    if is_long:
        out["mfe_pct"] = round(max((h / entry - 1.0) * 100.0 for h in highs), 4)
        out["mae_pct"] = round(min((l / entry - 1.0) * 100.0 for l in lows),  4)
    else:
        out["mfe_pct"] = round(max((entry / l - 1.0) * 100.0 for l in lows  if l > 0), 4) if lows  else None
        out["mae_pct"] = round(min((entry / h - 1.0) * 100.0 for h in highs if h > 0), 4) if highs else None

    # ── Target / stop hit detection ────────────────────────────────────────
    target_hit_day: Optional[str] = None
    stop_hit_day:   Optional[str] = None

    for bar in bars:
        bar_date = bar.get("date", "")
        high     = float(bar["high"])
        low      = float(bar["low"])

        if target is not None:
            if is_long  and high >= target and target_hit_day is None:
                target_hit_day = bar_date
            if not is_long and low  <= target and target_hit_day is None:
                target_hit_day = bar_date

        if stop is not None:
            if is_long  and low  <= stop and stop_hit_day is None:
                stop_hit_day = bar_date
            if not is_long and high >= stop and stop_hit_day is None:
                stop_hit_day = bar_date

    # ── First-event resolution ─────────────────────────────────────────────
    rr = float(out.get("knowledge_RR") or 0.0) if "knowledge_RR" in out else 0.0
    # Note: theoretical_R computed below after resolving first_event

    if target_hit_day is not None and stop_hit_day is not None:
        if target_hit_day < stop_hit_day:
            out["first_event"]     = TARGET_HIT
            out["first_event_day"] = target_hit_day
            out["target_hit"]      = True
        elif stop_hit_day < target_hit_day:
            out["first_event"]     = STOP_HIT
            out["first_event_day"] = stop_hit_day
            out["stop_hit"]        = True
        else:
            # Same bar — ambiguous
            out["first_event"]     = OUTCOME_AMBIGUOUS
            out["first_event_day"] = target_hit_day
            out["target_hit"]      = True
            out["stop_hit"]        = True
    elif target_hit_day is not None:
        out["first_event"]     = TARGET_HIT
        out["first_event_day"] = target_hit_day
        out["target_hit"]      = True
    elif stop_hit_day is not None:
        out["first_event"]     = STOP_HIT
        out["first_event_day"] = stop_hit_day
        out["stop_hit"]        = True
    elif len(bars) >= _OUTCOME_HORIZON_DAYS:
        # Full horizon available and neither target nor stop was hit
        out["first_event"] = OUTCOME_EXPIRED
    else:
        out["first_event"] = OUTCOME_PENDING

    # ── Theoretical R (risk multiple) ──────────────────────────────────────
    if out["target_hit"] and not out["stop_hit"]:
        # Use actual RR if target and stop are available
        if target is not None and stop is not None and entry > 0 and entry != stop:
            actual_rr = abs(target - entry) / abs(entry - stop)
            out["theoretical_R"] = round(actual_rr, 4)
    elif out["stop_hit"] and not out["target_hit"]:
        out["theoretical_R"] = -1.0
    elif out["first_event"] == OUTCOME_AMBIGUOUS:
        out["theoretical_R"] = None   # cannot determine

    return out


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV fetcher (yfinance)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_ohlcv_yfinance(
    symbol: str,
    trading_date: str,
    horizon_days: int = _OUTCOME_HORIZON_DAYS,
) -> List[Dict[str, Any]]:
    """
    Fetch T+1..T+horizon daily OHLCV bars from yfinance.
    Returns list of {"date", "open", "high", "low", "close", "volume"} dicts.
    Returns [] on any error.
    """
    try:
        import yfinance as yf
        from data_feeds.yahoo_feed import GLOBAL_SYMBOL_MAP

        start_dt = date.fromisoformat(trading_date) + timedelta(days=1)
        end_dt   = start_dt + timedelta(days=horizon_days * 3)  # buffer for weekends/holidays

        ticker_sym = GLOBAL_SYMBOL_MAP.get(symbol.upper())
        if ticker_sym is None:
            ticker_sym = f"{symbol}.NS"

        df = yf.download(
            ticker_sym,
            start=str(start_dt),
            end=str(end_dt),
            interval="1d",
            progress=False,
            auto_adjust=True,
            timeout=10,
        )
        if df is None or df.empty:
            return []

        bars = []
        for ts, row in df.iterrows():
            try:
                bars.append({
                    "date":   str(ts.date()) if hasattr(ts, "date") else str(ts)[:10],
                    "open":   float(row["Open"]),
                    "high":   float(row["High"]),
                    "low":    float(row["Low"]),
                    "close":  float(row["Close"]),
                    "volume": float(row.get("Volume", 0.0) or 0.0),
                })
            except (KeyError, TypeError, ValueError):
                continue
        return bars[:horizon_days]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_ENGINE_INSTANCE: Optional[KLPOutcomeEngine] = None
_ENGINE_LOCK = threading.Lock()


def get_klp_outcome_engine() -> KLPOutcomeEngine:
    """Return the session-scoped singleton KLPOutcomeEngine."""
    global _ENGINE_INSTANCE
    with _ENGINE_LOCK:
        if _ENGINE_INSTANCE is None:
            _ENGINE_INSTANCE = KLPOutcomeEngine()
    return _ENGINE_INSTANCE
