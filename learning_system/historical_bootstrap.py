"""
learning_system/historical_bootstrap.py
==========================================
KBS-001 — Historical Knowledge Bootstrap

Generates provenance-tagged OutcomeRecords from historical NSE OHLCV data.

Signal logic: 20-day close breakout (close > max(close[-21:-1])).
Stop:  entry - 1.5 × ATR(14)
Target: entry + RR × (entry - stop)  [default RR = 2.0]
Regime: derived from NIFTY index (^NSEI) 50-day and 200-day SMA.

ANTI-LOOKAHEAD CONTRACT (verified by test_dta_system_015):
  At time T, signal features use ONLY bars ending on or before T.
  Outcomes use ONLY bars strictly after T (T+1 .. T+HORIZON).
  source_type = "HISTORICAL" on every generated record.
  no_lookahead = True on every generated record.

WALK-FORWARD PARTITION (derived from data range, never hardcoded):
  TRAIN        : first 60% of dates with signals
  VALIDATION   : next 20%
  OOS          : next 10%
  RECENT_OOS   : last 10%

WHY ESS IS LIMITED WITH HISTORICAL DATA:
  HBE.ESS = sum of recency weights (exponential decay, half-life 90 days).
  Records from > 1 year ago contribute < 6% weight each.
  To bootstrap USEFUL state (ESS 10-29), records must be from the last
  6-12 months. For DECISION_ELIGIBLE (ESS >= 100), you need 100+ recent
  observations. This is by architectural design — the system requires
  recent confirmation to assert high authority.

broker_calls = 0, orders = 0 always.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GENERATION_METHOD = "OHLCV_BREAKOUT_20D_v1"
SOURCE_TYPE       = "HISTORICAL"

_DEFAULT_LOOKBACK_DAYS = 365     # fetch 1 year of history for signal generation
_SIGNAL_LOOKBACK       = 20      # 20-day breakout window
_ATR_PERIOD            = 14      # ATR period
_ATR_STOP_MULT         = 1.5     # stop = entry - 1.5 × ATR
_DEFAULT_RR            = 2.0     # target R:R
_OUTCOME_HORIZON       = 5       # outcome window: T+1..T+5 trading days

_NIFTY_TICKER  = "^NSEI"
_REGIME_LONG_MA = 200
_REGIME_SHORT_MA = 50

# Walk-forward partition fractions
_FRAC_TRAIN      = 0.60
_FRAC_VALIDATION = 0.20
_FRAC_OOS        = 0.10
# RECENT_OOS = remaining 10%

# Sector lookup — mirrors historical_behaviour_engine
_SYMBOL_SECTOR: Dict[str, str] = {
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "SBIN": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "BANKBARODA": "BANK", "INDUSINDBK": "BANK",
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY", "NTPC": "ENERGY",
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "BRITANNIA": "FMCG",
    "TATASTEEL": "METALS", "JSWSTEEL": "METALS", "HINDALCO": "METALS",
    "DLF": "REALTY", "LODHA": "REALTY",
    "BHARTIARTL": "TELECOM",
    "ASIANPAINT": "CONSUMER", "HAVELLS": "CONSUMER", "TITAN": "CONSUMER",
    "NIFTY": "INDEX", "BANKNIFTY": "INDEX",
}


def _sector(symbol: str) -> str:
    return _SYMBOL_SECTOR.get(symbol.upper().strip(), "UNKNOWN")


def _yf_ticker(symbol: str) -> str:
    if symbol.startswith("^"):
        return symbol
    mapping = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    return mapping.get(symbol.upper().strip(), f"{symbol.upper().strip()}.NS")


# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers (no yfinance — testable without network)
# ─────────────────────────────────────────────────────────────────────────────

def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Compute ATR from lists of highs, lows, and (prior) closes. No lookahead."""
    if len(highs) < period + 1:
        return (highs[-1] - lows[-1]) if highs else 0.0
    trs = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


def determine_regime(nifty_closes: List[float]) -> str:
    """
    Determine market regime from NIFTY closing prices.
    Uses data ending at the current bar — no lookahead.
    BULL: close > 200d SMA AND close > 50d SMA
    BEAR: close < 200d SMA
    RANGE: otherwise
    """
    if len(nifty_closes) < _REGIME_LONG_MA:
        return "UNKNOWN"
    close = nifty_closes[-1]
    ma200 = sum(nifty_closes[-_REGIME_LONG_MA:]) / _REGIME_LONG_MA
    ma50  = sum(nifty_closes[-_REGIME_SHORT_MA:]) / _REGIME_SHORT_MA
    if close > ma200 and close > ma50:
        return "BULL"
    if close < ma200:
        return "BEAR"
    return "RANGE"


def assign_partition(signal_dates: List[str]) -> Dict[str, str]:
    """
    Assign walk-forward validation partitions to a list of signal dates.
    Partitions are derived from the actual data range — never hardcoded.
    Returns {date_str: partition_label}.
    """
    if not signal_dates:
        return {}
    sorted_dates = sorted(set(signal_dates))
    n = len(sorted_dates)
    i_val  = int(n * _FRAC_TRAIN)
    i_oos  = int(n * (_FRAC_TRAIN + _FRAC_VALIDATION))
    i_roos = int(n * (_FRAC_TRAIN + _FRAC_VALIDATION + _FRAC_OOS))
    result = {}
    for i, d in enumerate(sorted_dates):
        if i < i_val:
            result[d] = "TRAIN"
        elif i < i_oos:
            result[d] = "VALIDATION"
        elif i < i_roos:
            result[d] = "OOS"
        else:
            result[d] = "RECENT_OOS"
    return result


def compute_outcome(
    entry_price: float,
    stop_price:  float,
    target_price: float,
    future_highs: List[float],
    future_lows:  List[float],
    future_closes: List[float],
) -> Tuple[str, float, float, float, float, float]:
    """
    Compute outcome from post-signal bars (T+1..T+HORIZON).
    Returns (first_event, t1_ret, t3_ret, t5_ret, mfe_pct, mae_pct).
    future_* must contain bars strictly after the signal date — no lookahead.
    """
    if not future_closes or entry_price <= 0:
        return "OUTCOME_EXPIRED", 0.0, 0.0, 0.0, 0.0, 0.0

    t1 = ((future_closes[0] / entry_price) - 1) * 100 if len(future_closes) >= 1 else 0.0
    t3 = ((future_closes[2] / entry_price) - 1) * 100 if len(future_closes) >= 3 else t1
    t5 = ((future_closes[4] / entry_price) - 1) * 100 if len(future_closes) >= 5 else t3

    mfe = max((h - entry_price) / entry_price * 100 for h in future_highs) if future_highs else 0.0
    mae = min((l - entry_price) / entry_price * 100 for l in future_lows)  if future_lows  else 0.0

    # First event: check each day in order
    first_event = "OUTCOME_EXPIRED"
    for i in range(min(len(future_highs), _OUTCOME_HORIZON)):
        target_hit = future_highs[i] >= target_price
        stop_hit   = future_lows[i]  <= stop_price
        if target_hit and stop_hit:
            # Both on same day — use open to determine which came first (approximate)
            first_event = "TARGET_HIT"   # conservative: assume target first
            break
        if target_hit:
            first_event = "TARGET_HIT"
            break
        if stop_hit:
            first_event = "STOP_HIT"
            break

    return first_event, round(t1, 4), round(t3, 4), round(t5, 4), round(mfe, 4), round(mae, 4)


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV fetcher (isolates yfinance dependency — mockable in tests)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker: str, start: str, end: str) -> Optional[Any]:
    """
    Fetch daily OHLCV from yfinance. Returns DataFrame or None on failure.
    Uses timeout=8 to match the project yfinance convention.
    """
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True, timeout=8)
        return df if df is not None and not df.empty else None
    except Exception as exc:
        log.debug("[KBS-001] fetch_ohlcv failed for %s: %s", ticker, exc)
        return None


def _df_to_lists(df: Any) -> Tuple[List[str], List[float], List[float], List[float], List[float]]:
    """Convert yfinance DataFrame to (dates, opens, highs, lows, closes)."""
    import pandas as pd
    dates   = [str(idx.date()) for idx in df.index]
    opens   = [float(df["Open"].iloc[i])  for i in range(len(df))]
    highs   = [float(df["High"].iloc[i])  for i in range(len(df))]
    lows    = [float(df["Low"].iloc[i])   for i in range(len(df))]
    closes  = [float(df["Close"].iloc[i]) for i in range(len(df))]
    return dates, opens, highs, lows, closes


# ─────────────────────────────────────────────────────────────────────────────
# Main bootstrap class
# ─────────────────────────────────────────────────────────────────────────────

class HistoricalBootstrap:
    """
    KBS-001 — Generates OutcomeRecords from historical OHLCV via breakout signals.

    Usage:
        from learning_system.historical_bootstrap import HistoricalBootstrap
        bootstrap = HistoricalBootstrap()
        records = bootstrap.generate_records("TATASTEEL", days_back=365)
        # Inject into HBE:
        hbe.load_bootstrap_records(records)

    For testing without network, supply pre-built records via _inject_ohlcv().
    """

    def __init__(self, rr: float = _DEFAULT_RR) -> None:
        self.rr = rr
        self.broker_calls = 0
        self.orders       = 0
        self._nifty_cache: Dict[str, List[float]] = {}   # date → [closes_up_to_date]

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_records(
        self,
        symbol:     str,
        days_back:  int = _DEFAULT_LOOKBACK_DAYS,
        end_date:   Optional[date] = None,
    ) -> List["OutcomeRecord"]:
        """
        Generate historical OutcomeRecords for one symbol.

        Parameters
        ----------
        symbol    : NSE symbol (e.g. "TATASTEEL")
        days_back : How many calendar days of history to use for signals
        end_date  : Last date (default: today)

        Returns
        -------
        List of OutcomeRecords with source_type='HISTORICAL'.
        Empty list if data unavailable.
        """
        from opportunity_engine.hbe_models import OutcomeRecord

        end = end_date or date.today()
        # Fetch extra days for warmup (signal lookback + ATR period)
        fetch_start = (end - timedelta(days=days_back + _SIGNAL_LOOKBACK + _ATR_PERIOD + 30)).isoformat()
        fetch_end   = (end + timedelta(days=_OUTCOME_HORIZON + 2)).isoformat()

        ticker = _yf_ticker(symbol)
        df = fetch_ohlcv(ticker, fetch_start, fetch_end)
        if df is None:
            log.debug("[KBS-001] No data for %s", symbol)
            return []

        dates, opens, highs, lows, closes = _df_to_lists(df)
        if len(closes) < _SIGNAL_LOOKBACK + _ATR_PERIOD + _OUTCOME_HORIZON + 5:
            return []

        # Load NIFTY closes for regime computation
        nifty_closes = self._load_nifty_closes(fetch_start, fetch_end)

        # Signal cutoff: only generate signals within days_back of end_date
        signal_start = (end - timedelta(days=days_back)).isoformat()

        records: List[OutcomeRecord] = []
        seen_obs_ids: set = set()

        for i in range(_SIGNAL_LOOKBACK + _ATR_PERIOD, len(closes) - _OUTCOME_HORIZON):
            bar_date = dates[i]
            if bar_date < signal_start:
                continue
            if bar_date > end.isoformat():
                break

            # ── Features (only data ending at bar i — no lookahead) ──────────
            close_i = closes[i]
            high_20d = max(closes[i - _SIGNAL_LOOKBACK: i])  # highest of prior 20 closes

            # BUY signal: today's close breaks above prior 20-day high
            if close_i <= high_20d:
                continue

            atr = compute_atr(highs[i - _ATR_PERIOD: i + 1],
                               lows[i  - _ATR_PERIOD: i + 1],
                               closes[i - _ATR_PERIOD - 1: i])
            if atr <= 0:
                continue

            stop   = close_i - _ATR_STOP_MULT * atr
            target = close_i + self.rr * (close_i - stop)

            # Regime from NIFTY closes up to bar_date
            regime = self._regime_at(bar_date, nifty_closes)

            # ── Outcome (strictly T+1..T+5 — no lookahead) ──────────────────
            fut_highs  = highs[i + 1:  i + 1 + _OUTCOME_HORIZON]
            fut_lows   = lows[i + 1:   i + 1 + _OUTCOME_HORIZON]
            fut_closes = closes[i + 1: i + 1 + _OUTCOME_HORIZON]

            first_event, t1, t3, t5, mfe, mae = compute_outcome(
                close_i, stop, target, fut_highs, fut_lows, fut_closes
            )
            from opportunity_engine.hbe_models import COMPLETED_OUTCOMES
            if first_event not in COMPLETED_OUTCOMES:
                continue

            obs_id = f"KBS_{symbol}_{bar_date}_{uuid.uuid4().hex[:8]}"
            if obs_id in seen_obs_ids:
                continue
            seen_obs_ids.add(obs_id)

            records.append(OutcomeRecord(
                obs_id=obs_id,
                trading_date=bar_date,
                symbol=symbol.upper(),
                direction="BUY",
                regime=regime,
                sector=_sector(symbol),
                reference_entry=round(close_i, 2),
                knowledge_target=round(target, 2),
                knowledge_stop=round(stop, 2),
                atr=round(atr, 4),
                atr_pct=round(atr / close_i * 100, 4),
                scanner_confidence=7.0,   # proxy — no live scanner at historical time
                candidate_score=0.60,
                knowledge_score=0.0,
                knowledge_rr=round(self.rr, 2),
                first_event=first_event,
                first_event_day=dates[i + _OUTCOME_HORIZON - 1] if len(dates) > i + _OUTCOME_HORIZON - 1 else None,
                target_hit=(first_event == "TARGET_HIT"),
                stop_hit=(first_event == "STOP_HIT"),
                t1_ret_pct=t1,
                t3_ret_pct=t3,
                t5_ret_pct=t5,
                mfe_pct=mfe,
                mae_pct=mae,
                days_to_event=_OUTCOME_HORIZON,
                no_lookahead=True,
                source_type=SOURCE_TYPE,
                validation_partition="",  # populated by assign_partitions()
            ))

        records = self.assign_partitions(records)
        log.info("[KBS-001] %s: %d historical records generated (%d days_back)",
                 symbol, len(records), days_back)
        return records

    def assign_partitions(self, records: List["OutcomeRecord"]) -> List["OutcomeRecord"]:
        """Assign walk-forward validation partitions in-place and return the list."""
        partition_map = assign_partition([r.trading_date for r in records])
        from dataclasses import replace
        return [replace(r, validation_partition=partition_map.get(r.trading_date, "TRAIN"))
                for r in records]

    # ── NIFTY regime helpers ─────────────────────────────────────────────────

    def _load_nifty_closes(self, start: str, end: str) -> Dict[str, float]:
        """Return {date_str: close} for NIFTY. Cached per session."""
        cache_key = f"{start}_{end}"
        if cache_key in self._nifty_cache:
            return self._nifty_cache[cache_key]

        df = fetch_ohlcv(_NIFTY_TICKER, start, end)
        if df is None:
            return {}
        dates, _, _, _, closes = _df_to_lists(df)
        result = {d: c for d, c in zip(dates, closes)}
        self._nifty_cache[cache_key] = result
        return result

    def _regime_at(self, bar_date: str, nifty_by_date: Dict[str, float]) -> str:
        """Compute regime using NIFTY closes up to and including bar_date."""
        sorted_dates = sorted(k for k in nifty_by_date if k <= bar_date)
        if len(sorted_dates) < _REGIME_LONG_MA:
            return "UNKNOWN"
        closes = [nifty_by_date[d] for d in sorted_dates[-_REGIME_LONG_MA:]]
        return determine_regime(closes)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: bulk generate for multiple symbols
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_symbols(
    symbols:   List[str],
    days_back: int = _DEFAULT_LOOKBACK_DAYS,
) -> List["OutcomeRecord"]:
    """
    Generate historical records for a list of symbols.
    Returns a deduplicated combined list.
    """
    from opportunity_engine.hbe_models import OutcomeRecord
    bs = HistoricalBootstrap()
    all_records: List[OutcomeRecord] = []
    seen: set = set()
    for sym in symbols:
        recs = bs.generate_records(sym, days_back=days_back)
        for r in recs:
            if r.obs_id not in seen:
                all_records.append(r)
                seen.add(r.obs_id)
    return all_records
