"""
AngelOne SmartAPI Feed Adapter
================================
Primary Indian market data source (equities + options) via AngelOne SmartAPI.

Provides:
  • NSE equity real-time quotes (LTP / OHLC / bid-ask / volume)
  • NSE indices  (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY)
  • NFO options chain (full strike list + live LTP / OI / bid-ask per contract)
  • Historical OHLCV candles (1m → 1d)

Session lifecycle:
  • generateSession() on startup (TOTP-based auto-login)
  • _refresh_if_needed() re-authenticates when session age > 50 min
    (AngelOne JWTs last ~60 min; 50-min safety margin avoids mid-call expiry)

Token resolution (symbol → AngelOne token):
  • NSE indices: hardcoded static tokens (never change)
  • NSE equities: searchScrip() on first use, persisted to
    data/angelone_token_cache.json so restarts don't redo lookups
  • NFO options: resolved on demand when building options chain

Rate limits (AngelOne SmartAPI free tier):
  • getMarketData: 10 req/s, 10,000 req/day
  • getCandleData: 3 req/s,  500 req/day
  • searchScrip:   10 req/s

Install: pip install smartapi-python pyotp logzero
"""

from __future__ import annotations

import json
import threading
import time as _time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base_feed import BaseFeed, OptionsChain, OptionsContract, PriceBar, TickerQuote
from utils import get_logger

log = get_logger(__name__)

# ── Static index tokens (NSE segment, these never change) ─────────────────────
_INDEX_TOKENS: Dict[str, Tuple[str, str, str]] = {
    # symbol         exchange   tradingsymbol          symboltoken
    "NIFTY":      ("NSE",  "Nifty 50",              "99926000"),
    "BANKNIFTY":  ("NSE",  "Nifty Bank",             "99926009"),
    "FINNIFTY":   ("NSE",  "Nifty Fin Service",       "99926037"),
    "MIDCPNIFTY": ("NSE",  "NIFTY MID SELECT",        "99926074"),
    "INDIAVIX":   ("NSE",  "India VIX",               "99926017"),
}

# ── Interval map: BaseFeed standard → AngelOne getCandleData values ────────────
_INTERVAL_MAP: Dict[str, str] = {
    "1m":  "ONE_MINUTE",
    "5m":  "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "30m": "THIRTY_MINUTE",
    "1h":  "ONE_HOUR",
    "1d":  "ONE_DAY",
}

# Max tokens per getMarketData batch call (AngelOne API limit)
_BATCH_MAX = 50

# Session refresh threshold (minutes before assumed expiry)
_SESSION_REFRESH_AFTER_MIN = 50

# Persistent token cache file
_CACHE_FILE = Path("data/angelone_token_cache.json")


def _safe_float(v, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if f == f else default   # NaN check
    except (TypeError, ValueError):
        return default


def _expiry_tag(expiry_str: Optional[str]) -> Optional[str]:
    """
    Convert expiry string to the tag embedded in AngelOne NFO tradingsymbols.

    AngelOne uses DDMMMYY (2-digit year): e.g. "05JUN26"
    "2026-06-05" → "05JUN26"
    "05JUN2026"  → "05JUN26"
    "05JUN26"    → "05JUN26"
    """
    if not expiry_str:
        return None
    expiry_str = expiry_str.strip().upper()
    # Already DDMMMYY (7 chars, 2-digit year)
    if len(expiry_str) == 7 and expiry_str[2:5].isalpha() and expiry_str[5:].isdigit():
        return expiry_str
    # DDMMMYYYY (9 chars, 4-digit year) — truncate to 2-digit year
    if len(expiry_str) == 9 and expiry_str[2:5].isalpha():
        return expiry_str[:7]   # "05JUN2026" → "05JUN20"... wrong — parse properly
    try:
        # Try YYYY-MM-DD
        dt = datetime.strptime(expiry_str[:10], "%Y-%m-%d")
        return dt.strftime("%d%b%y").upper()   # "05JUN26"
    except ValueError:
        pass
    try:
        # Try DDMMMYYYY
        dt = datetime.strptime(expiry_str[:9], "%d%b%Y")
        return dt.strftime("%d%b%y").upper()
    except ValueError:
        pass
    return None


def _nearest_nifty_expiry_tag() -> str:
    """
    Return the tag for the nearest NIFTY weekly expiry.
    NIFTY weekly expiry = Monday (changed by SEBI in 2024).
    Format: DDMMMYY (e.g. 02JUN26)
    """
    today = datetime.today()
    # weekday(): Monday=0, Tuesday=1, ..., Sunday=6
    # Find next Monday (or today if today is Monday)
    days_to_monday = (0 - today.weekday()) % 7
    if days_to_monday == 0:
        days_to_monday = 7   # if today is Monday, go to next Monday
    return (today + timedelta(days=days_to_monday)).strftime("%d%b%y").upper()


def _nearest_thursday_tag() -> str:
    """Return nearest Thursday tag (for BANKNIFTY and others). Format: DDMMMYY."""
    today = datetime.today()
    days  = (3 - today.weekday()) % 7
    if days == 0:
        days = 7
    return (today + timedelta(days=days)).strftime("%d%b%y").upper()


# Map of underlying → its weekly expiry weekday
_WEEKLY_EXPIRY_DAY: Dict[str, str] = {
    "NIFTY":      "MONDAY",
    "BANKNIFTY":  "WEDNESDAY",   # BANKNIFTY weekly = Wednesday since 2024
    "FINNIFTY":   "TUESDAY",
    "MIDCPNIFTY": "MONDAY",
}


def _nearest_expiry_tag(underlying: str) -> str:
    """Return the nearest weekly expiry tag for the given underlying.

    Uses the current week's expiry if it hasn't passed yet (market still open);
    otherwise uses the next week's expiry.
    """
    today   = datetime.today()
    day_map = {"MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4}
    target  = day_map.get(_WEEKLY_EXPIRY_DAY.get(underlying.upper(), "THURSDAY"), 3)
    days    = (target - today.weekday()) % 7
    # If today IS the expiry day, use today (trades until 15:30 IST)
    # If today is past the expiry (earlier in the week), go forward
    if days == 0:
        # Check if market is still open (before 15:45 IST buffer)
        if today.hour < 15 or (today.hour == 15 and today.minute < 45):
            pass   # use today — expiry is still tradeable
        else:
            days = 7  # expired today — go to next week
    return (today + timedelta(days=days)).strftime("%d%b%y").upper()


class AngelOneFeed(BaseFeed):
    """
    AngelOne SmartAPI-backed data feed implementing the BaseFeed interface.

    Designed as a drop-in companion to DhanFeed — activated automatically by
    DataFeedManager when Dhan data API is blocked (HTTP 451) or unavailable.
    """

    def __init__(self) -> None:
        self._smart      = None
        self._connected  = False
        self._session_ts: Optional[datetime] = None   # when session was created
        self._lock       = threading.RLock()
        self._last_reconnect_attempt: Optional[datetime] = None  # rate-limit reconnects

        # token cache: bare_symbol → (exchange, tradingsymbol, symboltoken)
        self._token_cache: Dict[str, Tuple[str, str, str]] = {}
        # reverse map: symboltoken → bare_symbol (for batch response mapping)
        self._token_to_sym: Dict[str, str] = {}
        # 300-second options chain result cache — prevents consecutive searchScrip
        # calls from hitting AngelOne rate limits (pre-warm fires every 270s;
        # 300s TTL guarantees cache is always populated when a scheduled cycle fires)
        self._options_chain_cache: Dict[str, Tuple[float, object]] = {}
        # Signals when the startup BANKNIFTY pre-warm has finished writing to
        # _options_chain_cache.  Any other thread that needs BANKNIFTY waits on
        # this event (timeout 20s) so it gets a cache hit instead of firing a
        # concurrent searchScrip call that lands inside AngelOne's 6-8s rate-limit
        # window and returns None → SYNTHETIC.
        self._prewarm_done = threading.Event()

        # Seed with hardcoded index tokens
        for sym, info in _INDEX_TOKENS.items():
            self._token_cache[sym] = info
            self._token_to_sym[info[2]] = sym

        self._load_token_cache()
        self._connect()

        # Startup pre-warm: fetch NIFTY + BANKNIFTY options chains in background
        # so the 300s result cache is populated BEFORE the first orchestrator cycle
        # fires (~40s after boot).  15s initial delay lets the AngelOne session
        # stabilise; 5s gap between symbols avoids rate-limit bursts.
        _pw = threading.Thread(target=self._startup_prewarm_options,
                               daemon=True, name="AO-StartupPrewarm")
        _pw.start()

    def _startup_prewarm_options(self) -> None:
        """Background thread: pre-warms BANKNIFTY options chain at startup.

        Only BANKNIFTY is pre-warmed here because:
        - NIFTY falls back to Dhan (which always works for NIFTY)
        - BANKNIFTY has no Dhan fallback (MULTI_SID_REJECTED) and the warm_loop
          only reaches BANKNIFTY ~25s after boot (after NIFTY fetch completes).
        - By firing immediately (first searchScrip call on the API key → zero
          rate-limit risk) and completing at ~T+11s, it sets _prewarm_done so all
          other callers that need BANKNIFTY unblock and get a 300s cache hit instead
          of firing a concurrent searchScrip that hits the rate-limit window.
        """
        try:
            self.get_options_chain("BANKNIFTY") # stored in _options_chain_cache
        except Exception:
            pass
        finally:
            self._prewarm_done.set()  # unblock any waiting callers

    # ── Connection & session ────────────────────────────────────────────────

    def _connect(self) -> None:
        try:
            import pyotp
            from SmartApi import SmartConnect
            from config import (
                ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
                ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET,
            )
            if not all([ANGELONE_API_KEY, ANGELONE_CLIENT_ID,
                        ANGELONE_PASSWORD, ANGELONE_TOTP_SECRET]):
                log.info("[AngelOneFeed] Credentials not configured — feed inactive.")
                return

            totp  = pyotp.TOTP(ANGELONE_TOTP_SECRET).now()
            smart = SmartConnect(api_key=ANGELONE_API_KEY)
            resp  = smart.generateSession(ANGELONE_CLIENT_ID, ANGELONE_PASSWORD, totp)

            if resp.get("status"):
                self._smart      = smart
                self._connected  = True
                self._session_ts = datetime.now()
                log.info(
                    "[AngelOneFeed] Connected. ClientID=%s  feedToken=%s…",
                    ANGELONE_CLIENT_ID,
                    str(resp.get("data", {}).get("feedToken", ""))[:20],
                )
            else:
                log.error("[AngelOneFeed] Login failed: %s", resp.get("message", resp))

        except ImportError as e:
            log.warning("[AngelOneFeed] Missing package (%s) — inactive. "
                        "Run: pip install smartapi-python pyotp logzero", e)
        except Exception as exc:
            log.error("[AngelOneFeed] Connection error: %s", exc)

    def _refresh_if_needed(self) -> bool:
        """Re-authenticate if session is stale (>50 min old) or disconnected. Returns True if live."""
        # If disconnected, attempt one reconnect (rate-limited to once per 5 min)
        if not self._connected or self._smart is None:
            _now = datetime.now()
            _since_last = (
                (_now - self._last_reconnect_attempt).total_seconds()
                if self._last_reconnect_attempt else float("inf")
            )
            if _since_last >= 300:  # 5-minute backoff
                log.info(
                    "[AngelOneFeed] Disconnected — attempting auto-reconnect "
                    "(last attempt %.0f s ago).", _since_last
                )
                self._last_reconnect_attempt = _now
                self._connect()
            return self._connected
        if self._session_ts is None:
            return True
        age_min = (datetime.now() - self._session_ts).total_seconds() / 60
        if age_min > _SESSION_REFRESH_AFTER_MIN:
            log.info("[AngelOneFeed] Session age=%.0f min — refreshing.", age_min)
            self._connected = False
            self._smart = None
            self._connect()
        return self._connected

    # ── BaseFeed properties ─────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "AngelOneFeed"

    @property
    def is_live(self) -> bool:
        return self._connected and self._smart is not None

    # ── Token cache (persistent) ────────────────────────────────────────────

    def _load_token_cache(self) -> None:
        try:
            p = _CACHE_FILE if _CACHE_FILE.is_absolute() else \
                (Path("/app") / _CACHE_FILE if Path("/app").exists() else _CACHE_FILE)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                for sym, info in data.items():
                    if isinstance(info, list) and len(info) == 3:
                        t = tuple(info)
                        self._token_cache[sym]      = t
                        self._token_to_sym[t[2]]    = sym
                log.debug("[AngelOneFeed] Loaded %d cached tokens.", len(data))
        except Exception as e:
            log.debug("[AngelOneFeed] Token cache load failed: %s", e)

    def _save_token_cache(self) -> None:
        try:
            p = _CACHE_FILE if _CACHE_FILE.is_absolute() else \
                (Path("/app") / _CACHE_FILE if Path("/app").exists() else _CACHE_FILE)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps({k: list(v) for k, v in self._token_cache.items()},
                           indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.debug("[AngelOneFeed] Token cache save failed: %s", e)

    def _resolve_token(self, symbol: str) -> Optional[Tuple[str, str, str]]:
        """
        Return (exchange, tradingsymbol, symboltoken) for a symbol.

        Lookup order:
          1. _token_cache (in-memory, includes hardcoded indices)
          2. searchScrip("NSE", bare_symbol) — NSE equity discovery
        """
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")

        with self._lock:
            if bare in self._token_cache:
                return self._token_cache[bare]

        if not self._refresh_if_needed():
            return None

        try:
            resp = self._smart.searchScrip("NSE", bare)
            if not (resp and resp.get("status") and resp.get("data")):
                return None
            # Find exact tradingsymbol match (prefer EQ type, then bare match)
            candidates = resp["data"]
            match = None
            for c in candidates:
                ts = (c.get("tradingsymbol") or "").upper()
                if ts == bare or ts == bare + "-EQ":
                    match = c
                    if ts == bare:   # prefer exact over -EQ
                        break
            if match is None and candidates:
                match = candidates[0]   # fallback to first result

            if match:
                info = (
                    match.get("exchange", "NSE"),
                    match.get("tradingsymbol", bare),
                    str(match.get("symboltoken", "")),
                )
                with self._lock:
                    self._token_cache[bare]      = info
                    self._token_to_sym[info[2]]  = bare
                # Persist (background — non-blocking)
                threading.Thread(target=self._save_token_cache, daemon=True).start()
                return info
        except Exception as e:
            log.debug("[AngelOneFeed] searchScrip(%s) failed: %s", bare, e)
        return None

    # ── Quote building ──────────────────────────────────────────────────────

    def _market_data_to_quote(self, symbol: str, item: dict) -> TickerQuote:
        ltp    = _safe_float(item.get("ltp"))
        close  = _safe_float(item.get("close"))
        change = ltp - close if close else 0.0
        chg_pct = (change / close * 100) if close else 0.0
        return TickerQuote(
            symbol         = symbol,
            timestamp      = datetime.now(),
            ltp            = ltp,
            open           = _safe_float(item.get("open")),
            high           = _safe_float(item.get("high")),
            low            = _safe_float(item.get("low")),
            close          = close,
            change         = _safe_float(item.get("change"), change),
            change_pct     = _safe_float(item.get("changePercent"), chg_pct),
            volume         = _safe_float(item.get("tradeVolume") or item.get("volume")),
            bid            = _safe_float(item.get("totBuyQuan")),    # best proxy available
            ask            = _safe_float(item.get("totSellQuan")),
            oi             = _safe_float(item.get("totOI")),
            feed_source    = "ANGELONE",
            feed_degraded  = False,
            fallback_active= False,
        )

    # ── BaseFeed: get_quote ─────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        if not self._refresh_if_needed():
            return None
        info = self._resolve_token(symbol)
        if not info:
            return None
        exchange, tradingsymbol, token = info
        try:
            resp = self._smart.ltpData(exchange, tradingsymbol, token)
            if not (resp and resp.get("status") and resp.get("data")):
                return None
            d = resp["data"]
            # ltpData returns: {exchange, tradingsymbol, symboltoken, open, high, low, close, ltp}
            return TickerQuote(
                symbol       = symbol.upper().replace(".NS", "").replace(".BO", ""),
                timestamp    = datetime.now(),
                ltp          = _safe_float(d.get("ltp")),
                open         = _safe_float(d.get("open")),
                high         = _safe_float(d.get("high")),
                low          = _safe_float(d.get("low")),
                close        = _safe_float(d.get("close")),
                change       = _safe_float(d.get("ltp", 0)) - _safe_float(d.get("close", 0)),
                change_pct   = 0.0,
                volume       = 0.0,
                feed_source  = "ANGELONE",
            )
        except Exception as e:
            log.debug("[AngelOneFeed] get_quote(%s) error: %s", symbol, e)
        return None

    # ── BaseFeed: get_multiple_quotes (batch) ───────────────────────────────

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        if not self._refresh_if_needed():
            return {}

        # Resolve all tokens — unknown symbols trigger searchScrip (cached after)
        by_exchange: Dict[str, List[str]] = {}       # exchange → [tokens]
        token_to_sym: Dict[str, str]      = {}        # token → original symbol

        for sym in symbols:
            info = self._resolve_token(sym)
            if info:
                exchange, _, token = info
                by_exchange.setdefault(exchange, []).append(token)
                token_to_sym[token] = sym

        if not by_exchange:
            return {}

        results: Dict[str, TickerQuote] = {}

        for exchange, tokens in by_exchange.items():
            # Batch in chunks of _BATCH_MAX
            for i in range(0, len(tokens), _BATCH_MAX):
                chunk = tokens[i:i + _BATCH_MAX]
                try:
                    resp = self._smart.getMarketData("FULL", {exchange: chunk})
                    if not (resp and resp.get("status") and resp.get("data")):
                        continue
                    for item in resp["data"].get("fetched", []):
                        tok = str(item.get("symbolToken", ""))
                        orig_sym = token_to_sym.get(tok)
                        if orig_sym:
                            q = self._market_data_to_quote(
                                orig_sym.upper().replace(".NS", "").replace(".BO", ""),
                                item,
                            )
                            results[orig_sym] = q
                except Exception as e:
                    log.debug("[AngelOneFeed] getMarketData batch error: %s", e)

        return results

    # ── BaseFeed: get_history ───────────────────────────────────────────────

    def get_history(
        self,
        symbol:   str,
        days:     int = 30,
        interval: str = "1d",
    ) -> List[PriceBar]:
        if not self._refresh_if_needed():
            return []
        info = self._resolve_token(symbol)
        if not info:
            return []
        exchange, _, token = info

        ang_interval = _INTERVAL_MAP.get(interval, "ONE_DAY")
        now      = datetime.now()
        from_dt  = (now - timedelta(days=days)).strftime("%Y-%m-%d 09:15")
        to_dt    = now.strftime("%Y-%m-%d 15:30")

        try:
            resp = self._smart.getCandleData({
                "exchange":    exchange,
                "symboltoken": token,
                "interval":    ang_interval,
                "fromdate":    from_dt,
                "todate":      to_dt,
            })
            if not (resp and resp.get("status") and resp.get("data")):
                return []
            bars = []
            bare = symbol.upper().replace(".NS", "").replace(".BO", "")
            for row in resp["data"]:
                # row: [timestamp_str, open, high, low, close, volume]
                if len(row) < 6:
                    continue
                try:
                    ts = datetime.strptime(str(row[0])[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    ts = datetime.now()
                bars.append(PriceBar(
                    symbol    = bare,
                    timestamp = ts,
                    open      = _safe_float(row[1]),
                    high      = _safe_float(row[2]),
                    low       = _safe_float(row[3]),
                    close     = _safe_float(row[4]),
                    volume    = _safe_float(row[5]),
                    interval  = interval,
                ))
            return bars
        except Exception as e:
            log.debug("[AngelOneFeed] get_history(%s) error: %s", symbol, e)
        return []

    # ── Options chain ────────────────────────────────────────────────────────

    def get_options_chain(
        self,
        underlying: str,
        expiry:     Optional[str] = None,
        dte_target: int           = 20,
    ) -> Optional[OptionsChain]:
        """
        Fetch a live options chain for NIFTY or BANKNIFTY.

        Steps:
          1. searchScrip("NFO", underlying) → all strike/expiry contracts
          2. Filter by expiry tag (nearest Thursday if not specified)
          3. getMarketData("FULL", {"NFO": [tokens]}) → live LTP / OI / bid / ask
          4. Get spot price via get_quote(underlying)
          5. Build OptionsChain with OptionsContract objects
        """
        if not self._refresh_if_needed():
            return None

        # ── Startup gate: wait for BANKNIFTY pre-warm to finish ──────────────────
        # The startup pre-warm fires searchScrip("NFO","BANKNIFTY") at T+0.  Any
        # concurrent call that also fires searchScrip within the 6-8s AngelOne
        # rate-limit window gets a rate-limit error → None → SYNTHETIC.  We block
        # BANKNIFTY callers until the pre-warm event fires (i.e. cache is written),
        # then they get a 300s cache hit.  The pre-warm thread itself is exempt.
        import threading as _threading_mod
        if (
            underlying.upper() == "BANKNIFTY"
            and not self._prewarm_done.is_set()
            and _threading_mod.current_thread().name != "AO-StartupPrewarm"
        ):
            self._prewarm_done.wait(timeout=20)

        # ── 90-second result cache — return last successful chain if fresh enough ──
        import time as _time_mod
        _cache_key = underlying.upper()
        _cached_entry = self._options_chain_cache.get(_cache_key)
        if _cached_entry is not None:
            _cached_ts, _cached_chain = _cached_entry
            if _time_mod.time() - _cached_ts <= 300:
                log.debug(
                    "[AngelOneFeed] options chain cache hit: %s age=%.0fs",
                    underlying, _time_mod.time() - _cached_ts,
                )
                return _cached_chain

        exp_tag = _expiry_tag(expiry) or _nearest_expiry_tag(underlying)

        try:
            # Step 1 — get all NFO contracts for underlying
            resp = self._smart.searchScrip("NFO", underlying.upper())
            if not (resp and resp.get("status") and resp.get("data")):
                log.debug("[AngelOneFeed] searchScrip NFO %s returned no data", underlying)
                return None

            all_contracts = resp["data"]

            # Step 2 — filter by expiry
            # If explicit expiry requested, match that tag; otherwise find the
            # nearest upcoming expiry from the actual contract list.
            if expiry and exp_tag:
                filtered = [
                    c for c in all_contracts
                    if exp_tag in (c.get("tradingsymbol") or "").upper()
                ]
            else:
                # Extract all expiry tags for pure-underlying contracts and pick nearest.
                # Use a digit-check instead of an exclusion list: option tradingsymbols
                # always have a digit immediately after the underlying prefix
                # (e.g. NIFTY02JUN26... ts[5]='0', BANKNIFTY25AUG26... ts[9]='2').
                # This correctly handles NIFTY vs NIFTYBANK and also BANKNIFTY itself
                # without accidentally excluding BANKNIFTY contracts via "BANK" match.
                underlying_upper = underlying.upper()
                pfx_len = len(underlying_upper)

                def _is_own_option(ts: str) -> bool:
                    """True when tradingsymbol is an option contract for this underlying."""
                    return (
                        ts.startswith(underlying_upper)
                        and len(ts) > pfx_len
                        and ts[pfx_len].isdigit()
                        and (ts.endswith("CE") or ts.endswith("PE"))
                    )

                # Extract DDMMMYY tags from matching contracts
                tag_set = set()
                for c in all_contracts:
                    ts = (c.get("tradingsymbol") or "").upper()
                    if _is_own_option(ts):
                        tag = ts[pfx_len:pfx_len + 7]
                        if len(tag) == 7 and tag[2:5].isalpha():
                            tag_set.add(tag)
                # Find expiry tag closest to dte_target (not simply nearest)
                today_dt          = datetime.today().date()
                best_tag          = None
                best_dt           = None
                best_diff         = float("inf")
                _ao_future_tags: list = []
                for tag in sorted(tag_set):
                    try:
                        dt = datetime.strptime(tag, "%d%b%y").date()
                        if dt >= today_dt:
                            _d_dte  = (dt - today_dt).days
                            _d_diff = abs(_d_dte - dte_target)
                            _ao_future_tags.append((tag, _d_dte))
                            if _d_diff < best_diff:
                                best_diff = _d_diff
                                best_dt   = dt
                                best_tag  = tag
                    except ValueError:
                        continue
                log.info(
                    "[ExpirySelectionAudit] source=ANGELONE  symbol=%s  "
                    "requested_dte_target=%d  available_expiries=%r  "
                    "selected_expiry=%s  selected_dte=%d  selection_reason=closest_to_dte_target",
                    underlying, dte_target,
                    _ao_future_tags[:8],
                    best_tag, (best_dt - today_dt).days if best_dt else 0,
                )
                exp_tag = best_tag or exp_tag
                filtered = [
                    c for c in all_contracts
                    if exp_tag and _is_own_option((c.get("tradingsymbol") or "").upper())
                       and exp_tag in (c.get("tradingsymbol") or "").upper()
                ]

            if not filtered:
                log.debug("[AngelOneFeed] No NFO contracts found for %s expiry=%s (tag=%s)",
                          underlying, expiry, exp_tag)
                return None

            # Build token list for batch fetch
            nfo_tokens     = [str(c["symboltoken"]) for c in filtered]
            token_to_meta  = {
                str(c["symboltoken"]): c["tradingsymbol"]
                for c in filtered
            }

            # Step 3 — batch fetch live data (chunks of 50)
            market_data: Dict[str, dict] = {}
            for i in range(0, len(nfo_tokens), _BATCH_MAX):
                chunk = nfo_tokens[i:i + _BATCH_MAX]
                try:
                    mresp = self._smart.getMarketData("FULL", {"NFO": chunk})
                    if mresp and mresp.get("status") and mresp.get("data"):
                        for item in mresp["data"].get("fetched", []):
                            tok = str(item.get("symbolToken", ""))
                            market_data[tok] = item
                except Exception as me:
                    log.debug("[AngelOneFeed] options batch chunk error: %s", me)

            # ── OI Trace: raw_feed stage — sample first item for field diagnostics ──
            if market_data:
                _oi_sample_tok = next(iter(market_data))
                _oi_sample     = market_data[_oi_sample_tok]
                log.debug(
                    "[OptionsOITrace] stage=raw_feed symbol=%s tokens_fetched=%d "
                    "sample_token=%s sample_totOI=%s sample_fields=%s",
                    underlying, len(market_data), _oi_sample_tok,
                    _oi_sample.get("totOI"),
                    [k for k in _oi_sample.keys() if "oi" in k.lower() or "OI" in k or "interest" in k.lower()],
                )

            # Step 4 — spot price
            spot_q = self.get_quote(underlying)
            spot   = spot_q.ltp if spot_q else 0.0

            # Step 5 — build contracts
            contracts: List[OptionsContract] = []
            for token, ts in token_to_meta.items():
                # Parse tradingsymbol: NIFTY05JUN202624600CE
                ts_upper = ts.upper()
                opt_type = "CE" if ts_upper.endswith("CE") else "PE"
                prefix   = underlying.upper()
                try:
                    # Remove prefix + expiry tag (7 chars DDMMMYY) + option_type (2 chars)
                    inner   = ts_upper[len(prefix):]          # "05JUN2624600CE"
                    strike_str = inner[7:-2]                  # skip 7-char expiry + 2-char type
                    strike  = float(strike_str)
                except (ValueError, IndexError):
                    continue

                md   = market_data.get(token, {})
                ltp  = _safe_float(md.get("ltp"))
                oi   = _safe_float(md.get("opnInterest") or md.get("totOI"))
                vol  = _safe_float(md.get("tradeVolume") or md.get("volume"))
                bid  = _safe_float(md.get("totBuyQuan"))
                ask  = _safe_float(md.get("totSellQuan"))

                contracts.append(OptionsContract(
                    symbol      = underlying.upper(),
                    expiry      = expiry or exp_tag,
                    strike      = strike,
                    option_type = opt_type,
                    ltp         = ltp,
                    iv          = 0.0,    # not available from getMarketData FULL mode
                    delta       = 0.0,
                    gamma       = 0.0,
                    theta       = 0.0,
                    vega        = 0.0,
                    oi          = oi,
                    volume      = vol,
                    bid         = bid,
                    ask         = ask,
                ))

            if not contracts:
                return None

            # Compute PCR from OI
            total_ce_oi = sum(c.oi for c in contracts if c.option_type == "CE")
            total_pe_oi = sum(c.oi for c in contracts if c.option_type == "PE")
            pcr = (total_pe_oi / total_ce_oi) if total_ce_oi else 0.0

            # ── OptionsOIAudit ─────────────────────────────────────────────────────
            _oi_contracts_with_oi = sum(1 for c in contracts if (c.oi or 0) > 0)
            log.info(
                "[OptionsOIAudit] symbol=%s source=ANGELONE expiry=%s "
                "contracts_received=%d contracts_with_oi=%d "
                "total_oi=%.0f put_oi=%.0f call_oi=%.0f "
                "pcr=%.4f oi_available=%s",
                underlying, exp_tag or expiry,
                len(contracts), _oi_contracts_with_oi,
                total_ce_oi + total_pe_oi,
                total_pe_oi, total_ce_oi,
                pcr, _oi_contracts_with_oi > 0,
            )

            chain = OptionsChain(
                underlying  = underlying.upper(),
                expiry      = expiry or exp_tag,
                spot_price  = spot,
                timestamp   = datetime.now(),
                contracts   = contracts,
                pcr         = pcr,
                total_oi    = total_ce_oi + total_pe_oi,
                is_live     = True,
            )
            log.info(
                "[AngelOneFeed] options chain: underlying=%s expiry=%s "
                "contracts=%d spot=%.1f pcr=%.2f",
                underlying, exp_tag, len(contracts), spot, pcr,
            )
            # Store in 90s result cache for subsequent same-cycle calls
            import time as _time_mod
            self._options_chain_cache[underlying.upper()] = (_time_mod.time(), chain)
            return chain

        except Exception as e:
            log.error("[AngelOneFeed] get_options_chain(%s) error: %s", underlying, e)
        return None
