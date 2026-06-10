"""
MarketDataRouter
================
Unified market-data abstraction layer for all execution-critical pricing.

  BROKER-GRADE DATA FOR MONEY DECISIONS
  PUBLIC DATA FOR CONTEXTUAL INTELLIGENCE

Priority for every Indian equity / index symbol:
  1. Dhan   — authoritative live LTP (broker-grade, zero Yahoo limitations)
  2. Yahoo  — fallback when Dhan unavailable or symbol unknown
  3. LTP cache — last-known-good when BOTH live feeds fail this cycle
  4. FEED_DEGRADED — symbol excluded; SL/adaptive monitoring suppressed

For global / analytics symbols (SP500, VIX, USDINR …):
  Yahoo is primary; Dhan not consulted.

Source attribution is written back onto every TickerQuote:
  quote.feed_source      — "DHAN" | "YAHOO" | "CACHE"
  quote.fallback_active  — True when Dhan failed and another source used
  quote.feed_degraded    — True when no live data; cached LTP served

Divergence detection:
  When Dhan and Yahoo return prices that differ >2% for the same symbol,
  a warning is emitted and the divergence counter increments.
  Both values are preserved (Dhan wins for execution; Yahoo discarded).

Observability:
  router.get_router_stats()      — per-lifetime counters + current-cycle distribution
  router.get_degraded_symbols()  — symbols excluded in last get_live_prices() call
  router.get_source_report()     — human-readable summary for dashboard / Telegram

Singleton:
  from data_feeds.market_data_router import get_market_data_router
  router = get_market_data_router()
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from .base_feed import TickerQuote
from utils import get_logger

log = get_logger(__name__)

# ── Singleton ─────────────────────────────────────────────────────────────
_ROUTER_INSTANCE: Optional["MarketDataRouter"] = None


def get_market_data_router() -> "MarketDataRouter":
    global _ROUTER_INSTANCE
    if _ROUTER_INSTANCE is None:
        _ROUTER_INSTANCE = MarketDataRouter()
    return _ROUTER_INSTANCE


# ── NSE index → Yahoo Finance ticker map ──────────────────────────────────
# Used in the Yahoo fallback path when Dhan is unavailable/doesn't know symbol.
_INDEX_YF_MAP: Dict[str, str] = {
    "NIFTY":       "^NSEI",
    "BANKNIFTY":   "^NSEBANK",
    "FINNIFTY":    "NIFTY_FIN_SERVICE.NS",
    "MIDCAPNIFTY": "^NSEMDCP50",
    "INDIAVIX":    "^INDIAVIX",
    "SENSEX":      "^BSESN",
}

# ── Symbols that are always fetched via Yahoo (global markets, no Dhan) ───
_YAHOO_ONLY: Set[str] = {
    "SP500", "NASDAQ", "DOW", "NIKKEI", "HANGSENG", "SHANGHAI", "KOSPI",
    "USDINR", "DXY", "EURUSD", "GBPUSD",
    "GOLD", "SILVER", "CRUDE_WTI", "CRUDE_BRENT", "NATURAL_GAS",
    "VIX", "US10Y",
}

# Cache staleness limit for live-pricing use-cases (SL / target / MTM)
# A cached price older than this is treated as degraded (not served).
_CACHE_MAX_AGE_SEC: float = 900.0   # 15 min

# Log a warning if Dhan and Yahoo prices differ by more than this fraction
_DIVERGENCE_THRESHOLD: float = 0.02   # 2 %


class MarketDataRouter:
    """
    Dhan-primary, Yahoo-fallback, cache-safety-net routing layer.

    This is the ONLY class that should be called for execution-critical live
    pricing (SL monitoring, target monitoring, MTM, adaptive exits, carry
    expiry pricing, DupGuard exposure).

    Yahoo remains available via DataFeedManager for historical analytics,
    global indices, and regime intelligence — NOT for position governance.
    """

    def __init__(self) -> None:
        # Shares the already-initialised feed instances from DataFeedManager
        from .data_feed_manager import get_feed_manager
        _fm = get_feed_manager()
        self._dhan  = _fm.dhan
        self._yahoo = _fm.yahoo

        # LTP cache: bare_symbol → (ltp, monotonic_ts, source_str)
        self._ltp_cache: Dict[str, Tuple[float, float, str]] = {}

        # ── Lifetime observability counters ───────────────────────────────
        self._dhan_success:     int = 0
        self._dhan_fail:        int = 0
        self._yahoo_success:    int = 0
        self._yahoo_fail:       int = 0
        self._cache_served:     int = 0
        self._degraded_count:   int = 0
        self._divergence_count: int = 0
        self._total_calls:      int = 0

        # ── Per-cycle state (reset by get_live_prices) ────────────────────
        self._last_degraded:      Set[str]        = set()
        self._last_source_dist:   Dict[str, int]  = {}
        self._last_symbol_sources: Dict[str, str] = {}   # sym → DHAN|YAHOO|CACHE|DEGRADED

        log.info(
            "[MarketDataRouter] Initialised.  primary=Dhan(%s)  fallback=Yahoo(%s)",
            "LIVE" if self._dhan.is_live else "SIM",
            "LIVE" if self._yahoo.is_live else "SIM",
        )

    # ── Normalisation ─────────────────────────────────────────────────────

    @staticmethod
    def _bare(symbol: str) -> str:
        """Canonical bare symbol: strip exchange suffixes / leading ^."""
        return symbol.upper().replace(".NS", "").replace(".BO", "").lstrip("^")

    def _to_yahoo_ticker(self, bare: str) -> str:
        """Map a bare Indian symbol to its Yahoo Finance ticker string."""
        from .yahoo_feed import GLOBAL_SYMBOL_MAP
        if bare in _INDEX_YF_MAP:
            return _INDEX_YF_MAP[bare]
        if bare in GLOBAL_SYMBOL_MAP:
            return GLOBAL_SYMBOL_MAP[bare]
        return f"{bare}.NS"    # default NSE equity format

    # ── Main batch interface ───────────────────────────────────────────────

    def get_live_prices(
        self,
        symbols: List[str],
    ) -> Dict[str, TickerQuote]:
        """
        Broker-grade batch price fetch for execution-critical use.

        Accepts any symbol format (bare, .NS, .BO, ^NSEI) — normalised
        internally to bare.  Returns dict keyed by BARE symbol.

        Each returned TickerQuote has provenance metadata set:
          quote.feed_source     — "DHAN" | "YAHOO" | "CACHE"
          quote.fallback_active — True when Dhan missed and Yahoo/cache used
          quote.feed_degraded   — True when no live data; cached LTP served

        After calling this method use get_degraded_symbols() to obtain
        the set of symbols that had neither live data nor a valid cached LTP
        (they were excluded from the returned dict and from monitoring).
        """
        # ── Reset per-cycle state ─────────────────────────────────────────
        self._last_degraded       = set()
        self._last_source_dist    = {}
        self._last_symbol_sources = {}

        bare_symbols = [self._bare(s) for s in symbols]
        self._total_calls += len(bare_symbols)

        # Partition: Indian symbols (may use Dhan) vs global-only (Yahoo only)
        dhan_targets  = [s for s in bare_symbols if s not in _YAHOO_ONLY]
        yahoo_targets = [s for s in bare_symbols if s in _YAHOO_ONLY]

        # ── 1. Dhan batch for Indian symbols ─────────────────────────────
        dhan_results: Dict[str, TickerQuote] = {}
        if self._dhan.is_live and dhan_targets:
            try:
                raw = self._dhan.get_multiple_quotes(dhan_targets)
                for sym, q in raw.items():
                    bare = self._bare(sym)
                    if q and getattr(q, "ltp", 0) > 0:
                        q.feed_source     = "DHAN"
                        q.fallback_active = False
                        q.feed_degraded   = False
                        q.symbol          = bare
                        self._ltp_cache[bare] = (float(q.ltp), time.monotonic(), "DHAN")
                        dhan_results[bare] = q
                        self._dhan_success += 1
                        self._last_source_dist["DHAN"] = (
                            self._last_source_dist.get("DHAN", 0) + 1
                        )
                        self._last_symbol_sources[bare] = "DHAN"
                        log.debug("[MarketDataRouter] DHAN  %s=%.2f", bare, q.ltp)
            except Exception as exc:
                log.warning("[MarketDataRouter] Dhan batch error: %s", exc)

        # Symbols Dhan missed (unknown/failed) — send to Yahoo
        dhan_missed = [s for s in dhan_targets if s not in dhan_results]
        if dhan_missed:
            self._dhan_fail += len(dhan_missed)
            log.debug("[MarketDataRouter] Dhan missed %d symbols → Yahoo: %s",
                      len(dhan_missed), dhan_missed)

        # ── 2. Yahoo batch for Dhan-missed + global symbols ───────────────
        yahoo_batch_bare = dhan_missed + yahoo_targets
        yahoo_results: Dict[str, TickerQuote] = {}

        if yahoo_batch_bare:
            # Build yf-ticker → bare reverse map for de-aliasing results
            yf_to_bare: Dict[str, str] = {}
            yf_tickers: List[str] = []
            for s in yahoo_batch_bare:
                yf = self._to_yahoo_ticker(s)
                yf_to_bare[yf] = s
                yf_tickers.append(yf)

            try:
                raw = self._yahoo.get_multiple_quotes(yf_tickers)
                for yf_ticker, q in raw.items():
                    bare = yf_to_bare.get(yf_ticker)
                    if not bare:
                        # Try stripping .NS suffix if Yahoo returned a different key
                        bare = yf_to_bare.get(yf_ticker + ".NS") or self._bare(yf_ticker)
                    if bare and q and getattr(q, "ltp", 0) > 0:
                        # Skip sim-injected values (feed_degraded=True from YahooFeed patch)
                        if getattr(q, "feed_degraded", False):
                            continue
                        q.feed_source     = "YAHOO"
                        q.fallback_active = bare not in _YAHOO_ONLY  # True = was Dhan target
                        q.feed_degraded   = False
                        q.symbol          = bare
                        self._ltp_cache[bare] = (float(q.ltp), time.monotonic(), "YAHOO")
                        yahoo_results[bare] = q
                        self._yahoo_success += 1
                        self._last_source_dist["YAHOO"] = (
                            self._last_source_dist.get("YAHOO", 0) + 1
                        )
                        self._last_symbol_sources[bare] = "YAHOO"
                        if q.fallback_active:
                            log.info("[MarketDataRouter] YAHOO_FALLBACK  %s=%.2f "
                                     "(Dhan unavailable)", bare, q.ltp)
                        else:
                            log.debug("[MarketDataRouter] YAHOO  %s=%.2f", bare, q.ltp)
            except Exception as exc:
                log.warning("[MarketDataRouter] Yahoo batch error: %s", exc)
                self._yahoo_fail += len(yahoo_batch_bare)

        # ── 3. Cache fallback for symbols still missing ───────────────────
        all_fetched = set(dhan_results) | set(yahoo_results)
        cache_results: Dict[str, TickerQuote] = {}

        for bare in bare_symbols:
            if bare in all_fetched:
                continue
            cached = self._ltp_cache.get(bare)
            if cached:
                cached_ltp, cached_ts, cached_src = cached
                age = time.monotonic() - cached_ts
                if age < _CACHE_MAX_AGE_SEC:
                    q = TickerQuote(
                        symbol             = bare,
                        timestamp          = datetime.now(),
                        ltp                = cached_ltp,
                        open               = cached_ltp,
                        high               = cached_ltp,
                        low                = cached_ltp,
                        close              = cached_ltp,
                        change             = 0.0,
                        change_pct         = 0.0,
                        volume             = 0.0,
                        feed_source        = "CACHE",
                        fallback_active    = True,
                        feed_degraded      = True,
                        consecutive_failures = 1,
                    )
                    cache_results[bare] = q
                    self._cache_served += 1
                    self._last_source_dist["CACHE"] = (
                        self._last_source_dist.get("CACHE", 0) + 1
                    )
                    self._last_symbol_sources[bare] = "CACHE"
                    log.info(
                        "[MarketDataRouter] CACHE_FALLBACK  %s  ltp=%.2f  "
                        "age=%.0fs  orig_src=%s",
                        bare, cached_ltp, age, cached_src,
                    )
                else:
                    # Cache too stale → degraded
                    self._last_degraded.add(bare)
                    self._degraded_count += 1
                    log.warning(
                        "[MarketDataRouter] FEED_DEGRADED  %s  "
                        "cache_age=%.0fs > limit %.0fs — symbol excluded",
                        bare, age, _CACHE_MAX_AGE_SEC,
                    )
            else:
                # No cache at all → degraded
                self._last_degraded.add(bare)
                self._degraded_count += 1
                self._last_symbol_sources[bare] = "DEGRADED"
                log.warning(
                    "[MarketDataRouter] FEED_DEGRADED  %s  "
                    "no live data and no cached LTP — symbol excluded",
                    bare,
                )

        # Track yahoo failures for degraded symbols
        self._yahoo_fail += len(self._last_degraded)

        # ── 4. Cross-validation: divergence check ────────────────────────
        # Dhan and Yahoo returned prices for the same symbol — compare.
        for sym in set(dhan_results) & set(yahoo_results):
            d_ltp = dhan_results[sym].ltp
            y_ltp = yahoo_results[sym].ltp
            if y_ltp > 0:
                div_pct = abs(d_ltp - y_ltp) / y_ltp
                if div_pct > _DIVERGENCE_THRESHOLD:
                    self._divergence_count += 1
                    log.warning(
                        "[MarketDataRouter] FEED_DIVERGENCE  %s  "
                        "dhan=%.2f  yahoo=%.2f  diff=%.1f%%  "
                        "→ Dhan authoritative for execution",
                        sym, d_ltp, y_ltp, div_pct * 100,
                    )

        # ── 5. Merge (Dhan wins, Yahoo fills gaps, cache last resort) ────
        result: Dict[str, TickerQuote] = {}
        result.update(cache_results)    # lowest priority
        result.update(yahoo_results)    # mid priority
        result.update(dhan_results)     # highest priority (authoritative)

        return result

    # ── Single-symbol helpers ─────────────────────────────────────────────

    def get_ltp(self, symbol: str) -> Tuple[float, str]:
        """
        Single-symbol LTP.
        Returns (ltp, source) where source is "DHAN" | "YAHOO" | "CACHE" | "DEGRADED".
        Returns (0.0, "DEGRADED") when no data available.
        """
        bare = self._bare(symbol)
        res  = self.get_live_prices([bare])
        q    = res.get(bare)
        if q and q.ltp > 0:
            return float(q.ltp), q.feed_source
        return 0.0, "DEGRADED"

    # ── Observability ─────────────────────────────────────────────────────

    def get_degraded_symbols(self) -> Set[str]:
        """
        Symbols that had no live data AND no valid cached LTP in the most
        recent get_live_prices() call.  These symbols were excluded from the
        returned dict.  SL monitoring and adaptive exits must be suppressed
        for these symbols until a live price is re-established.
        """
        return set(self._last_degraded)

    def get_symbol_sources(self) -> Dict[str, str]:
        """
        Per-symbol data source from the most recent get_live_prices() call.
        Returns dict of bare_symbol → "DHAN" | "YAHOO" | "CACHE" | "DEGRADED".
        Empty between calls or before the first call.
        """
        return dict(self._last_symbol_sources)

    def get_router_stats(self) -> dict:
        """
        Lifetime observability stats.  CycleHealthMonitor uses this to
        report primary_feed_health, fallback_usage, and degraded symbols.
        """
        total_live = self._dhan_success + self._yahoo_success
        dhan_pct   = round(self._dhan_success / total_live * 100, 1) if total_live > 0 else 0.0
        fallback_pct = round(self._yahoo_success / total_live * 100, 1) if total_live > 0 else 0.0
        return {
            # Dhan (primary)
            "dhan_success":        self._dhan_success,
            "dhan_fail":           self._dhan_fail,
            "dhan_success_pct":    dhan_pct,
            "dhan_live":           self._dhan.is_live,
            # Yahoo (fallback)
            "yahoo_success":       self._yahoo_success,
            "yahoo_fail":          self._yahoo_fail,
            "yahoo_fallback_pct":  fallback_pct,
            "yahoo_live":          self._yahoo.is_live,
            # Cache / degraded
            "cache_served":        self._cache_served,
            "degraded_total":      self._degraded_count,
            # Divergence
            "divergence_count":    self._divergence_count,
            # Totals
            "total_symbol_calls":  self._total_calls,
            # Current cycle
            "last_source_dist":    dict(self._last_source_dist),
            "last_degraded":       sorted(self._last_degraded),
        }

    def get_source_report(self) -> str:
        """Human-readable one-liner for logs / Telegram / dashboard."""
        s = self.get_router_stats()
        parts = []
        if s["dhan_live"]:
            parts.append(f"Dhan={s['dhan_success_pct']}%✅")
        else:
            parts.append("Dhan=SIM")
        parts.append(f"Yahoo_fallback={s['yahoo_fallback_pct']}%")
        parts.append(f"cache={s['cache_served']}")
        if s["last_degraded"]:
            parts.append(f"DEGRADED={s['last_degraded']}")
        if s["divergence_count"]:
            parts.append(f"divergence={s['divergence_count']}")
        return "  ".join(parts)
