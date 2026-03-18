"""
Data Feed Manager
==================
Unified interface for all data sources.
Automatically selects the best available feed and provides a single API
that the rest of the system (GlobalDataAI, MarketIntelligence, etc.) calls.

Architecture:
    DataFeedManager
      ├── YahooFeed            — global indices, currencies, commodities
      ├── NSEFeed              — Indian market data + options chain
      └── broker feed (future) — Zerodha WebSocket for real-time intraday

Wire-in:
  Replace _fetch_live_data() stub in global_data_ai.py with
  DataFeedManager.get_global_snapshot() to get real prices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from .yahoo_feed import YahooFeed
from .nse_feed   import NSEFeed
from .dhan_feed  import DhanFeed
from .base_feed  import TickerQuote, PriceBar, OptionsChain
from utils       import get_logger

log = get_logger(__name__)

# Singleton instance — created once, shared across all components
_INSTANCE: Optional["DataFeedManager"] = None


def get_feed_manager() -> "DataFeedManager":
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = DataFeedManager()
    return _INSTANCE


class FeedStatus:
    """Health snapshot of all data feeds."""
    def __init__(self, yahoo_live: bool, nse_live: bool, nse_mode: str,
                 dhan_live: bool = False) -> None:
        self.yahoo_live  = yahoo_live
        self.nse_live    = nse_live
        self.nse_mode    = nse_mode
        self.dhan_live   = dhan_live
        self.timestamp   = datetime.now()

    def summary(self) -> str:
        y = "✅ LIVE" if self.yahoo_live else "🔄 SIM"
        n = f"✅ {self.nse_mode.upper()}" if self.nse_live else "🔄 SIM"
        d = "✅ LIVE" if self.dhan_live else "not configured"
        return f"Yahoo={y}  NSE={n}  Dhan={d}"


class DataFeedManager:
    """
    Central hub for all market data.

    Usage::
        from data_feeds import get_feed_manager
        fm = get_feed_manager()

        # Global quote
        sp500 = fm.get_quote("SP500")

        # Indian index
        nifty = fm.get_indian_quote("NIFTY")

        # Options chain
        chain = fm.get_options_chain("NIFTY")

        # Historical candles
        bars = fm.get_history("NIFTY", days=30)

        # Full global snapshot (wires into GlobalDataAI)
        snap = fm.get_global_snapshot()
    """

    def __init__(self) -> None:
        self.yahoo = YahooFeed()
        self.nse   = NSEFeed()
        self.dhan  = DhanFeed()   # primary Indian data source when credentials set
        log.info("[DataFeedManager] Initialised. %s", self.status().summary())

    # ── Status ─────────────────────────────────────────────────────────────

    def status(self) -> FeedStatus:
        return FeedStatus(
            yahoo_live = self.yahoo.is_live,
            nse_live   = self.nse.is_live,
            nse_mode   = self.nse.name,
            dhan_live  = self.dhan.is_live,
        )

    # ── Quotes ─────────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Get a market quote. Indian symbols prefer DhanFeed when live."""
        from .dhan_feed import DHAN_SECURITY_MAP
        if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:
            q = self.dhan.get_quote(symbol)
            if q and q.ltp > 0:
                return q
        return self.yahoo.get_quote(symbol)

    def get_indian_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Get an Indian market quote — prefers DhanFeed, falls back to NSEFeed."""
        if self.dhan.is_live:
            q = self.dhan.get_quote(symbol)
            if q and q.ltp > 0:
                return q
        return self.nse.get_quote(symbol)

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Batch fetch quotes. Indian symbols via Dhan, global via Yahoo."""
        from .dhan_feed import DHAN_SECURITY_MAP
        if self.dhan.is_live:
            indian = [s for s in symbols if s.upper() in DHAN_SECURITY_MAP]
            global_ = [s for s in symbols if s.upper() not in DHAN_SECURITY_MAP]
            result = self.dhan.get_multiple_quotes(indian) if indian else {}
            result.update(self.yahoo.get_multiple_quotes(global_) if global_ else {})
            return result
        return self.yahoo.get_multiple_quotes(symbols)

    # ── History ────────────────────────────────────────────────────────────

    def get_history(
        self,
        symbol:   str,
        days:     int  = 30,
        interval: str  = "1d",
        indian:   bool = False,
    ) -> List[PriceBar]:
        """
        Get historical OHLCV bars.
        Priority: DhanFeed (when live) → NSEFeed (indian) → YahooFeed.
        """
        from .dhan_feed import DHAN_SECURITY_MAP
        if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:
            bars = self.dhan.get_history(symbol, days, interval)
            if bars:
                return bars
        if indian:
            return self.nse.get_history(symbol, days, interval)
        return self.yahoo.get_history(symbol, days, interval)

    # ── Options ────────────────────────────────────────────────────────────

    def get_options_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> Optional[OptionsChain]:
        """Get full options chain. Prefers DhanFeed (live Greeks + OI) over NSEFeed."""
        if self.dhan.is_live:
            chain = self.dhan.get_options_chain(symbol, expiry)
            if chain:
                return chain
        return self.nse.get_options_chain(symbol, expiry)

    def get_pcr(self, symbol: str = "NIFTY") -> float:
        """Put-Call Ratio — from Dhan when live, else NSEFeed."""
        if self.dhan.is_live:
            pcr = self.dhan.get_pcr(symbol)
            if pcr > 0:
                return pcr
        return self.nse.get_pcr(symbol)

    def get_options_snapshot(self, symbol: str = "NIFTY") -> Dict:
        """
        Condensed options data for the AI intelligence layer.
        Returns: {pcr, spot, iv_rank, atm_iv, call_oi, put_oi}
        """
        chain = self.get_options_chain(symbol)
        if not chain:
            return {"pcr": 0.85, "spot": 22500, "iv_rank": 40,
                    "atm_iv": 14.0, "call_oi": 0, "put_oi": 0}

        atm     = chain.atm_strike()
        atm_contracts = [c for c in chain.contracts if c.strike == atm]
        atm_iv  = sum(c.iv for c in atm_contracts) / len(atm_contracts) if atm_contracts else 14.0
        call_oi = sum(c.oi for c in chain.calls())
        put_oi  = sum(c.oi for c in chain.puts())
        iv_rank = min(100, atm_iv * 2)   # rough percentile estimate

        return {
            "pcr":      chain.pcr,
            "spot":     chain.spot_price,
            "iv_rank":  round(iv_rank, 1),
            "atm_iv":   round(atm_iv, 2),
            "call_oi":  call_oi,
            "put_oi":   put_oi,
            "max_pain": chain.max_pain,
            "expiry":   chain.expiry,
        }

    # ── Global Snapshot (for GlobalDataAI) ────────────────────────────────

    def get_global_snapshot(self) -> Dict:
        """
        Fetch all global market data in one call.
        Returns a flat dict matching the GlobalSnapshot field names.
        Used in GlobalDataAI._fetch_live_data() override.
        """
        symbols = [
            "SP500", "NASDAQ", "DOW",
            "NIKKEI", "HANGSENG",
            "USDINR", "DXY", "EURUSD",
            "GOLD", "CRUDE_WTI", "CRUDE_BRENT",
            "VIX", "US10Y",
        ]
        # Batch fetch
        quotes = self.get_multiple_quotes(symbols)

        def q(sym: str, field: str = "ltp") -> float:
            qt = quotes.get(sym)
            if qt is None:
                return 0.0
            return getattr(qt, field, 0.0)

        def chg(sym: str) -> float:
            qt = quotes.get(sym)
            return qt.change_pct if qt else 0.0

        return {
            # US
            "sp500_level":     q("SP500"),
            "sp500_change":    chg("SP500"),
            "nasdaq_level":    q("NASDAQ"),
            "nasdaq_change":   chg("NASDAQ"),
            "dow_level":       q("DOW"),
            "dow_change":      chg("DOW"),
            # Asia
            "nikkei_level":    q("NIKKEI"),
            "nikkei_change":   chg("NIKKEI"),
            "hangseng_level":  q("HANGSENG"),
            "hangseng_change": chg("HANGSENG"),
            # Currencies
            "usdinr":          (self.dhan.get_ltp("USDINR") if self.dhan.is_live else 0)
                               or q("USDINR") or 83.5,
            "usdinr_rate":     (self.dhan.get_ltp("USDINR") if self.dhan.is_live else 0)
                               or q("USDINR") or 83.5,   # GlobalSnapshot field name
            "dxy":             q("DXY"),
            "eurusd":          q("EURUSD"),
            # Commodities
            "gold_price":      q("GOLD"),
            "gold_change":     chg("GOLD"),
            "crude_wti":       q("CRUDE_WTI"),
            "crude_brent":     q("CRUDE_BRENT"),
            "crude_change":    chg("CRUDE_WTI"),
            # Vol / Bonds
            "vix":             q("VIX"),
            "us_10y_yield":    q("US10Y"),
            # India — prefer DhanFeed (has real VIX + USDINR); fallback to yfinance/NSE
            "india_vix":       (self.dhan.get_ltp("INDIAVIX") if self.dhan.is_live else 0)
                               or (self.nse.get_quote("INDIAVIX").ltp
                                   if self.nse.get_quote("INDIAVIX") else 14.0),
            "nifty_level":     (self.dhan.get_ltp("NIFTY") if self.dhan.is_live else 0)
                               or (self.nse.get_quote("NIFTY").ltp
                                   if self.nse.get_quote("NIFTY") else 22500.0),
            "banknifty_level": (self.dhan.get_ltp("BANKNIFTY") if self.dhan.is_live else 0)
                               or (self.nse.get_quote("BANKNIFTY").ltp
                                   if self.nse.get_quote("BANKNIFTY") else 48000.0),
        }

    # ── Indian Market Batch ────────────────────────────────────────────────

    def get_indian_market_snapshot(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, TickerQuote]:
        """
        Fetch multiple Indian stocks/indices at once.
        Default: top 20 Nifty constituents.
        """
        symbols = symbols or [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
            "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI",
            "SUNPHARMA", "TITAN", "ULTRACEMCO", "NESTLEIND", "WIPRO",
        ]
        results = {}
        for sym in symbols:
            q = self.nse.get_quote(sym)
            if q:
                results[sym] = q
        return results
