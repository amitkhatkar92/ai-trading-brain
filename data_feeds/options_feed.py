"""
NSE Options Chain Feed
======================
Primary: yfinance live options chain (NIFTY, BANKNIFTY).
Fallback: Black-Scholes synthetic chain when live data unavailable.

Features:
 • 5-minute cache (options chains are stable within a 5-min window)
 • Greeks computed via Black-Scholes (delta, gamma, theta/day, vega/1%)
 • IV Rank (0–100) maintained via rolling 252-day history
 • Automatic spot price fetching per instrument
 • Clean dataclasses — no pandas dependency for consumers
"""

from __future__ import annotations

import math
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# ── NSE lot sizes — check NSE circulars periodically ──────────────────────
NSE_LOT_SIZES: Dict[str, int] = {
    "NIFTY":       75,
    "BANKNIFTY":   15,
    "FINNIFTY":    65,
    "MIDCPNIFTY":  75,
    "SENSEX":      10,
    "BANKEX":      15,
}

# NSE strike-price intervals per instrument
NSE_STRIKE_INTERVALS: Dict[str, float] = {
    "NIFTY":       50.0,
    "BANKNIFTY":  100.0,
    "FINNIFTY":    50.0,
    "MIDCPNIFTY":  25.0,
    "SENSEX":     100.0,
}

# yfinance ticker symbols for spot price
_SPOT_TICKER: Dict[str, str] = {
    "NIFTY":      "^NSEI",
    "BANKNIFTY":  "^NSEBANK",
    "FINNIFTY":   "NIFTY_FIN_SERVICE.NS",
}

# Approximate Indian risk-free rate (RBI repo rate)
_RISK_FREE = 0.065   # 6.5 %

# Cache TTL in seconds
_CACHE_TTL = 300     # 5 minutes

# How many strikes on each side of ATM to include in chain
_STRIKES_EACH_SIDE = 10

# Minimum premium — ignore deeply OTM contracts
_MIN_PREMIUM = 0.50

# Minimum live OI to consider a contract tradable
MIN_TRADABLE_OI = 500


# ── Data models ────────────────────────────────────────────────────────────

@dataclass
class OptionContract:
    """One row of an options chain (single leg)."""
    strike:        float
    expiry:        date
    option_type:   str    # "CE" | "PE"
    premium:       float  # mid-price (bid+ask)/2 or last price
    bid:           float
    ask:           float
    iv:            float  # implied vol, annualised decimal (0.18 = 18 %)
    delta:         float  # –1 → +1
    gamma:         float
    theta:         float  # per-day theta decay (negative for long)
    vega:          float  # for 1 % IV move
    open_interest: int
    volume:        int
    is_live:       bool   # False when constructed from Black-Scholes


@dataclass
class OptionsChain:
    """Full snapshot of an expiry chain for one instrument."""
    symbol:     str
    spot:       float
    expiry:     date
    dte:        int            # calendar days to expiry
    calls:      List[OptionContract] = field(default_factory=list)
    puts:       List[OptionContract] = field(default_factory=list)
    atm_iv:     float = 0.0   # average IV of the two nearest ATM strikes
    iv_rank:    float = 50.0  # 0–100 percentile vs rolling 252-day window
    is_live:    bool  = False  # True if data came from live chain
    fetched_at: datetime = field(default_factory=datetime.now)

    # ── Convenience accessors ──────────────────────────────────────────

    def atm_strike(self) -> float:
        """Round spot to nearest strike interval."""
        interval = NSE_STRIKE_INTERVALS.get(self.symbol, 50.0)
        return round(self.spot / interval) * interval

    def atm_call(self) -> Optional[OptionContract]:
        if not self.calls:
            return None
        return min(self.calls, key=lambda c: abs(c.strike - self.spot))

    def atm_put(self) -> Optional[OptionContract]:
        if not self.puts:
            return None
        return min(self.puts, key=lambda p: abs(p.strike - self.spot))

    def otm_calls_above(self, above_strike: float, n: int = 1) -> List[OptionContract]:
        """OTM calls with strike strictly above *above_strike*, sorted ascending."""
        return sorted(
            [c for c in self.calls if c.strike > above_strike],
            key=lambda c: c.strike,
        )[:n]

    def otm_puts_below(self, below_strike: float, n: int = 1) -> List[OptionContract]:
        """OTM puts with strike strictly below *below_strike*, sorted descending."""
        return sorted(
            [p for p in self.puts if p.strike < below_strike],
            key=lambda p: p.strike,
            reverse=True,
        )[:n]


# ── Black-Scholes engine ───────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    """Cumulative distribution function of the standard normal."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    """Probability density function of the standard normal."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs_greeks(
    S: float, K: float, T: float, r: float, sigma: float, is_call: bool
) -> Dict[str, float]:
    """
    Black-Scholes price and first-order Greeks.

    Parameters
    ----------
    S       : spot price
    K       : strike price
    T       : years to expiry  (dte / 365)
    r       : continuous risk-free rate
    sigma   : annualised implied volatility (decimal)
    is_call : True → call, False → put

    Returns dict: price, delta, gamma, theta (per day), vega (per 1 % IV).
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"price": 0.0, "delta": 0.0 if is_call else -1.0,
                "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    sqrt_T = math.sqrt(T)
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    except (ValueError, ZeroDivisionError):
        return {"price": 0.0, "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d2      = d1 - sigma * sqrt_T
    n_d1    = _norm_pdf(d1)
    disc    = math.exp(-r * T)
    gamma   = n_d1 / (S * sigma * sqrt_T)
    vega    = S * n_d1 * sqrt_T / 100.0   # per 1 % IV change

    if is_call:
        price = S * _norm_cdf(d1) - K * disc * _norm_cdf(d2)
        delta = _norm_cdf(d1)
        theta = (-(S * n_d1 * sigma) / (2 * sqrt_T)
                 - r * K * disc * _norm_cdf(d2)) / 365.0
    else:
        price = K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1.0
        theta = (-(S * n_d1 * sigma) / (2 * sqrt_T)
                 + r * K * disc * _norm_cdf(-d2)) / 365.0

    return {
        "price": round(max(price, _MIN_PREMIUM), 2),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega":  round(vega, 4),
    }


# ── Core feed class ────────────────────────────────────────────────────────

class OptionsFeed:
    """
    NSE Options Chain data provider.

    Usage
    -----
    chain = get_options_feed().get_chain("NIFTY", dte_target=20)
    """

    def __init__(self) -> None:
        self._cache:      Dict[str, Tuple[float, OptionsChain]] = {}
        self._iv_history: Dict[str, List[Tuple[date, float]]]   = {}
        self._lock = threading.Lock()

        # Background refresh thread — keeps chain cache warm between cycles.
        # Options scan cold-start costs ~1.5s/symbol; with cycle gaps of 10–90 min
        # the 5-min TTL always expires, so every cycle was a fresh fetch.
        # This thread refreshes every 270s so cache is always < 30s stale.
        _t = threading.Thread(target=self._warm_loop, daemon=True, name="OptionsFeed-warm")
        _t.start()

    def _warm_loop(self) -> None:
        """Continuous background refresh loop for OPTIONS_SYMBOLS."""
        import time as _time
        from opportunity_engine.options_opportunity_ai import OPTIONS_SYMBOLS as _SYMS
        first = True
        while True:
            for sym in _SYMS:
                try:
                    chain = self._fetch_live(sym, dte_target=20)
                    if chain is None:
                        chain = self._build_synthetic(sym, dte_target=20)
                    if chain:
                        if chain.atm_iv > 0:
                            self._update_iv_history(sym, chain.atm_iv)
                        chain.iv_rank = self._compute_iv_rank(sym, chain.atm_iv)
                        with self._lock:
                            self._cache[f"{sym}_20"] = (_time.time(), chain)
                        if first:
                            log.info(
                                "[OptionsFeed] Cache pre-warmed %s  DTE=%d  spot=%.0f  IVR=%.0f",
                                sym, chain.dte, chain.spot, chain.iv_rank,
                            )
                        else:
                            log.debug(
                                "[OptionsFeed] Background refresh %s  DTE=%d  spot=%.0f  IVR=%.0f",
                                sym, chain.dte, chain.spot, chain.iv_rank,
                            )
                except Exception as exc:
                    log.warning(
                        "[OptionsFeed] Background refresh failed for %s: %s — keeping previous cache",
                        sym, exc,
                    )
            first = False
            _time.sleep(max(60, _CACHE_TTL - 30))  # refresh every 270s

    # ── Public API ─────────────────────────────────────────────────────

    def get_chain(self, symbol: str, dte_target: int = 20) -> Optional[OptionsChain]:
        """
        Return the options chain nearest to *dte_target* calendar days.
        Result is cached for 5 minutes. Falls back to synthetic if live unavailable.
        """
        key = f"{symbol}_{dte_target}"
        with self._lock:
            cached = self._cache.get(key)
            if cached and (time.time() - cached[0]) < _CACHE_TTL:
                return cached[1]

        chain = self._fetch_live(symbol, dte_target)
        if chain is None:
            chain = self._build_synthetic(symbol, dte_target)

        if chain:
            if chain.atm_iv > 0:
                self._update_iv_history(symbol, chain.atm_iv)
            chain.iv_rank = self._compute_iv_rank(symbol, chain.atm_iv)
            with self._lock:
                self._cache[key] = (time.time(), chain)

        return chain

    def get_spot(self, symbol: str) -> float:
        """Fetch current spot price; returns 0.0 on failure."""
        try:
            import yfinance as yf
            ticker_sym = _SPOT_TICKER.get(symbol)
            if not ticker_sym:
                return 0.0
            info = yf.Ticker(ticker_sym).fast_info
            price = float(info.get("last_price") or info.get("previousClose") or 0)
            return price
        except Exception as exc:
            log.debug("[OptionsFeed] get_spot(%s) failed: %s", symbol, exc)
            return 0.0

    def get_lot_size(self, symbol: str) -> int:
        return NSE_LOT_SIZES.get(symbol, 75)

    def get_iv_rank(self, symbol: str) -> float:
        """Return current IV Rank 0–100 using rolling 252-day history."""
        chain = self._cache.get(f"{symbol}_20")
        if chain:
            return chain[1].iv_rank
        return 50.0   # neutral when no history

    def chain_quality_score(self, chain: "OptionsChain") -> Tuple[float, List[str]]:
        """
        Score the quality of a live NSE options chain on a 0.0–1.0 scale.

        Returns (score, issues) where issues is a list of strings describing
        detected problems.  A score < 0.5 means the chain is unreliable for
        live trading decisions.

        Checks:
          1. Minimum tradable strikes per side (OI > MIN_TRADABLE_OI, bid > 0)
          2. Bid-ask spread tightness (wide spread = illiquid / stale)
          3. ATM proximity — at least 2 tradable strikes within ATM ± 2 intervals
             must exist on each side (catches far-OTM-only liquid chains)
          4. Synthetic flag (immediately returns 0.0 for non-live chains)
        """
        issues: List[str] = []
        if not chain.is_live:
            return 0.0, ["synthetic chain — Black-Scholes, not market data"]

        MIN_STRIKES    = 5      # need at least 5 tradable strikes each side
        MAX_SPREAD_PCT = 0.30   # bid-ask spread > 30% of mid → illiquid
        ATM_MIN_NEAR   = 2      # need ≥ 2 tradable strikes within ATM ± 2 intervals

        def _tradable(contracts: List) -> Tuple[int, float]:
            """Return (count_with_oi, avg_spread_pct)."""
            tradable = [c for c in contracts
                        if c.open_interest >= MIN_TRADABLE_OI and c.bid > 0]
            if not tradable:
                return 0, 1.0
            spreads = []
            for c in tradable:
                mid = (c.bid + c.ask) / 2.0 if c.ask > 0 else c.premium
                if mid > 0:
                    spreads.append((c.ask - c.bid) / mid)
            avg_spread = sum(spreads) / len(spreads) if spreads else 1.0
            return len(tradable), avg_spread

        call_count, call_spread = _tradable(chain.calls)
        put_count,  put_spread  = _tradable(chain.puts)

        score = 1.0

        # Penalty for too few tradable strikes
        if call_count < MIN_STRIKES:
            issues.append(
                f"calls: only {call_count} tradable strikes (need {MIN_STRIKES})"
            )
            score -= 0.35
        if put_count < MIN_STRIKES:
            issues.append(
                f"puts: only {put_count} tradable strikes (need {MIN_STRIKES})"
            )
            score -= 0.35

        # Penalty for wide bid-ask spread
        avg_spread = (call_spread + put_spread) / 2.0
        if avg_spread > MAX_SPREAD_PCT:
            issues.append(
                f"avg bid-ask spread {avg_spread:.0%} > {MAX_SPREAD_PCT:.0%} (illiquid)"
            )
            score -= 0.30

        # ── ATM proximity check ────────────────────────────────────────
        # Validates that the liquid strikes are near ATM, not only far OTM.
        # A chain where only deep OTM strikes are liquid is useless for
        # spread construction (ATM legs would have no fill).
        spot     = chain.spot
        interval = NSE_STRIKE_INTERVALS.get(chain.symbol, 50.0)
        atm_band = interval * 2.0   # ± 2 strike intervals from ATM

        near_calls = [
            c for c in chain.calls
            if c.open_interest >= MIN_TRADABLE_OI
            and c.bid > 0
            and abs(c.strike - spot) <= atm_band
        ]
        near_puts = [
            c for c in chain.puts
            if c.open_interest >= MIN_TRADABLE_OI
            and c.bid > 0
            and abs(c.strike - spot) <= atm_band
        ]

        if len(near_calls) < ATM_MIN_NEAR:
            issues.append(
                f"calls: only {len(near_calls)} tradable ATM-near strikes "
                f"(need {ATM_MIN_NEAR} within ±{atm_band:.0f} of spot={spot:.0f})"
            )
            score -= 0.25
        if len(near_puts) < ATM_MIN_NEAR:
            issues.append(
                f"puts: only {len(near_puts)} tradable ATM-near strikes "
                f"(need {ATM_MIN_NEAR} within ±{atm_band:.0f} of spot={spot:.0f})"
            )
            score -= 0.25

        score = round(max(0.0, min(1.0, score)), 2)
        return score, issues

    # ── Private: live fetch ────────────────────────────────────────────

    def _fetch_live(self, symbol: str, dte_target: int) -> Optional[OptionsChain]:
        # ── Path 1: AngelOne live options chain (primary — TOTP auto-refresh) ──
        # AngelOne SmartAPI provides live LTP + bid/ask for NFO contracts.
        # No daily manual token required — TOTP rotates automatically.
        # Do NOT gate on is_live: get_options_chain() calls _refresh_if_needed()
        # internally and will auto-reconnect expired sessions.
        try:
            from data_feeds.data_feed_manager import get_feed_manager as _gfm_ao
            _ao = getattr(_gfm_ao(), "angelone", None)
            if _ao is not None:
                _base_ao = _ao.get_options_chain(symbol, dte_target=dte_target)
                if _base_ao is not None and getattr(_base_ao, "contracts", None):
                    # ── P1A: sync raw chain back to DataFeedManager._options_chain_state ──
                    # The warm loop calls AngelOneFeed directly and never touches
                    # _options_chain_state, so fetched_at was frozen at first-cycle time.
                    # Writing here keeps get_cached_pcr() age < 300s after every refresh.
                    try:
                        _gfm_ao()._options_chain_state[symbol.upper()] = {
                            "chain":      _base_ao,
                            "fetched_at": datetime.now(),
                            "source":     "ANGELONE",
                            "is_live":    True,
                        }
                    except Exception:
                        pass
                    _spot     = float(_base_ao.spot_price)
                    _exp_str  = _base_ao.expiry          # DDMMMYY e.g. "02JUN26"
                    try:
                        _expiry_dt = datetime.strptime(_exp_str, "%d%b%y").date()
                    except ValueError:
                        try:
                            _expiry_dt = datetime.strptime(_exp_str[:10], "%Y-%m-%d").date()
                        except ValueError:
                            _expiry_dt = date.today()
                    _dte      = max((_expiry_dt - date.today()).days, 0)
                    _T        = max(_dte, 1) / 365.0
                    _interval = NSE_STRIKE_INTERVALS.get(symbol, 50.0)
                    _calls_ao: List[OptionContract] = []
                    _puts_ao:  List[OptionContract] = []
                    for _c in _base_ao.contracts:
                        if not _c.ltp or _c.ltp < _MIN_PREMIUM:
                            continue
                        # AngelOne does not return IV — use BS with 16% seed
                        _iv = 0.16
                        _g  = bs_greeks(_spot, _c.strike, _T, _RISK_FREE, _iv, _c.is_call)
                        _contract = OptionContract(
                            strike=_c.strike, expiry=_expiry_dt,
                            option_type=_c.option_type, premium=_c.ltp,
                            bid=getattr(_c, "bid", 0.0), ask=getattr(_c, "ask", 0.0),
                            iv=_iv,
                            delta=_g.get("delta", 0), gamma=_g.get("gamma", 0),
                            theta=_g.get("theta", 0), vega=_g.get("vega", 0),
                            open_interest=int(getattr(_c, "oi", 0) or 0),
                            volume=int(getattr(_c, "volume", 0) or 0),
                            is_live=True,
                        )
                        if _c.is_call:
                            _calls_ao.append(_contract)
                        else:
                            _puts_ao.append(_contract)
                    if _calls_ao or _puts_ao:
                        _atm_calls_ao = [c for c in _calls_ao
                                         if abs(c.strike - _spot) <= _interval * 1.5]
                        _atm_iv_ao    = (sum(c.iv for c in _atm_calls_ao) / len(_atm_calls_ao)
                                         if _atm_calls_ao else 0.16)
                        _chain_ao = OptionsChain(
                            symbol=symbol, spot=_spot, expiry=_expiry_dt, dte=_dte,
                            calls=_calls_ao, puts=_puts_ao, atm_iv=_atm_iv_ao, is_live=True,
                        )
                        log.info(
                            "[OptionsFeed] AngelOne live chain %s  DTE=%d  spot=%.0f  "
                            "ATM-IV=%.1f%%  strikes=%d",
                            symbol, _dte, _spot, _atm_iv_ao * 100,
                            len(_calls_ao) + len(_puts_ao),
                        )
                        log.info(
                            "[ExpirySelectionResult] source=ANGELONE  symbol=%s  "
                            "live_chain=True  expiry=%s  dte=%d",
                            symbol, _expiry_dt, _dte,
                        )
                        return _chain_ao
        except Exception as _ao_exc:
            log.debug("[OptionsFeed] AngelOne chain unavailable for %s: %s", symbol, _ao_exc)

        # ── Path 1.5: Dhan live options chain (fallback — requires daily token) ─
        # Dhan option_chain() is a trading-API call (not a data subscription),
        # so it may work even when the OHLC data feed returns 451.
        try:
            from data_feeds.data_feed_manager import get_feed_manager
            _fm = get_feed_manager()
            _dhan = getattr(_fm, "dhan", None)
            if _dhan is not None:
                _base_chain = _dhan.get_options_chain(symbol, dte_target=dte_target)
                if _base_chain is not None and getattr(_base_chain, "contracts", None):
                    # Convert base_feed.OptionsChain → options_feed.OptionsChain
                    _spot     = float(_base_chain.spot_price)
                    _exp_str  = _base_chain.expiry          # "YYYY-MM-DD"
                    _expiry_dt = datetime.strptime(_exp_str, "%Y-%m-%d").date()
                    _dte      = max((_expiry_dt - date.today()).days, 0)
                    _T        = max(_dte, 1) / 365.0
                    _interval = NSE_STRIKE_INTERVALS.get(symbol, 50.0)
                    _calls: List[OptionContract] = []
                    _puts:  List[OptionContract] = []
                    for _c in _base_chain.contracts:
                        if not _c.ltp or _c.ltp < _MIN_PREMIUM:
                            continue
                        # Dhan IV is in percentage (e.g. 16.0 = 16%) — normalise
                        _iv = _c.iv / 100.0 if _c.iv > 1.0 else _c.iv
                        _iv = _iv if 0.01 <= _iv <= 5.0 else 0.16
                        _g  = bs_greeks(_spot, _c.strike, _T, _RISK_FREE, _iv, _c.is_call)
                        _contract = OptionContract(
                            strike=_c.strike, expiry=_expiry_dt,
                            option_type=_c.option_type, premium=_c.ltp,
                            bid=getattr(_c, "bid", 0.0), ask=getattr(_c, "ask", 0.0),
                            iv=_iv,
                            delta=_g.get("delta", 0), gamma=_g.get("gamma", 0),
                            theta=_g.get("theta", 0), vega=_g.get("vega", 0),
                            open_interest=int(getattr(_c, "oi", 0) or 0),
                            volume=int(getattr(_c, "volume", 0) or 0),
                            is_live=True,
                        )
                        if _c.is_call:
                            _calls.append(_contract)
                        else:
                            _puts.append(_contract)
                    if _calls or _puts:
                        # If Dhan returned a near-term expiry (DTE < 7) but the
                        # caller requested a further one (dte_target ≥ 14), fall
                        # through to NSE which honours dte_target.
                        if _dte < 7 and dte_target >= 14:
                            log.debug(
                                "[OptionsFeed] Dhan chain %s DTE=%d is near-term "
                                "but dte_target=%d — falling through to NSE "
                                "for next expiry.",
                                symbol, _dte, dte_target,
                            )
                        else:
                            _atm_calls = [c for c in _calls
                                          if abs(c.strike - _spot) <= _interval * 1.5]
                            _atm_iv    = (sum(c.iv for c in _atm_calls) / len(_atm_calls)
                                          if _atm_calls else 0.16)
                            _chain = OptionsChain(
                                symbol=symbol, spot=_spot, expiry=_expiry_dt, dte=_dte,
                                calls=_calls, puts=_puts, atm_iv=_atm_iv, is_live=True,
                            )
                            log.info(
                                "[OptionsFeed] Dhan live chain %s  DTE=%d  spot=%.0f  "
                                "ATM-IV=%.1f%%  strikes=%d",
                                symbol, _dte, _spot, _atm_iv * 100,
                                len(_calls) + len(_puts),
                            )
                            log.info(
                                "[ExpirySelectionResult] source=DHAN  symbol=%s  "
                                "live_chain=True  expiry=%s  dte=%d",
                                symbol, _expiry_dt, _dte,
                            )
                            return _chain
        except Exception as _dhan_exc:
            log.debug("[OptionsFeed] Dhan chain unavailable for %s: %s", symbol, _dhan_exc)

        # ── Path 2: NSE public API via nsepython ───────────────────────────────
        # nseindia.com/api/option-chain-indices is freely accessible from VPS.
        # Returns real premiums, OI, IV during market hours (09:15–15:30 IST).
        try:
            from data_feeds.data_feed_manager import get_feed_manager as _gfm2
            _nse_feed = getattr(_gfm2(), "nse", None)
            if _nse_feed is not None and getattr(_nse_feed, "_mode", "") == "nsepython":
                _base = _nse_feed.get_options_chain(symbol)
                if _base is not None and getattr(_base, "is_live", False) and getattr(_base, "contracts", None):
                    _spot     = float(_base.spot_price)
                    _exp_str  = _base.expiry
                    try:
                        _expiry_dt = datetime.strptime(_exp_str, "%Y-%m-%d").date()
                    except Exception:
                        _expiry_dt = datetime.strptime(_exp_str, "%d-%b-%Y").date()
                    _dte      = max((_expiry_dt - date.today()).days, 0)
                    _T        = max(_dte, 1) / 365.0
                    _interval = NSE_STRIKE_INTERVALS.get(symbol, 50.0)
                    _calls: List[OptionContract] = []
                    _puts:  List[OptionContract] = []
                    for _c in _base.contracts:
                        if not _c.ltp or _c.ltp < _MIN_PREMIUM:
                            continue
                        _iv = _c.iv / 100.0 if _c.iv > 1.0 else _c.iv
                        _iv = _iv if 0.01 <= _iv <= 5.0 else 0.16
                        _g  = bs_greeks(_spot, _c.strike, _T, _RISK_FREE, _iv,
                                        _c.option_type == "CE")
                        _contract = OptionContract(
                            strike=_c.strike, expiry=_expiry_dt,
                            option_type=_c.option_type, premium=_c.ltp,
                            bid=getattr(_c, "bid", 0.0), ask=getattr(_c, "ask", 0.0),
                            iv=_iv,
                            delta=_g.get("delta", 0), gamma=_g.get("gamma", 0),
                            theta=_g.get("theta", 0), vega=_g.get("vega", 0),
                            open_interest=int(getattr(_c, "oi", 0) or 0),
                            volume=int(getattr(_c, "volume", 0) or 0),
                            is_live=True,
                        )
                        if _c.option_type == "CE":
                            _calls.append(_contract)
                        else:
                            _puts.append(_contract)
                    if _calls or _puts:
                        _atm_calls = [c for c in _calls
                                      if abs(c.strike - _spot) <= _interval * 1.5]
                        _atm_iv    = (sum(c.iv for c in _atm_calls) / len(_atm_calls)
                                      if _atm_calls else 0.16)
                        _chain = OptionsChain(
                            symbol=symbol, spot=_spot, expiry=_expiry_dt, dte=_dte,
                            calls=_calls, puts=_puts, atm_iv=_atm_iv, is_live=True,
                        )
                        log.info(
                            "[OptionsFeed] NSE live chain %s  DTE=%d  spot=%.0f  "
                            "ATM-IV=%.1f%%  strikes=%d",
                            symbol, _dte, _spot, _atm_iv * 100,
                            len(_calls) + len(_puts),
                        )
                        return _chain
                    else:
                        log.warning(
                            "[OptionsFeed] NSE chain %s: %d raw contracts, 0 passed "
                            "premium/type filter (spot=%.0f, MIN_PREMIUM=%.2f) — "
                            "first contract: ltp=%.2f iv=%.2f",
                            symbol, len(_base.contracts), _spot, _MIN_PREMIUM,
                            _base.contracts[0].ltp if _base.contracts else 0,
                            _base.contracts[0].iv  if _base.contracts else 0,
                        )
                else:
                    # _base is None, is_live=False, or contracts empty
                    log.warning(
                        "[OptionsFeed] NSE chain %s: is_live=%s contracts=%d "
                        "— NSE API unreachable, falling through to synthetic",
                        symbol,
                        getattr(_base, "is_live", "N/A") if _base is not None else "None",
                        len(getattr(_base, "contracts", []) or []) if _base is not None else 0,
                    )
            else:
                log.warning(
                    "[OptionsFeed] NSE feed unavailable for %s (feed=%s mode=%s)",
                    symbol,
                    type(_nse_feed).__name__ if _nse_feed else "None",
                    getattr(_nse_feed, "_mode", "N/A") if _nse_feed else "N/A",
                )
        except Exception as _nse_exc:
            log.warning("[OptionsFeed] NSE chain unavailable for %s: %s", symbol, _nse_exc)

        # ── Path 2: yfinance options chain ────────────────────────────────────
        try:
            import yfinance as yf
            ticker_sym = _SPOT_TICKER.get(symbol)
            if not ticker_sym:
                return None

            tk   = yf.Ticker(ticker_sym)
            info = tk.fast_info
            spot = float(info.get("last_price") or info.get("previousClose") or 0)
            if spot <= 0:
                return None

            expiry_dates = tk.options   # tuple of "YYYY-MM-DD" strings
            if not expiry_dates:
                return None

            today  = date.today()
            # Pick expiry closest to dte_target but >= 3 DTE
            valid  = [d for d in expiry_dates
                      if (datetime.strptime(d, "%Y-%m-%d").date() - today).days >= 3]
            if not valid:
                return None

            best   = min(valid,
                         key=lambda d: abs(
                             (datetime.strptime(d, "%Y-%m-%d").date() - today).days - dte_target
                         ))
            expiry_dt = datetime.strptime(best, "%Y-%m-%d").date()
            dte       = (expiry_dt - today).days

            raw   = tk.option_chain(best)
            T     = max(dte, 1) / 365.0
            calls = self._parse_leg(raw.calls, expiry_dt, "CE", spot, T, True)
            puts  = self._parse_leg(raw.puts,  expiry_dt, "PE", spot, T, False)

            if not calls and not puts:
                return None

            # ATM IV: average IV of strikes within 1 interval of ATM
            interval   = NSE_STRIKE_INTERVALS.get(symbol, 50.0)
            atm_calls  = [c for c in calls if abs(c.strike - spot) <= interval * 1.5]
            atm_iv     = (sum(c.iv for c in atm_calls) / len(atm_calls)
                          if atm_calls else 0.0)

            chain = OptionsChain(
                symbol=symbol, spot=spot, expiry=expiry_dt, dte=dte,
                calls=calls, puts=puts, atm_iv=atm_iv, is_live=True,
            )
            log.info(
                "[OptionsFeed] Live chain %s  DTE=%d  spot=%.0f  ATM-IV=%.1f%%  "
                "strikes=%d",
                symbol, dte, spot, atm_iv * 100, len(calls) + len(puts),
            )
            return chain

        except Exception as exc:
            log.warning("[OptionsFeed] Live fetch failed for %s: %s", symbol, exc)
            return None

    def _parse_leg(
        self,
        df,
        expiry:   date,
        opt_type: str,
        spot:     float,
        T:        float,
        is_call:  bool,
    ) -> List[OptionContract]:
        contracts: List[OptionContract] = []
        try:
            for _, row in df.iterrows():
                strike = float(row.get("strike") or 0)
                if strike <= 0:
                    continue
                bid     = float(row.get("bid") or 0)
                ask     = float(row.get("ask") or 0)
                last    = float(row.get("lastPrice") or 0)
                premium = (bid + ask) / 2.0 if bid > 0 and ask > 0 else last
                if premium < _MIN_PREMIUM:
                    continue
                iv_raw  = float(row.get("impliedVolatility") or 0)
                if iv_raw <= 0 or iv_raw > 5.0:   # sanity: 0 % – 500 %
                    continue
                g = bs_greeks(spot, strike, T, _RISK_FREE, iv_raw, is_call)
                contracts.append(OptionContract(
                    strike=strike, expiry=expiry, option_type=opt_type,
                    premium=round(premium, 2), bid=bid, ask=ask,
                    iv=round(iv_raw, 4),
                    delta=g["delta"], gamma=g["gamma"],
                    theta=g["theta"], vega=g["vega"],
                    open_interest=int(row.get("openInterest") or 0),
                    volume=int(row.get("volume") or 0),
                    is_live=True,
                ))
        except Exception as exc:
            log.debug("[OptionsFeed] _parse_leg error: %s", exc)
        return contracts

    # ── Private: synthetic fallback ────────────────────────────────────

    def _build_synthetic(self, symbol: str, dte_target: int) -> Optional[OptionsChain]:
        """
        Construct a Black-Scholes chain using the last known IV.
        Data quality is lower — signals will be marked as synthetic and
        receive a confidence discount.
        """
        try:
            spot = self.get_spot(symbol)
            if spot <= 0:
                return None

            interval   = NSE_STRIKE_INTERVALS.get(symbol, 50.0)
            atm_strike = round(spot / interval) * interval
            today      = date.today()

            # Target expiry: next Thursday near dte_target
            expiry = today + timedelta(days=dte_target)
            for _ in range(7):                        # find next Thursday
                if expiry.weekday() == 3:
                    break
                expiry += timedelta(days=1)

            dte    = max((expiry - today).days, 3)
            T      = dte / 365.0
            base_iv = self._last_known_iv(symbol) or 0.16   # default 16 %

            def _smile_iv(k: float) -> float:
                """Slight volatility smile for OTM strikes."""
                moneyness = abs(k - spot) / max(spot, 1)
                return base_iv * (1.0 + 0.4 * moneyness)

            calls, puts = [], []
            for i in range(-_STRIKES_EACH_SIDE, _STRIKES_EACH_SIDE + 1):
                k   = atm_strike + i * interval
                iv  = _smile_iv(k)
                g_c = bs_greeks(spot, k, T, _RISK_FREE, iv, True)
                g_p = bs_greeks(spot, k, T, _RISK_FREE, iv, False)
                if g_c["price"] >= _MIN_PREMIUM:
                    calls.append(OptionContract(
                        strike=k, expiry=expiry, option_type="CE",
                        premium=g_c["price"],
                        bid=round(g_c["price"] * 0.98, 2),
                        ask=round(g_c["price"] * 1.02, 2),
                        iv=round(iv, 4),
                        delta=g_c["delta"], gamma=g_c["gamma"],
                        theta=g_c["theta"], vega=g_c["vega"],
                        open_interest=0, volume=0, is_live=False,
                    ))
                if g_p["price"] >= _MIN_PREMIUM:
                    puts.append(OptionContract(
                        strike=k, expiry=expiry, option_type="PE",
                        premium=g_p["price"],
                        bid=round(g_p["price"] * 0.98, 2),
                        ask=round(g_p["price"] * 1.02, 2),
                        iv=round(iv, 4),
                        delta=g_p["delta"], gamma=g_p["gamma"],
                        theta=g_p["theta"], vega=g_p["vega"],
                        open_interest=0, volume=0, is_live=False,
                    ))

            chain = OptionsChain(
                symbol=symbol, spot=spot, expiry=expiry, dte=dte,
                calls=calls, puts=puts, atm_iv=base_iv, is_live=False,
            )
            log.info(
                "[OptionsFeed] Synthetic chain %s  DTE=%d  spot=%.0f  IV=%.1f%% "
                "(no live data)",
                symbol, dte, spot, base_iv * 100,
            )
            return chain

        except Exception as exc:
            log.warning("[OptionsFeed] Synthetic build failed for %s: %s", symbol, exc)
            return None

    # ── Private: IV Rank ───────────────────────────────────────────────

    def _update_iv_history(self, symbol: str, atm_iv: float) -> None:
        today = date.today()
        hist  = self._iv_history.setdefault(symbol, [])
        # Avoid duplicate entries for the same date
        if hist and hist[-1][0] == today:
            hist[-1] = (today, atm_iv)
        else:
            hist.append((today, atm_iv))
        # Keep ~252 trading days
        cutoff = today - timedelta(days=365)
        self._iv_history[symbol] = [(d, v) for d, v in hist if d >= cutoff]

    def _compute_iv_rank(self, symbol: str, current_iv: float) -> float:
        """IV Rank: 100 × (current – 52w_low) / (52w_high – 52w_low)."""
        hist = self._iv_history.get(symbol, [])
        if len(hist) < 10 or current_iv <= 0:
            return 50.0
        vals = [v for _, v in hist]
        lo, hi = min(vals), max(vals)
        if hi <= lo:
            return 50.0
        return round(min((current_iv - lo) / (hi - lo) * 100.0, 100.0), 1)

    def _last_known_iv(self, symbol: str) -> Optional[float]:
        hist = self._iv_history.get(symbol, [])
        return hist[-1][1] if hist else None


# ── Module-level singleton ─────────────────────────────────────────────────

_INSTANCE:  Optional[OptionsFeed] = None
_INST_LOCK: threading.Lock        = threading.Lock()


def get_options_feed() -> OptionsFeed:
    """Return the process-wide OptionsFeed singleton."""
    global _INSTANCE
    with _INST_LOCK:
        if _INSTANCE is None:
            _INSTANCE = OptionsFeed()
    return _INSTANCE
