"""
Dhan Broker Feed Adapter
========================
Connects to Dhan API v2 for real Indian market data:

  • Live REST quotes  — OHLC, LTP, OI, IV for any NSE/BSE instrument
  • WebSocket ticks   — zero-delay MarketFeed (background thread + cache)
  • Historical OHLCV  — daily candles + intraday minute candles
  • Options chain     — full chain with Greeks, OI, PCR, IV
  • India VIX         — native from Dhan (no yfinance delisting issue)
  • Order placement   — place/modify/cancel via REST (for live trading)

Setup
-----
  pip install dhanhq

  Add to .env  (or export in shell):
      DHAN_CLIENT_ID    = "your-client-id"
      DHAN_ACCESS_TOKEN = "your-access-token"

  Get credentials:
      https://dhan.co → My Profile → API → Create App → Get Access Token

Rate limits (Dhan v2):
    REST   → 10 req/s  |  250 req/min  |  7 000 req/day
    Market Feed → WebSocket: unlimited tick stream

Exchange segments used herein:
    "NSE_EQ"   → NSE Cash Equity
    "NSE_FNO"  → NSE Futures & Options
    "IDX_I"    → NSE Index  (NIFTY, BANKNIFTY …)
    "BSE_EQ"   → BSE Cash
    "CUR_IDX"  → Currency index  (USDINR)
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from .base_feed import BaseFeed, PriceBar, TickerQuote, OptionsChain, OptionsContract
from utils import get_logger

log = get_logger(__name__)

# ── Credential helpers ────────────────────────────────────────────────────

def _get_credentials() -> Tuple[str, str]:
    client_id    = os.getenv("DHAN_CLIENT_ID", "")
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
    return client_id, access_token


# ── Static security ID map (Dhan numeric IDs) ─────────────────────────────
# These are the official Dhan security IDs for common instruments.
# The adapter will also attempt to extend this map automatically by
# calling dhan.fetch_security_list() on first connect.

DHAN_SECURITY_MAP: Dict[str, Dict[str, Any]] = {
    # ── Indices (exchange_segment = "IDX_I", instrument_type = "INDEX")
    "NIFTY":         {"security_id": "13",    "segment": "IDX_I",  "itype": "INDEX"},
    "BANKNIFTY":     {"security_id": "25",    "segment": "IDX_I",  "itype": "INDEX"},
    "FINNIFTY":      {"security_id": "27",    "segment": "IDX_I",  "itype": "INDEX"},
    "MIDCAPNIFTY":   {"security_id": "442",   "segment": "IDX_I",  "itype": "INDEX"},
    "INDIAVIX":      {"security_id": "21",    "segment": "IDX_I",  "itype": "INDEX"},
    "SENSEX":        {"security_id": "51",    "segment": "IDX_I",  "itype": "INDEX"},

    # ── Currency
    "USDINR":        {"security_id": "101",   "segment": "CUR_IDX","itype": "FUTIDX"},

    # ── NSE Large-Cap Equities (exchange_segment = "NSE_EQ")
    "HDFCBANK":      {"security_id": "1333",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "RELIANCE":      {"security_id": "2885",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "TCS":           {"security_id": "11536", "segment": "NSE_EQ", "itype": "EQUITY"},
    "INFY":          {"security_id": "10604", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ICICIBANK":     {"security_id": "4963",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "KOTAKBANK":     {"security_id": "1922",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "HINDUNILVR":    {"security_id": "1394",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "ITC":           {"security_id": "1660",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "SBIN":          {"security_id": "3045",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "AXISBANK":      {"security_id": "5900",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "LT":            {"security_id": "11483", "segment": "NSE_EQ", "itype": "EQUITY"},
    "WIPRO":         {"security_id": "3787",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "BAJFINANCE":    {"security_id": "317",   "segment": "NSE_EQ", "itype": "EQUITY"},
    "MARUTI":        {"security_id": "10999", "segment": "NSE_EQ", "itype": "EQUITY"},
    "BHARTIARTL":    {"security_id": "317",   "segment": "NSE_EQ", "itype": "EQUITY"},
    "SUNPHARMA":     {"security_id": "3351",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "TITAN":         {"security_id": "3506",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "NESTLEIND":     {"security_id": "17963", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ULTRACEMCO":    {"security_id": "11532", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ASIANPAINT":    {"security_id": "236",   "segment": "NSE_EQ", "itype": "EQUITY"},
    "TECHM":         {"security_id": "13538", "segment": "NSE_EQ", "itype": "EQUITY"},
    "POWERGRID":     {"security_id": "14977", "segment": "NSE_EQ", "itype": "EQUITY"},
    "NTPC":          {"security_id": "11630", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ONGC":          {"security_id": "11654", "segment": "NSE_EQ", "itype": "EQUITY"},
    "HCLTECH":       {"security_id": "7229",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "ADANIENT":      {"security_id": "25",    "segment": "NSE_EQ", "itype": "EQUITY"},
    "JSWSTEEL":      {"security_id": "11723", "segment": "NSE_EQ", "itype": "EQUITY"},
    "TATAMOTORS":    {"security_id": "3456",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "TATASTEEL":     {"security_id": "3499",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "M&M":           {"security_id": "2031",  "segment": "NSE_EQ", "itype": "EQUITY"},
}

# MarketFeed exchange segment integers (for WebSocket subscription)
_WS_SEGMENT: Dict[str, int] = {
    "NSE_EQ":  1,
    "NSE_FNO": 2,
    "IDX_I":   13,
    "BSE_EQ":  4,
    "CUR_IDX": 7,
}


# ── yfinance ticker map (fallback when Dhan Data API not subscribed) ────────
_YF_TICKERS: Dict[str, str] = {
    "NIFTY":       "^NSEI",
    "BANKNIFTY":   "^NSEBANK",
    "INDIAVIX":    "^INDIAVIX",
    "FINNIFTY":    "NIFTY_FIN_SERVICE.NS",
    "MIDCAPNIFTY": "^NSEMDCP50",
    "SENSEX":      "^BSESN",
    "USDINR":      "USDINR=X",
    "SGXNIFTY":    "^NSEI",
    "GOLD":        "GC=F",
    "HDFCBANK":    "HDFCBANK.NS",
    "RELIANCE":    "RELIANCE.NS",
    "TCS":         "TCS.NS",
    "INFY":        "INFY.NS",
    "ICICIBANK":   "ICICIBANK.NS",
    "SBIN":        "SBIN.NS",
    "WIPRO":       "WIPRO.NS",
    "BAJFINANCE":  "BAJFINANCE.NS",
}

# ── Simulation fallback prices (approximate; only used if yfinance also fails) ─
_SIM_PRICES: Dict[str, float] = {
    "NIFTY": 23987.0, "BANKNIFTY": 56064.0, "FINNIFTY": 26071.0,
    "MIDCAPNIFTY": 13055.0, "INDIAVIX": 20.8, "USDINR": 86.5,
    "HDFCBANK": 1900.0, "RELIANCE": 1320.0, "TCS": 3800.0,
    "INFY": 1750.0, "ICICIBANK": 1380.0, "SBIN": 820.0,
    "WIPRO": 300.0, "BAJFINANCE": 8900.0,
}


class DhanFeed(BaseFeed):
    """
    Full Dhan API v2 feed adapter.

    Falls back gracefully to simulation if credentials are not set
    or if the API call fails, so the system keeps running in dev/test.

    Usage:
        feed = DhanFeed()
        if feed.is_live:
            q = feed.get_quote("NIFTY")   # real data
    """

    # ── Init ──────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._dhan         = None       # dhanhq REST client
        self._context      = None       # DhanContext
        self._live         = False
        self._ws_cache:    Dict[str, Dict] = {}   # symbol → latest tick from WS
        self._ws_thread:   Optional[threading.Thread] = None
        self._ws_running   = False
        self._extra_map:   Dict[str, Dict[str, Any]] = {}  # loaded from instrument list

        self._connect()

    def _connect(self) -> None:
        """Try to initialise dhanhq client with environment credentials."""
        client_id, access_token = _get_credentials()
        if not client_id or not access_token:
            log.warning(
                "[DhanFeed] Credentials not set (DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN). "
                "Running in simulation mode."
            )
            return
        try:
            from dhanhq import dhanhq as _DhanHQ  # type: ignore  # works v2.0.x and v2.1+
            # v2.1+ exposes DhanContext; v2.0.x uses direct positional args
            try:
                from dhanhq import DhanContext  # type: ignore  # v2.1+
                self._context = DhanContext(client_id, access_token)
                self._dhan    = _DhanHQ(self._context)
            except ImportError:
                # v2.0.x — no DhanContext; pass credentials directly
                self._dhan    = _DhanHQ(client_id, access_token)
                self._context = None
            self._live = True
            try:
                import dhanhq as _pkg
                _ver = getattr(_pkg, "__version__", "unknown")
            except Exception:
                _ver = "unknown"
            log.info("[DhanFeed] \u2705 Connected to Dhan API  client_id=%s  pkg_version=%s",
                     client_id, _ver)
            # Optional list preload can be noisy with some dhanhq versions;
            # keep default startup path clean unless explicitly enabled.
            if os.getenv("DHAN_LOAD_SECURITY_LIST", "false").strip().lower() in ("1", "true", "yes", "on"):
                self._load_instrument_list()
        except ImportError:
            log.warning(
                "[DhanFeed] dhanhq package not installed. "
                "Run: pip install dhanhq   — falling back to simulation."
            )
        except Exception as exc:
            log.error("[DhanFeed] Connection failed: %s — falling back to simulation.", exc)

    def _load_instrument_list(self) -> None:
        """
        Optionally load Dhan's compact instrument list to build a dynamic
        security_id map for any symbol not covered by DHAN_SECURITY_MAP.
        Runs in a background thread to avoid blocking startup.
        """
        def _load():
            try:
                result = self._dhan.fetch_security_list("compact")
                if not result or not isinstance(result, list):
                    return
                for row in result:
                    sym = row.get("SEM_TRADING_SYMBOL", "").upper()
                    seg = row.get("SEM_EXM_EXCH_ID", "NSE_EQ")
                    sid = str(row.get("SEM_SMST_SECURITY_ID", ""))
                    if sym and sid and sym not in DHAN_SECURITY_MAP:
                        self._extra_map[sym] = {
                            "security_id": sid,
                            "segment":     seg,
                            "itype":       row.get("SEM_INSTRUMENT_NAME", "EQUITY"),
                        }
                log.info("[DhanFeed] Instrument list loaded — %d extra symbols.", len(self._extra_map))
            except Exception as exc:
                log.debug("[DhanFeed] Instrument list load skipped: %s", exc)

        t = threading.Thread(target=_load, daemon=True, name="DhanInstrumentLoader")
        t.start()

    # ── BaseFeed interface ────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "DHAN" if self._live else "DHAN(SIM)"

    @property
    def is_live(self) -> bool:
        return self._live

    # ── Symbol lookup ─────────────────────────────────────────────────────

    def _lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return Dhan meta dict for a symbol (static map first, then dynamic)."""
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        return DHAN_SECURITY_MAP.get(sym) or self._extra_map.get(sym)

    # ── Quotes (REST) ─────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Fetch latest OHLC quote via Dhan REST market-quote API."""
        # Return cached WebSocket tick if fresher than 5 s
        cached = self._ws_cache.get(symbol.upper())
        if cached and (time.time() - cached.get("_ts", 0)) < 5:
            return self._ws_tick_to_quote(symbol, cached)

        if not self._live:
            return self._yf_quote(symbol) or self._sim_quote(symbol)

        meta = self._lookup(symbol)
        if not meta:
            log.debug("[DhanFeed] Unknown symbol: %s", symbol)
            return self._yf_quote(symbol) or self._sim_quote(symbol)

        try:
            seg = meta["segment"]
            sid = int(meta["security_id"])
            # Build securities dict expected by ohlc_data
            sec_dict = {seg: [sid]}
            resp = self._dhan.ohlc_data(securities=sec_dict)
            if not resp or "data" not in resp:
                return self._yf_quote(symbol) or self._sim_quote(symbol)
            data = resp["data"]
            # ohlc_data returns {segment: {str(sid): {...}}}
            seg_data = data.get(seg, data)
            row = seg_data.get(str(sid), {})
            if not row:
                return self._yf_quote(symbol) or self._sim_quote(symbol)
            return self._row_to_quote(symbol, row)
        except Exception as exc:
            log.debug("[DhanFeed] get_quote(%s) error: %s", symbol, exc)
            return self._yf_quote(symbol) or self._sim_quote(symbol)

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Batch-fetch OHLC quotes for multiple symbols in grouped API calls."""
        if not self._live:
            return {s: self._sim_quote(s) for s in symbols if self._sim_quote(s)}

        # Group by exchange segment for efficient batch calls
        groups: Dict[str, List[int]] = {}
        sym_map: Dict[Tuple[str, int], str] = {}  # (seg, sid) → symbol
        missing: List[str] = []

        for sym in symbols:
            meta = self._lookup(sym)
            if not meta:
                missing.append(sym)
                continue
            seg = meta["segment"]
            sid = int(meta["security_id"])
            groups.setdefault(seg, []).append(sid)
            sym_map[(seg, sid)] = sym

        result: Dict[str, TickerQuote] = {}

        if groups:
            try:
                resp = self._dhan.ohlc_data(securities=groups)
                data = resp.get("data", resp) if resp else {}
                for seg, sids in groups.items():
                    seg_data = data.get(seg, {})
                    for sid in sids:
                        row = seg_data.get(str(sid), {})
                        sym = sym_map.get((seg, sid))
                        if row and sym:
                            result[sym] = self._row_to_quote(sym, row)
            except Exception as exc:
                log.debug("[DhanFeed] batch quote error: %s", exc)

        # Fallback sim for unknown symbols
        for sym in missing:
            q = self._sim_quote(sym)
            if q:
                result[sym] = q

        return result

    def get_ltp(self, symbol: str) -> float:
        """Lightweight LTP-only fetch. Tries Dhan ticker_data, then yfinance, then sim."""
        if not self._live:
            return self._yf_ltp(symbol) or _SIM_PRICES.get(symbol.upper(), 100.0)
        meta = self._lookup(symbol)
        if not meta:
            return self._yf_ltp(symbol) or _SIM_PRICES.get(symbol.upper(), 100.0)
        try:
            seg = meta["segment"]
            sid = int(meta["security_id"])
            resp = self._dhan.ticker_data(securities={seg: [sid]})
            data = (resp or {}).get("data", resp or {})
            seg_data = data.get(seg, data)
            row = seg_data.get(str(sid), {})
            ltp = float(row.get("last_price", row.get("ltp", 0)))
            if ltp:
                return ltp
            # Dhan returned empty — fall back to yfinance
            return self._yf_ltp(symbol) or _SIM_PRICES.get(symbol.upper(), 100.0)
        except Exception as exc:
            log.debug("[DhanFeed] get_ltp(%s) error: %s", symbol, exc)
            return self._yf_ltp(symbol) or _SIM_PRICES.get(symbol.upper(), 100.0)

    # ── Historical OHLCV ──────────────────────────────────────────────────

    def get_history(
        self,
        symbol:   str,
        days:     int  = 30,
        interval: str  = "1d",   # "1d" | "1m" | "5m" | "15m" | "30m" | "60m"
    ) -> List[PriceBar]:
        """
        Fetch historical OHLCV candles via Dhan API.
        - interval "1d"  → historical_daily_data
        - interval "Xm"  → intraday_minute_data (max 30 calendar days)
        """
        if not self._live:
            return self._sim_history(symbol, days)

        meta = self._lookup(symbol)
        if not meta:
            return self._sim_history(symbol, days)

        sid = meta["security_id"]
        seg = meta["segment"]
        itype = meta.get("itype", "EQUITY")

        to_dt   = date.today()
        from_dt = to_dt - timedelta(days=days + 5)   # buffer for weekends

        from_str = from_dt.strftime("%Y-%m-%d")
        to_str   = to_dt.strftime("%Y-%m-%d")

        try:
            if interval == "1d":
                resp = self._dhan.historical_daily_data(
                    security_id    = sid,
                    exchange_segment = seg,
                    instrument_type  = itype,
                    from_date        = from_str,
                    to_date          = to_str,
                )
            else:
                # Convert "5m" → 5, "15m" → 15 etc.
                mins = int(interval.replace("m", "")) if interval.endswith("m") else 1
                resp = self._dhan.intraday_minute_data(
                    security_id      = sid,
                    exchange_segment = seg,
                    instrument_type  = itype,
                    interval         = str(mins),
                    from_date        = from_str,
                    to_date          = to_str,
                )
        except Exception as exc:
            log.debug("[DhanFeed] get_history(%s) error: %s", symbol, exc)
            return self._sim_history(symbol, days)

        return self._parse_candles(symbol, resp, interval)

    # ── Options Chain ─────────────────────────────────────────────────────

    def get_options_chain(
        self,
        symbol: str = "NIFTY",
        expiry: Optional[str] = None,
    ) -> Optional[OptionsChain]:
        """
        Fetch full options chain (all strikes, all expiries) via Dhan API.
        expiry format: "YYYY-MM-DD"  (nearest expiry used if None)
        """
        if not self._live:
            return None   # caller falls back to NSEFeed simulation

        meta = self._lookup(symbol)
        if not meta or meta["segment"] != "IDX_I":
            log.debug("[DhanFeed] Options chain only supported for NSE indices.")
            return None

        # Determine nearest weekly expiry if not provided
        if expiry is None:
            expiry = self._nearest_expiry()

        try:
            resp = self._dhan.option_chain(
                under_security_id     = int(meta["security_id"]),
                under_exchange_segment= "IDX_I",
                expiry                = expiry,
            )
            return self._parse_option_chain(symbol, resp, expiry)
        except Exception as exc:
            log.debug("[DhanFeed] get_options_chain(%s) error: %s", symbol, exc)
            return None

    def get_pcr(self, symbol: str = "NIFTY") -> float:
        """Put-Call Ratio from live options chain."""
        chain = self.get_options_chain(symbol)
        if chain and chain.pcr:
            return chain.pcr
        return 0.85   # default neutral PCR

    # ── WebSocket Live Market Feed ────────────────────────────────────────

    def start_live_feed(self, symbols: List[str]) -> None:
        """
        Start a background WebSocket thread that keeps self._ws_cache
        updated with the latest ticks for the given symbols.

        Once running, get_quote() will return cached ticks (0-delay).

        Parameters
        ----------
        symbols : list of symbol names, e.g. ["NIFTY", "HDFCBANK", "TCS"]
        """
        if not self._live:
            log.warning("[DhanFeed] Cannot start live feed — not connected to Dhan.")
            return
        if self._ws_running:
            log.debug("[DhanFeed] Live feed already running.")
            return

        instruments = []
        for sym in symbols:
            meta = self._lookup(sym)
            if not meta:
                continue
            ws_seg = _WS_SEGMENT.get(meta["segment"], 1)
            instruments.append((ws_seg, meta["security_id"]))

        if not instruments:
            log.warning("[DhanFeed] No valid instruments for live feed.")
            return

        self._ws_running = True
        self._ws_thread  = threading.Thread(
            target=self._ws_loop,
            args=(instruments,),
            daemon=True,
            name="DhanMarketFeed",
        )
        self._ws_thread.start()
        log.info("[DhanFeed] Live MarketFeed started — %d instruments.", len(instruments))

    def stop_live_feed(self) -> None:
        """Signal the WebSocket thread to stop."""
        self._ws_running = False
        log.info("[DhanFeed] Live feed stop requested.")

    def _ws_loop(self, instruments: List[Tuple[int, str]]) -> None:
        """Background thread: maintains WebSocket connection and updates cache."""
        client_id, access_token = _get_credentials()
        try:
            # Support v2.1+ (top-level MarketFeed) and v2.0.x (marketfeed.DhanFeed)
            try:
                from dhanhq import MarketFeed as _MarketFeed  # type: ignore  # v2.1+
                _new_api = True
            except ImportError:
                from dhanhq.marketfeed import DhanFeed as _MarketFeed  # type: ignore  # v2.0.x
                _new_api = False

            while self._ws_running:
                try:
                    feed_instruments = [
                        (seg, sid, _MarketFeed.Full)
                        for seg, sid in instruments
                    ]
                    if _new_api and self._context is not None:
                        feed = _MarketFeed(self._context, feed_instruments, version="v2")
                    elif _new_api:
                        feed = _MarketFeed(client_id, access_token, feed_instruments)
                    else:
                        # v2.0.x: positional client_id, access_token, instruments
                        feed = _MarketFeed(client_id, access_token, feed_instruments)
                    log.info("[DhanFeed] WebSocket connected.")

                    while self._ws_running:
                        feed.run_forever()
                        response = feed.get_data()
                        if response:
                            self._handle_ws_tick(response)

                except Exception as exc:
                    if self._ws_running:
                        log.warning("[DhanFeed] WebSocket disconnected: %s — reconnecting in 5s.", exc)
                        time.sleep(5)
        except ImportError:
            log.error("[DhanFeed] dhanhq not available for WebSocket.")

    def _handle_ws_tick(self, data: Dict) -> None:
        """Parse a MarketFeed WebSocket packet and update cache."""
        # Dhan returns security_id as the key in the packet
        sid = str(data.get("security_id", data.get("securityId", "")))
        if not sid:
            return
        # Reverse-lookup symbol from security_id
        sym = self._sid_to_symbol(sid)
        if sym:
            data["_ts"] = time.time()
            self._ws_cache[sym] = data

    def _sid_to_symbol(self, sid: str) -> Optional[str]:
        """Reverse-lookup: security_id → symbol name."""
        for sym, meta in DHAN_SECURITY_MAP.items():
            if meta["security_id"] == sid:
                return sym
        for sym, meta in self._extra_map.items():
            if meta["security_id"] == sid:
                return sym
        return None

    # ── Order Placement (live trading) ────────────────────────────────────

    def place_order(
        self,
        symbol:        str,
        transaction:   str,   # "BUY" | "SELL"
        quantity:      int,
        order_type:    str = "MARKET",   # "MARKET" | "LIMIT"
        price:         float = 0.0,
        product_type:  str = "INTRA",    # "INTRA" | "CNC" | "MARGIN"
        validity:      str = "DAY",
    ) -> Optional[str]:
        """
        Place a live order via Dhan REST API.
        Returns order_id on success, None on failure.

        Parameters
        ----------
        symbol       : NSE symbol name (e.g. "HDFCBANK")
        transaction  : "BUY" or "SELL"
        quantity     : number of shares
        order_type   : "MARKET" | "LIMIT"
        price        : limit price (0 for market orders)
        product_type : "INTRA" (MIS), "CNC" (delivery), "MARGIN"
        validity     : "DAY" | "IOC"
        """
        if not self._live:
            log.warning("[DhanFeed] Not connected to Dhan — order not placed.")
            return None

        meta = self._lookup(symbol)
        if not meta:
            log.error("[DhanFeed] Unknown symbol for order: %s", symbol)
            return None

        try:
            resp = self._dhan.place_order(
                security_id       = meta["security_id"],
                exchange_segment  = meta["segment"],
                transaction_type  = transaction.upper(),
                quantity          = quantity,
                order_type        = order_type.upper(),
                product_type      = product_type.upper(),
                price             = price,
                validity          = validity.upper(),
            )
            order_id = (resp or {}).get("orderId", (resp or {}).get("order_id"))
            if order_id:
                log.info("[DhanFeed] ✅ Order placed: %s %s %s qty=%d → order_id=%s",
                         transaction, symbol, order_type, quantity, order_id)
                return str(order_id)
            log.warning("[DhanFeed] Order response missing order_id: %s", resp)
            return None
        except Exception as exc:
            log.error("[DhanFeed] place_order(%s) failed: %s", symbol, exc)
            return None

    def modify_order(
        self, order_id: str, price: float = 0.0,
        trigger_price: float = 0.0, quantity: Optional[int] = None,
    ) -> bool:
        """Modify a pending order's price/quantity."""
        if not self._live:
            return False
        try:
            self._dhan.modify_order(
                order_id      = order_id,
                order_type    = "LIMIT",
                leg_name      = "ENTRY_LEG",
                quantity      = quantity or 0,
                price         = price,
                trigger_price = trigger_price,
                disclosed_quantity = 0,
                validity      = "DAY",
            )
            return True
        except Exception as exc:
            log.error("[DhanFeed] modify_order(%s) failed: %s", order_id, exc)
            return False

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order by ID."""
        if not self._live:
            return False
        try:
            self._dhan.cancel_order(order_id)
            log.info("[DhanFeed] Order cancelled: %s", order_id)
            return True
        except Exception as exc:
            log.error("[DhanFeed] cancel_order(%s) failed: %s", order_id, exc)
            return False

    def get_positions(self) -> List[Dict]:
        """Fetch open positions from Dhan account."""
        if not self._live:
            return []
        try:
            resp = self._dhan.get_positions()
            return resp if isinstance(resp, list) else (resp or {}).get("data", [])
        except Exception as exc:
            log.debug("[DhanFeed] get_positions error: %s", exc)
            return []

    def get_fund_limits(self) -> Dict:
        """Fetch available margin / cash balance from Dhan."""
        if not self._live:
            return {"availabelBalance": 0, "sodLimit": 0}
        try:
            resp = self._dhan.get_fund_limits()
            return resp or {}
        except Exception as exc:
            log.debug("[DhanFeed] get_fund_limits error: %s", exc)
            return {}

    # ── Internal parsers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_quote(symbol: str, row: Dict) -> TickerQuote:
        """Convert Dhan API ohlc_data row → TickerQuote."""
        ltp    = float(row.get("last_price",    row.get("ltp",   0)) or 0)
        open_  = float(row.get("open",          row.get("o",     ltp)) or ltp)
        high   = float(row.get("high",          row.get("h",     ltp)) or ltp)
        low    = float(row.get("low",           row.get("l",     ltp)) or ltp)
        close  = float(row.get("close",         row.get("prev_close", ltp)) or ltp)
        vol    = float(row.get("volume",        row.get("v",     0)) or 0)
        oi     = float(row.get("open_interest", row.get("oi",    0)) or 0)
        chg    = round(ltp - close, 2)
        chg_p  = round(chg / close * 100, 4) if close else 0.0
        return TickerQuote(
            symbol     = symbol,
            timestamp  = datetime.now(),
            ltp        = ltp,
            open       = open_,
            high       = high,
            low        = low,
            close      = close,
            change     = chg,
            change_pct = chg_p,
            volume     = vol,
            oi         = oi,
        )

    @staticmethod
    def _ws_tick_to_quote(symbol: str, tick: Dict) -> TickerQuote:
        """Convert a WebSocket MarketFeed Full packet → TickerQuote."""
        ltp   = float(tick.get("LTP",    tick.get("last_price", 0)) or 0)
        open_ = float(tick.get("open",   ltp))
        high  = float(tick.get("high",   ltp))
        low   = float(tick.get("low",    ltp))
        close = float(tick.get("close",  tick.get("prev_close", ltp)))
        vol   = float(tick.get("volume", 0))
        oi    = float(tick.get("OI",     tick.get("oi", 0)))
        chg   = round(ltp - close, 2)
        chg_p = round(chg / close * 100, 4) if close else 0.0
        return TickerQuote(
            symbol     = symbol,
            timestamp  = datetime.fromtimestamp(tick.get("_ts", time.time())),
            ltp        = ltp,
            open       = open_,
            high       = high,
            low        = low,
            close      = close,
            change     = chg,
            change_pct = chg_p,
            volume     = vol,
            oi         = oi,
        )

    @staticmethod
    def _parse_candles(symbol: str, resp: Any, interval: str) -> List[PriceBar]:
        """Parse Dhan historical/intraday response → List[PriceBar]."""
        if not resp:
            return []
        # Dhan returns {"open": [...], "high": [...], "low": [...],
        #               "close": [...], "volume": [...], "start_Time": [...]}
        try:
            data  = resp if isinstance(resp, dict) else {}
            opens  = data.get("open",       [])
            highs  = data.get("high",       [])
            lows   = data.get("low",        [])
            closes = data.get("close",      [])
            vols   = data.get("volume",     [])
            times  = data.get("start_Time", data.get("timestamp", []))
            bars   = []
            for i in range(min(len(opens), len(closes))):
                try:
                    ts_raw = times[i] if i < len(times) else None
                    if ts_raw is None:
                        ts = datetime.now()
                    elif isinstance(ts_raw, (int, float)):
                        ts = datetime.fromtimestamp(ts_raw)
                    else:
                        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                    bars.append(PriceBar(
                        symbol    = symbol,
                        timestamp = ts,
                        open      = float(opens[i]  or 0),
                        high      = float(highs[i]  or 0) if i < len(highs) else float(opens[i]),
                        low       = float(lows[i]   or 0) if i < len(lows)  else float(opens[i]),
                        close     = float(closes[i] or 0),
                        volume    = float(vols[i]   or 0) if i < len(vols)  else 0.0,
                        interval  = interval,
                    ))
                except Exception:
                    continue
            return bars
        except Exception as exc:
            log.debug("[DhanFeed] _parse_candles error: %s", exc)
            return []

    @staticmethod
    def _parse_option_chain(symbol: str, resp: Any, expiry: str) -> Optional[OptionsChain]:
        """Parse Dhan option_chain response → OptionsChain."""
        if not resp:
            return None
        try:
            data    = resp if isinstance(resp, dict) else {}
            # Dhan option_chain returns {"data": {"CE": {...}, "PE": {...}}, "underlying_price": ...}
            spot    = float(data.get("underlying_price", data.get("spot_price", 22500)))
            ce_data = data.get("data", {}).get("CE", {})
            pe_data = data.get("data", {}).get("PE", {})
            contracts: List[OptionsContract] = []
            total_call_oi = total_put_oi = 0.0

            for strike_str, ce in ce_data.items():
                strike = float(strike_str)
                oi = float(ce.get("OI", ce.get("oi", 0)) or 0)
                total_call_oi += oi
                contracts.append(OptionsContract(
                    symbol      = symbol,
                    expiry      = expiry,
                    strike      = strike,
                    option_type = "CE",
                    ltp         = float(ce.get("last_price", ce.get("LTP", 0)) or 0),
                    iv          = float(ce.get("impliedVolatility", ce.get("iv", 0)) or 0),
                    delta       = float(ce.get("delta", 0) or 0),
                    gamma       = float(ce.get("gamma", 0) or 0),
                    theta       = float(ce.get("theta", 0) or 0),
                    vega        = float(ce.get("vega",  0) or 0),
                    oi          = oi,
                    volume      = float(ce.get("volume", 0) or 0),
                    bid         = float(ce.get("bid_price", 0) or 0),
                    ask         = float(ce.get("ask_price", 0) or 0),
                ))

            for strike_str, pe in pe_data.items():
                strike = float(strike_str)
                oi = float(pe.get("OI", pe.get("oi", 0)) or 0)
                total_put_oi += oi
                contracts.append(OptionsContract(
                    symbol      = symbol,
                    expiry      = expiry,
                    strike      = strike,
                    option_type = "PE",
                    ltp         = float(pe.get("last_price", pe.get("LTP", 0)) or 0),
                    iv          = float(pe.get("impliedVolatility", pe.get("iv", 0)) or 0),
                    delta       = float(pe.get("delta", 0) or 0),
                    gamma       = float(pe.get("gamma", 0) or 0),
                    theta       = float(pe.get("theta", 0) or 0),
                    vega        = float(pe.get("vega",  0) or 0),
                    oi          = oi,
                    volume      = float(pe.get("volume", 0) or 0),
                    bid         = float(pe.get("bid_price", 0) or 0),
                    ask         = float(pe.get("ask_price", 0) or 0),
                ))

            pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0.85
            return OptionsChain(
                underlying = symbol,
                expiry     = expiry,
                spot_price = spot,
                timestamp  = datetime.now(),
                contracts  = contracts,
                pcr        = pcr,
                total_oi   = total_call_oi + total_put_oi,
            )
        except Exception as exc:
            log.debug("[DhanFeed] _parse_option_chain error: %s", exc)
            return None

    @staticmethod
    def _nearest_expiry() -> str:
        """Return the nearest Thursday (NSE weekly expiry) as YYYY-MM-DD."""
        today = date.today()
        days_until_thursday = (3 - today.weekday()) % 7   # 0=Mon … 3=Thu
        if days_until_thursday == 0 and today.weekday() == 3:
            pass   # today IS thursday
        next_thu = today + timedelta(days=days_until_thursday)
        return next_thu.strftime("%Y-%m-%d")

    # ── yfinance fallback ─────────────────────────────────────────────────

    def _yf_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Fetch OHLC quote from yfinance (used when Dhan Data API not subscribed)."""
        ticker_sym = _YF_TICKERS.get(symbol.upper())
        if not ticker_sym:
            return None
        try:
            import yfinance as yf  # type: ignore
            t   = yf.Ticker(ticker_sym)
            # 1-min intraday for today's OHLCV
            h   = t.history(period="1d", interval="1m", auto_adjust=False)
            if h.empty:
                return None
            ltp  = float(h["Close"].iloc[-1])
            opn  = float(h["Open"].iloc[0])
            high = float(h["High"].max())
            low  = float(h["Low"].min())
            vol  = float(h["Volume"].sum()) if "Volume" in h.columns else 0.0
            # Use actual prior trading day close (2d daily) as baseline
            # — avoids yfinance fast_info.previous_close adjustment errors
            try:
                h2   = t.history(period="2d", interval="1d", auto_adjust=False)
                prev = float(h2["Close"].iloc[-2]) if len(h2) >= 2 else ltp
            except Exception:
                prev = ltp
            change     = round(ltp - prev, 2)
            change_pct = round(change / prev * 100, 4) if prev else 0.0
            return TickerQuote(
                symbol     = symbol,
                timestamp  = datetime.now(),
                ltp        = round(ltp, 2),
                open       = round(opn, 2),
                high       = round(high, 2),
                low        = round(low, 2),
                close      = round(prev, 2),
                change     = change,
                change_pct = change_pct,
                volume     = vol,
            )
        except Exception as exc:
            log.debug("[DhanFeed] yf_quote(%s) error: %s", symbol, exc)
            return None

    def _yf_ltp(self, symbol: str) -> Optional[float]:
        """Fetch LTP-only from yfinance."""
        ticker_sym = _YF_TICKERS.get(symbol.upper())
        if not ticker_sym:
            return None
        try:
            import yfinance as yf  # type: ignore
            t = yf.Ticker(ticker_sym)
            h = t.history(period="1d", interval="1m", auto_adjust=False)
            if h.empty:
                return None
            return float(h["Close"].iloc[-1])
        except Exception as exc:
            log.debug("[DhanFeed] yf_ltp(%s) error: %s", symbol, exc)
            return None

    # ── Simulation fallback ───────────────────────────────────────────────

    def _sim_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Return a deterministic simulated quote (for dev/test)."""
        import random
        rng   = random.Random(hash(symbol) % 9999)
        base  = _SIM_PRICES.get(symbol.upper(), 1000.0)
        noise = rng.uniform(-0.5, 0.5) / 100
        ltp   = round(base * (1 + noise), 2)
        return TickerQuote(
            symbol     = symbol,
            timestamp  = datetime.now(),
            ltp        = ltp,
            open       = round(ltp * 0.995, 2),
            high       = round(ltp * 1.005, 2),
            low        = round(ltp * 0.990, 2),
            close      = round(ltp * 0.998, 2),
            change     = round(ltp * noise, 2),
            change_pct = round(noise * 100, 4),
            volume     = float(rng.randint(500_000, 5_000_000)),
        )

    def _sim_history(self, symbol: str, days: int) -> List[PriceBar]:
        """Return simulated daily bars for dev/test."""
        import random
        bars  = []
        base  = _SIM_PRICES.get(symbol.upper(), 1000.0)
        rng   = random.Random(hash(symbol) % 9999)
        price = base
        today = date.today()
        for d in range(days, -1, -1):
            dt = today - timedelta(days=d)
            if dt.weekday() >= 5:
                continue   # skip weekends
            chg   = rng.uniform(-1.5, 1.5) / 100
            open_ = round(price, 2)
            close = round(price * (1 + chg), 2)
            bars.append(PriceBar(
                symbol    = symbol,
                timestamp = datetime(dt.year, dt.month, dt.day, 15, 30),
                open      = open_,
                high      = round(max(open_, close) * 1.005, 2),
                low       = round(min(open_, close) * 0.995, 2),
                close     = close,
                volume    = float(rng.randint(500_000, 5_000_000)),
                interval  = "1d",
            ))
            price = close
        return bars[-days:]
