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
    "INFY":          {"security_id": "1594",  "segment": "NSE_EQ", "itype": "EQUITY"},  # was 10604 (=BHARTIARTL) — corrected
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
    "BHARTIARTL":    {"security_id": "10604", "segment": "NSE_EQ", "itype": "EQUITY"},  # was 317 (=BAJFINANCE duplicate) — corrected
    "SUNPHARMA":     {"security_id": "3351",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "TITAN":         {"security_id": "3506",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "NESTLEIND":     {"security_id": "17963", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ULTRACEMCO":    {"security_id": "11532", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ASIANPAINT":    {"security_id": "236",   "segment": "NSE_EQ", "itype": "EQUITY"},
    "TECHM":         {"security_id": "13538", "segment": "NSE_EQ", "itype": "EQUITY"},
    "POWERGRID":     {"security_id": "14977", "segment": "NSE_EQ", "itype": "EQUITY"},
    "NTPC":          {"security_id": "11630", "segment": "NSE_EQ", "itype": "EQUITY"},
    "ONGC":          {"security_id": "2475",  "segment": "NSE_EQ", "itype": "EQUITY"},  # was 11654 (=LALPATHLAB) — corrected
    "HCLTECH":       {"security_id": "7229",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "ADANIENT":      {"security_id": "25",    "segment": "NSE_EQ", "itype": "EQUITY"},
    "JSWSTEEL":      {"security_id": "11723", "segment": "NSE_EQ", "itype": "EQUITY"},
    # Post-demerger (2024): NSE ticker TATAMOTORS retired. Two successors created:
    #   TMPV (Passenger Vehicles) = security_id 3456  — NOT the primary successor
    #   TMCV (Commercial Vehicles, "Tata Motors Limited") = security_id 759782  ← correct
    # Maps to TMCV so legacy TATAMOTORS positions get correct Tata Motors Ltd prices.
    "TATAMOTORS":    {"security_id": "759782", "segment": "NSE_EQ", "itype": "EQUITY"},  # was 3456 (=TMPV spin-off) — corrected to TMCV
    "TATASTEEL":     {"security_id": "3499",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "M&M":           {"security_id": "2031",  "segment": "NSE_EQ", "itype": "EQUITY"},
    # Explicitly mapped to avoid wrong _extra_map dynamic resolution (cross-validated vs security_id_list.csv)
    "HINDALCO":      {"security_id": "1363",  "segment": "NSE_EQ", "itype": "EQUITY"},  # NSE:1363
    "COALINDIA":     {"security_id": "20374", "segment": "NSE_EQ", "itype": "EQUITY"},  # NSE:20374

    # ── Extended watchlist coverage (all verified from security_id_list.csv) ──
    "BANKBARODA":    {"security_id": "4668",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "BAJAJFINSV":    {"security_id": "16675", "segment": "NSE_EQ", "itype": "EQUITY"},
    "DIVISLAB":      {"security_id": "10940", "segment": "NSE_EQ", "itype": "EQUITY"},
    "DRREDDY":       {"security_id": "881",   "segment": "NSE_EQ", "itype": "EQUITY"},
    "TATACONSUM":    {"security_id": "3432",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "HAVELLS":       {"security_id": "9819",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "PIDILITIND":    {"security_id": "2664",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "GRASIM":        {"security_id": "1232",  "segment": "NSE_EQ", "itype": "EQUITY"},
    "ADANIPORTS":    {"security_id": "15083", "segment": "NSE_EQ", "itype": "EQUITY"},
}

# ── All symbols that the system may scan / trade — used for coverage audit ──
# Any symbol absent from DHAN_SECURITY_MAP triggers a [MISSING_DHAN_MAPPING] warning
# at startup so silent Yahoo/sim fallback is never invisible.
_ALL_WATCHLIST_SYMBOLS: frozenset = frozenset({
    # _BASE_WATCHLIST
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY", "BANKBARODA",
    "LT", "COALINDIA", "HCLTECH", "SBIN", "AXISBANK", "ONGC", "KOTAKBANK",
    "BHARTIARTL", "ITC", "BAJAJFINSV", "HINDALCO", "ULTRACEMCO", "TECHM", "NTPC",
    # _EXTENDED_WATCHLIST
    "HINDUNILVR", "ASIANPAINT", "BAJFINANCE", "MARUTI", "SUNPHARMA", "WIPRO",
    "POWERGRID", "DIVISLAB", "TITAN", "DRREDDY", "ADANIENT", "TATACONSUM",
    "NESTLEIND", "HAVELLS", "PIDILITIND", "GRASIM", "JSWSTEEL", "ADANIPORTS",
    # Indices
    "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY", "INDIAVIX",
})

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
    # Indices
    "NIFTY":       "^NSEI",
    "BANKNIFTY":   "^NSEBANK",
    "INDIAVIX":    "^INDIAVIX",
    "FINNIFTY":    "NIFTY_FIN_SERVICE.NS",
    "MIDCAPNIFTY": "^NSEMDCP50",
    "SENSEX":      "^BSESN",
    "USDINR":      "USDINR=X",
    "SGXNIFTY":    "^NSEI",
    "GOLD":        "GC=F",
    # NSE Large-Cap Equities (all mapped to SYMBOL.NS for yfinance)
    "HDFCBANK":    "HDFCBANK.NS",
    "RELIANCE":    "RELIANCE.NS",
    "TCS":         "TCS.NS",
    "INFY":        "INFY.NS",
    "ICICIBANK":   "ICICIBANK.NS",
    "KOTAKBANK":   "KOTAKBANK.NS",
    "HINDUNILVR":  "HINDUNILVR.NS",
    "ITC":         "ITC.NS",
    "SBIN":        "SBIN.NS",
    "AXISBANK":    "AXISBANK.NS",
    "LT":          "LT.NS",
    "WIPRO":       "WIPRO.NS",
    "BAJFINANCE":  "BAJFINANCE.NS",
    "MARUTI":      "MARUTI.NS",
    "BHARTIARTL":  "BHARTIARTL.NS",
    "SUNPHARMA":   "SUNPHARMA.NS",
    "TITAN":       "TITAN.NS",
    "NESTLEIND":   "NESTLEIND.NS",
    "ULTRACEMCO":  "ULTRACEMCO.NS",
    "ASIANPAINT":  "ASIANPAINT.NS",
    "TECHM":       "TECHM.NS",
    "POWERGRID":   "POWERGRID.NS",
    "NTPC":        "NTPC.NS",
    "ONGC":        "ONGC.NS",
    "HCLTECH":     "HCLTECH.NS",
    "ADANIENT":    "ADANIENT.NS",
    "JSWSTEEL":    "JSWSTEEL.NS",
    "TATAMOTORS":  "TATAMOTORS.NS",
    "TATASTEEL":   "TATASTEEL.NS",
    "M&M":         "M&M.NS",
    "HINDALCO":    "HINDALCO.NS",
    "COALINDIA":   "COALINDIA.NS",
    "BANKBARODA":  "BANKBARODA.NS",
    "BAJAJFINSV":  "BAJAJFINSV.NS",
    "DIVISLAB":    "DIVISLAB.NS",
    "DRREDDY":     "DRREDDY.NS",
    "TATACONSUM":  "TATACONSUM.NS",
    "HAVELLS":     "HAVELLS.NS",
    "PIDILITIND":  "PIDILITIND.NS",
    "GRASIM":      "GRASIM.NS",
    "ADANIPORTS":  "ADANIPORTS.NS",
}

# ── Simulation fallback prices (approximate; only used if yfinance also fails) ─
_SIM_PRICES: Dict[str, float] = {
    "NIFTY": 23987.0, "BANKNIFTY": 56064.0, "FINNIFTY": 26071.0,
    "MIDCAPNIFTY": 13055.0, "INDIAVIX": 20.8, "USDINR": 86.5,
    "HDFCBANK": 1900.0, "RELIANCE": 1320.0, "TCS": 3800.0,
    "INFY": 1750.0, "ICICIBANK": 1380.0, "SBIN": 820.0,
    "WIPRO": 300.0, "BAJFINANCE": 8900.0,
    # NSE equities — approximate; used only when yfinance also unavailable
    "COALINDIA": 468.0, "HINDALCO": 720.0, "BHARTIARTL": 1830.0,
    "ITC": 430.0, "TATAMOTORS": 900.0, "TATASTEEL": 165.0,
    "NTPC": 380.0, "M&M": 3000.0, "AXISBANK": 1200.0,
    "KOTAKBANK": 2200.0, "BAJAJFINSV": 1900.0, "TITAN": 3600.0,
    "SUNPHARMA": 1900.0, "ULTRACEMCO": 11000.0, "ASIANPAINT": 2400.0,
    "TECHM": 1700.0, "NESTLEIND": 2300.0, "POWERGRID": 340.0,
    "ONGC": 270.0, "HCLTECH": 1700.0, "ADANIENT": 2800.0,
    "JSWSTEEL": 1050.0, "TATACONSUM": 1100.0, "HINDUNILVR": 2400.0,
    "MARUTI": 12000.0, "LT": 3800.0, "HAVELLS": 1700.0,
    "PIDILITIND": 3100.0, "GRASIM": 2900.0, "ADANIPORTS": 1450.0,
    "BANKBARODA": 260.0, "DIVISLAB": 6000.0, "DRREDDY": 7500.0,
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
        # ── Token lifecycle tracking ──────────────────────────────────────
        self._token_present:   bool           = False
        self._token_expires_at: Optional[float] = None   # Unix timestamp
        self._token_issued_at:  Optional[float] = None   # Unix timestamp
        # Token warning governance — fire once at ≤30 min, suppress after that
        self._token_warn_sent: bool = False
        # Circuit breaker: count consecutive data-API failures (401/failure)
        self._dhan_consecutive_failures: int = 0
        self._DHAN_CIRCUIT_OPEN_AFTER:   int = 5   # trips after N consecutive failures

        # ── Forensic Dhan telemetry (Phases 1–7) ─────────────────────────
        # Phase 3: per-endpoint failure type counters
        self._dhan_failure_counts: Dict[str, Dict[str, int]] = {}
        # Phase 7: cumulative success/attempt counters
        self._dhan_equity_attempts:  int = 0
        self._dhan_equity_successes: int = 0
        self._dhan_opt_attempts:     int = 0
        self._dhan_opt_successes:    int = 0
        # Auto-reconnect: recreate SDK client after this many consecutive opt failures.
        # Keyed per symbol so NIFTY successes do NOT reset BANKNIFTY's counter.
        self._dhan_opt_consecutive_failures: Dict[str, int] = {}
        self._OPT_RECONNECT_THRESHOLD:       int = 3   # reconnect after 3 consecutive opt failures per symbol
        # Phase 5: how many times Dhan data was missing → Yahoo fallback used
        self._dhan_fallback_events:  int = 0
        # Phase 2: last readiness probe result dict
        self._readiness_probe_result: Optional[dict] = None
        # Phase 4: per time-window failure/success counts
        self._window_failure_counts: Dict[str, Dict[str, int]] = {}
        self._window_success_counts: Dict[str, Dict[str, int]] = {}

        # ── Phase 9: Runtime-mode truth tracking ─────────────────────────
        # _equity_verified: True after probe confirms equity data live.
        # _options_verified: True when opt_successes > 0 (passive, from traffic).
        # _readiness_verified: kept for backwards compat = _equity_verified.
        # Reset all on reconnect/token-refresh.
        self._equity_verified:   bool = False
        self._options_verified:  bool = False
        self._readiness_verified: bool = False  # backwards compat alias
        # Throttle: don't probe more often than once per 5 min.
        self._last_readiness_probe_ts: float = 0.0
        # Track the previous mode for [DhanModeTransition] emission.
        self._prev_runtime_mode: Optional[str] = None
        # Per-cycle mode counters for [DhanRuntimeSummary] at EOD.
        self._mode_cycle_counts: Dict[str, int] = {
            "LIVE_VERIFIED": 0,
            "PARTIAL_LIVE":  0,
            "FALLBACK":      0,
            "SIMULATION":    0,
        }

        # ── Patch 5/6: per-segment health state ──────────────────────────
        # Updated by get_quote() and get_multiple_quotes() after each call.
        # Values: "LIVE" | "IDX_I_EMPTY" | "EMPTY_SEGMENT" | "SEGMENT_UNSUPPORTED"
        self._segment_health: Dict[str, str] = {}

        self._connect()
        self._audit_dhan_coverage()

    def _audit_dhan_coverage(self) -> None:
        """
        Startup audit: log [MISSING_DHAN_MAPPING] for any watchlist symbol
        that has no entry in DHAN_SECURITY_MAP.  This makes fallback to
        Yahoo/sim explicit and visible — never silent.
        """
        missing = sorted(_ALL_WATCHLIST_SYMBOLS - set(DHAN_SECURITY_MAP))
        if missing:
            for sym in missing:
                log.warning("[MISSING_DHAN_MAPPING] symbol=%s — no Dhan security_id; "
                            "will use Yahoo/sim fallback", sym)
        else:
            log.info("[DhanFeed] ✅ Full Dhan symbol coverage — all %d watchlist "
                     "symbols mapped.", len(_ALL_WATCHLIST_SYMBOLS))

    def auth_state(self) -> dict:
        """
        Return a snapshot of the current Dhan authentication state.
        Safe to call at any time; never raises.
        """
        rem_s: Optional[float] = None
        if self._token_expires_at:
            rem_s = self._token_expires_at - time.time()
        return {
            "token_present":  self._token_present,
            "api_mode":       "LIVE" if self._live else "FALLBACK",
            "expires_in_sec": int(rem_s) if rem_s is not None else None,
            "expires_in_h":   f"{int(rem_s/3600)}h {int((rem_s%3600)/60)}m" if rem_s is not None else "unknown",
            "token_expired":  (rem_s is not None and rem_s <= 0),
        }

    def check_token_expiry(self, notifier=None) -> None:
        """
        Emit a governed token expiry warning.
        Fires ONCE when ≤30 min remaining. Suppresses all repeats until token
        is refreshed via reload_token() which resets _token_warn_sent.
        Logs at INFO level for monitoring; Telegram alert only on first warning.
        """
        if not self._token_expires_at:
            return
        rem_s = self._token_expires_at - time.time()
        rem_h = rem_s / 3600
        rem_m = int(rem_s / 60)
        if rem_s <= 0:
            msg = (
                "[DhanAuthState] ⛔ TOKEN EXPIRED — Dhan feed will fail. "
                "Send /token <new_token> via Telegram to hot-swap."
            )
            log.error(msg)
            if notifier:
                try:
                    notifier.send_alert(f"⛔ <b>Dhan token EXPIRED.</b> Send /token &lt;new_token&gt; now.")
                except Exception:
                    pass
        elif rem_s <= 1800:   # ≤30 min — governed single warning
            if not self._token_warn_sent:
                log.warning(
                    "[DhanAuthState] ⚠️ TOKEN EXPIRES SOON — %dm remaining. "
                    "Send /token <new_token> via Telegram before expiry.",
                    rem_m,
                )
                log.info("[TokenGovernance] expires_in=%dm warned=True reason=FIRST_WARNING", rem_m)
                self._token_warn_sent = True
                if notifier:
                    try:
                        notifier.send_alert(
                            f"⚠️ <b>Dhan token expires in {rem_m}m.</b>\n"
                            f"Send /token &lt;new_token&gt; now to keep Dhan feed LIVE."
                        )
                    except Exception:
                        pass
            else:
                log.debug(
                    "[TokenGovernance] expires_in=%dm warned=True reason=SUPPRESSED", rem_m
                )
        elif rem_h < 24:
            log.debug(
                "[TokenGovernance] expires_in=%dh%dm warned=%s reason=MONITORING",
                int(rem_h), int((rem_s % 3600) / 60), self._token_warn_sent,
            )

    def reload_token(self, new_token: str) -> bool:
        """
        Hot-swap the Dhan access token without restarting the process.

        Steps:
          1. Update os.environ so _get_credentials() picks up the new value.
          2. Persist the token to .env with direct write (no atomic rename —
             safe for bind-mounted volumes where tmp→rename fails with EBUSY).
          3. Reinitialise the dhanhq client via _connect().

        Returns True if the reconnect succeeds (self._live == True).
        """
        import pathlib

        new_token = new_token.strip()
        if not new_token:
            raise ValueError("Token must not be empty.")

        # 1 — update live environment
        os.environ["DHAN_ACCESS_TOKEN"] = new_token

        # 2 — persist to .env with a direct write (no atomic rename).
        #     Atomic rename (tmp.replace(env_path)) fails on bind-mounted volumes
        #     with [Errno 16] EBUSY.  Direct write_text is safe here because
        #     the .env file is only read at startup/reload, not streamed.
        env_path = pathlib.Path(__file__).parent.parent / ".env"
        try:
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith("DHAN_ACCESS_TOKEN"):
                        lines[i] = f"DHAN_ACCESS_TOKEN={new_token}\n"
                        updated = True
                        break
                if not updated:
                    lines.append(f"DHAN_ACCESS_TOKEN={new_token}\n")
                env_path.write_text("".join(lines), encoding="utf-8")
            else:
                env_path.write_text(f"DHAN_ACCESS_TOKEN={new_token}\n", encoding="utf-8")
            log.info("[DhanFeed] .env updated with new access token.")
        except Exception as exc:
            log.warning("[DhanFeed] Could not persist token to .env: %s", exc)

        # 3 — reinitialise dhanhq client (also resets circuit breaker)
        self._live    = False
        self._dhan    = None
        self._context = None
        self._dhan_consecutive_failures = 0         # reset circuit breaker on token refresh
        self._dhan_opt_consecutive_failures = {}    # reset opt session tracker on token refresh
        self._token_warn_sent = False               # reset warning flag after token refresh
        self._readiness_verified = False            # Phase 9: must re-verify after token swap
        self._equity_verified   = False             # Phase 11
        self._options_verified  = False             # Phase 11
        log.info("[TokenGovernance] warned=False reason=RESET_AFTER_REFRESH")
        self._connect()
        # Phase 5 — Recovery audit: was Dhan restored after token swap?
        _recovered = self._live
        log.info(
            "[DhanRecoveryAudit] recovered=%s  manual_token_required=True"
            "  token_swapped=True  api_mode=%s"
            "  cycles_until_recovery=0",
            _recovered, "LIVE" if _recovered else "FALLBACK",
        )
        if _recovered:
            # Phase 1 — subsystem state after recovery
            self._emit_subsystem_state()
            # Phase 9 — session state after token reload
            self._emit_session_state(trigger="reload_token")
            # Phase 2 — readiness probe after token refresh (market hours only)
            if self._is_market_open():
                self._readiness_probe()
        return self._live

    def _parse_jwt_expiry(self, token: str) -> Optional[float]:
        """Extract exp/iat claims from JWT payload without verifying signature.

        Dhan JWTs sometimes contain non-UTF-8 bytes inside the payload segment
        that make json.loads() fail.  We try json.loads first; if that fails we
        fall back to a regex scan of the raw decoded bytes so we can still read
        the numeric exp/iat even when the JSON is malformed.
        """
        try:
            import base64 as _b64, re as _re
            part = token.split(".")[1]
            part += "=" * (4 - len(part) % 4)
            raw = _b64.urlsafe_b64decode(part)
            try:
                import json as _json
                claims = _json.loads(raw)
                exp = claims.get("exp")
                iat = claims.get("iat")
            except Exception:
                # Malformed JSON — extract exp/iat via regex on the raw bytes
                raw_str = raw.decode("latin-1")  # latin-1 never fails
                exp_m = _re.search(r'"exp"\s*:\s*(\d+)', raw_str)
                iat_m = _re.search(r'"iat"\s*:\s*(\d+)', raw_str)
                exp = int(exp_m.group(1)) if exp_m else None
                iat = int(iat_m.group(1)) if iat_m else None
            if iat:
                self._token_issued_at = float(iat)
            return float(exp) if exp else None
        except Exception:
            return None

    def _connect(self) -> None:
        """Try to initialise dhanhq client with environment credentials."""
        client_id, access_token = _get_credentials()
        self._token_present = bool(access_token)
        if not client_id or not access_token:
            log.warning(
                "[DhanFeed] Credentials not set (DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN). "
                "Running in simulation mode."
            )
            log.warning(
                "[DhanAuthState] token_present=False  expires_in=N/A  api_mode=FALLBACK"
            )
            return
        # Parse JWT expiry before connecting
        self._token_expires_at = self._parse_jwt_expiry(access_token)
        _expires_in_h: str
        if self._token_expires_at:
            _rem_s = self._token_expires_at - time.time()
            _rem_h = int(_rem_s / 3600)
            _rem_m = int((_rem_s % 3600) / 60)
            _expires_in_h = f"{_rem_h}h {_rem_m}m"
        else:
            _expires_in_h = "unknown"
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
            log.info(
                "[DhanAuthState] token_present=True  expires_in=%s  api_mode=LIVE",
                _expires_in_h,
            )
            # [DhanForensic] Identity snapshot — used for parity analysis between symbols
            log.info(
                "[DhanForensic] CONNECT  client_obj=%d  ctx_obj=%s  "
                "dhan_http_obj=%s  token_sfx=%s",
                id(self._dhan),
                id(self._context) if self._context else "None",
                id(getattr(self._dhan, "dhan_http", None)),
                access_token[-8:] if access_token else "NONE",
            )
            # Warn early if token expires within 24 h
            if self._token_expires_at:
                self.check_token_expiry()
            # Phase 1 — subsystem state snapshot after successful connect
            self._emit_subsystem_state()
            # Phase 9 — initial session state (mode=FALLBACK until probe confirms live)
            self._emit_session_state(trigger="connect_success")
            # Phase 2 — active readiness probe (only during market hours to
            # avoid false negatives on overnight / pre-market starts)
            if self._is_market_open():
                self._readiness_probe()
            else:
                log.info(
                    "[DhanReadinessAudit] probe_deferred=True"
                    "  reason=OUTSIDE_MARKET_HOURS  window=%s"
                    "  declared_live=DEFERRED_UNTIL_MARKET_OPEN",
                    self._market_time_window(),
                )
                # Phase 9 — still emit session state for deferred-probe startup
                self._emit_session_state(trigger="connect_deferred_probe")
            # Optional list preload can be noisy with some dhanhq versions;
            # keep default startup path clean unless explicitly enabled.
            if os.getenv("DHAN_LOAD_SECURITY_LIST", "false").strip().lower() in ("1", "true", "yes", "on"):
                self._load_instrument_list()
        except ImportError:
            log.warning(
                "[DhanFeed] dhanhq package not installed. "
                "Run: pip install dhanhq   — falling back to simulation."
            )
            log.warning(
                "[DhanAuthState] token_present=%s  expires_in=%s  api_mode=FALLBACK",
                self._token_present, _expires_in_h,
            )
        except Exception as exc:
            log.error("[DhanFeed] Connection failed: %s — falling back to simulation.", exc)
            log.warning(
                "[DhanAuthState] token_present=%s  expires_in=%s  api_mode=FALLBACK",
                self._token_present, _expires_in_h,
            )

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

    # ── Circuit breaker ───────────────────────────────────────────────────

    def _trip_circuit(self) -> None:
        """
        Called when consecutive Dhan data-API failures reach the threshold.
        Marks the feed as non-live so callers skip straight to Yahoo/sim.
        The most common cause is an expired token (HTTP 401).
        """
        if not self._live:
            return  # already tripped
        self._live = False
        self._equity_verified  = False   # Phase 11: must re-verify after recovery
        self._readiness_verified = False # Phase 9: keep alias in sync
        log.error(
            "[DhanFeed] ⛔ Circuit breaker TRIPPED after %d consecutive API failures "
            "(status=failure / empty data from Dhan). "
            "Possible causes: token expired, API access not subscribed, or account blocked. "
            "Feed will use Yahoo/sim. Send /token <new_token> to restore if token expired.",
            self._dhan_consecutive_failures,
        )
        # Phase 1 + Phase 7 — emit full audit snapshot on circuit break
        self._emit_subsystem_state()
        self.get_live_readiness_score()
        # Phase 9 — runtime mode at circuit break (mode degrades to FALLBACK)
        self.emit_runtime_mode_tag("circuit_break",
                                   consecutive_failures=self._dhan_consecutive_failures)
        self._emit_session_state(trigger="circuit_break")
        try:
            from notifications.notifier_manager import get_notifier
            get_notifier().market_alert(
                "⛔ Dhan Feed Circuit Breaker",
                "5 consecutive data API failures — Dhan returning status=failure.\n"
                "Possible: token expired, no data subscription, or API blocked.\n"
                "System is using Yahoo fallback. Send /token <new_token> if token renewal is needed.",
            )
        except Exception:
            pass



    def _lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return Dhan meta dict for a symbol (static map first, then dynamic)."""
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        return DHAN_SECURITY_MAP.get(sym) or self._extra_map.get(sym)

    # ── Forensic Dhan Telemetry — Phases 1–7 ─────────────────────────────
    # All methods here are OBSERVE-ONLY: no behavioral changes, no side effects.

    @staticmethod
    def _market_time_window() -> str:
        """Return the NSE session window name for the current local time."""
        now = datetime.now()
        t   = now.hour * 60 + now.minute
        if   t < 9 * 60 + 15:  return "PREMARKET"
        elif t < 9 * 60 + 45:  return "OPENING"
        elif t < 15 * 60 + 30: return "INTRADAY"
        elif t < 18 * 60:      return "POSTCLOSE"
        else:                  return "OVERNIGHT"

    @staticmethod
    def _is_market_open() -> bool:
        now = datetime.now()
        t   = now.hour * 60 + now.minute
        return 9 * 60 + 15 <= t <= 15 * 60 + 30

    @staticmethod
    def _classify_dhan_response(resp: Any, exc: Optional[Exception]) -> str:
        """
        Phase 3 — Classify a Dhan non-success into a named failure category.

        AUTH_EXPIRED         — token expired; error_code/type populated in remarks
        AUTH_INVALID         — revoked / forbidden credentials
        ENTITLEMENT_MISSING  — data plan not subscribed for segment (HTTP 451)
        MULTI_SID_REJECTED   — status=failure, data='', all-None remarks — multi-SID
                               batch rejected OR segment unsupported (e.g. NSE_FNO).
                               NOT an auth event; does NOT trip circuit breaker.
        EMPTY_SEGMENT        — API OK but no rows returned for the requested segment
        IDX_I_EMPTY          — IDX_I (index) segment returned success with no data
        SEGMENT_UNSUPPORTED  — segment not enabled on this token tier
        HTTP_FAILURE         — network / non-4xx HTTP error
        RATE_LIMIT           — 429 too-many-requests
        TIMEOUT              — request timed out
        PARSE_FAILURE        — unexpected / non-dict response structure
        MARKET_CLOSED        — empty response expected (outside 09:15–15:30)
        UNKNOWN              — unclassified
        """
        if exc is not None:
            s = str(exc).lower()
            if "timeout" in s or "timed out" in s:        return "TIMEOUT"
            if "401" in s or "unauthorized" in s:         return "AUTH_EXPIRED"
            if "403" in s or "forbidden" in s:            return "AUTH_INVALID"
            if "451" in s:                                return "ENTITLEMENT_MISSING"
            if "429" in s or "rate limit" in s:           return "RATE_LIMIT"
            if "parse" in s or "json" in s or "decode" in s: return "PARSE_FAILURE"
            return "HTTP_FAILURE"
        if resp is None:
            return "HTTP_FAILURE"
        if not isinstance(resp, dict):
            return "PARSE_FAILURE"
        status      = resp.get("status", "")
        data        = resp.get("data", "")
        remarks_raw = resp.get("remarks", "")
        remarks     = str(remarks_raw or "").lower()
        if status in ("failure", "failed"):
            if isinstance(data, str) and data == "":
                # Distinguish MULTI_SID_REJECTED from AUTH_EXPIRED.
                # Multi-SID / segment-rejection: remarks dict with all-None fields.
                # True auth failure: error_code / error_type is populated.
                if isinstance(remarks_raw, dict):
                    if (remarks_raw.get("error_code") is None
                            and remarks_raw.get("error_type") is None):
                        return "MULTI_SID_REJECTED"
                # String remarks with explicit auth evidence → AUTH_EXPIRED
                if "401" in remarks or "unauthor" in remarks or "expired" in remarks:
                    return "AUTH_EXPIRED"
                # No error details → structural rejection, not auth
                return "MULTI_SID_REJECTED"
            if "401" in remarks or "unauthor" in remarks or "expired" in remarks:
                return "AUTH_EXPIRED"
            if "451" in remarks or "not subscrib" in remarks or "entitlement" in remarks:
                return "ENTITLEMENT_MISSING"
            if isinstance(data, dict) and not data:
                return "EMPTY_SEGMENT"
            return "UNKNOWN"
        if isinstance(data, dict) and not data:
            # Status OK but empty data dict — market-closed or unsupported segment
            window = DhanFeed._market_time_window()
            if window in ("OVERNIGHT", "PREMARKET", "POSTCLOSE"):
                return "MARKET_CLOSED"
            return "EMPTY_SEGMENT"
        return "UNKNOWN"

    def _emit_failure_classified(
        self,
        endpoint: str,
        resp: Any,
        exc: Optional[Exception],
    ) -> None:
        """
        Phase 3 — Log [DhanFailureClassified] and update counters.
        Never raises; forensic logging must not break the feed.
        """
        try:
            failure_type = self._classify_dhan_response(resp, exc)
            window       = self._market_time_window()
            retryable    = failure_type in ("TIMEOUT", "HTTP_FAILURE", "RATE_LIMIT", "MARKET_CLOSED")
            http_status  = "unknown"
            resp_preview = ""
            if isinstance(resp, dict):
                http_status  = str(resp.get("status", "unknown"))
                resp_preview = str(resp.get("data", ""))[:80]
            elif exc:
                resp_preview = str(exc)[:80]

            # Update per-endpoint failure type counts
            ep = self._dhan_failure_counts.setdefault(endpoint, {})
            ep[failure_type] = ep.get(failure_type, 0) + 1
            # Update per-window counts
            win_ep = self._window_failure_counts.setdefault(window, {})
            win_ep[endpoint] = win_ep.get(endpoint, 0) + 1

            _circuit_types = ("AUTH_EXPIRED", "AUTH_INVALID", "HTTP_FAILURE", "TIMEOUT")
            log.info(
                "[DhanClassifier] endpoint=%s  raw_status=%r"
                "  classified=%s  circuit_impact=%s",
                endpoint, http_status, failure_type,
                "YES" if failure_type in _circuit_types else "NO",
            )
            log.info(
                "[DhanFailureClassified] endpoint=%s  failure_type=%s"
                "  http_status=%r  response_preview=%r"
                "  market_open=%s  window=%s  retryable=%s  consecutive=%d",
                endpoint, failure_type,
                http_status, resp_preview,
                self._is_market_open(), window, retryable,
                self._dhan_consecutive_failures,
            )

            # Phase 4 — emit [DhanTimeWindowAudit] every 5th failure per window/endpoint
            win_total = sum(win_ep.values())
            if win_total > 0 and win_total % 5 == 0:
                self._emit_window_audit(window, endpoint)
        except Exception:
            pass   # forensic logging must never break the feed

    def _emit_window_audit(self, window: str, endpoint: str) -> None:
        """Phase 4 — Log [DhanTimeWindowAudit] rolling per-window metrics."""
        fail_n = self._window_failure_counts.get(window, {}).get(endpoint, 0)
        succ_n = self._window_success_counts.get(window, {}).get(endpoint, 0)
        total  = fail_n + succ_n
        rate   = round(succ_n / total, 3) if total else 0.0
        log.info(
            "[DhanTimeWindowAudit] window=%s  endpoint=%s"
            "  success_rate=%.1f%%  successes=%d  failures=%d  total_calls=%d",
            window, endpoint, rate * 100, succ_n, fail_n, total,
        )

    def _emit_subsystem_state(self) -> None:
        """
        Phase 1 — Log [DhanSubsystemState]: structured snapshot across 5 domains.
        Called at connect, token-refresh, and circuit-break.
        """
        try:
            auth = self.auth_state()
            # AUTH domain
            if not auth["token_present"]:
                auth_str = "NO_TOKEN"
            elif auth["token_expired"]:
                auth_str = "EXPIRED"
            else:
                auth_str = f"OK(expires={auth['expires_in_h']})"

            # DATA equity domain
            eq_fails = sum(self._dhan_failure_counts.get("equity_batch", {}).values())
            eq_ok    = self._dhan_equity_successes
            if not self._live and self._dhan_consecutive_failures >= self._DHAN_CIRCUIT_OPEN_AFTER:
                eq_state = "CIRCUIT_OPEN"
            elif self._live:
                eq_state = "LIVE" if eq_ok > 0 else "LIVE_UNVERIFIED"
            else:
                eq_state = "FALLBACK"

            # DATA options domain
            opt_fails = sum(self._dhan_failure_counts.get("options_chain", {}).values())
            opt_ok    = self._dhan_opt_successes
            if opt_ok > 0:
                opt_state = "AVAILABLE"
            elif opt_fails > 0:
                opt_state = "NEVER_SUCCEEDED"
            else:
                opt_state = "UNTESTED"

            # ENTITLEMENT domain — infer from accumulated failure types
            all_ftypes: Dict[str, int] = {}
            for ep_counts in self._dhan_failure_counts.values():
                for ftype, cnt in ep_counts.items():
                    all_ftypes[ftype] = all_ftypes.get(ftype, 0) + cnt
            if all_ftypes.get("ENTITLEMENT_MISSING", 0) > 0:
                ent_state = "MISSING"
            elif all_ftypes.get("AUTH_EXPIRED", 0) > 3:
                ent_state = "SUSPECTED_TOKEN_ISSUE"
            elif self._live:
                ent_state = "ASSUMED_OK"
            else:
                ent_state = "UNKNOWN"

            # EXECUTION domain — infer from auth (not probed to avoid side effects)
            exec_state = "READY" if self._live else "UNTESTED_FALLBACK"

            log.info(
                "[DhanSubsystemState]"
                " auth=%s  equity_data=%s  options_data=%s"
                " entitlement=%s  execution_api=%s  overall=%s"
                " eq_successes=%d  eq_failures=%d"
                " opt_successes=%d  opt_failures=%d"
                " circuit_consecutive=%d",
                auth_str, eq_state, opt_state,
                ent_state, exec_state,
                "LIVE" if self._live else "FALLBACK",
                eq_ok, eq_fails,
                opt_ok, opt_fails,
                self._dhan_consecutive_failures,
            )
        except Exception:
            pass

    def _readiness_probe(self) -> dict:
        """
        Phase 11 — Active readiness check with split equity/options verification.
        Logs [ReadinessTrace], [ReadinessFailure], [ReadinessScore], [DhanReadinessAudit].
        Safe to call any time; never raises.
        """
        import time as _time
        _t0 = _time.time()
        self._last_readiness_probe_ts = _t0

        auth         = self.auth_state()
        auth_ok      = auth["token_present"] and not auth["token_expired"] and self._live
        market_open  = self._is_market_open()

        quote_ok     = False
        parse_ok     = False
        freshness_ok = False
        segment_ok   = False
        latency_ms   = 0.0
        resp_status  = "not_attempted"
        resp_keys    = []
        failure_reason = "NOT_ATTEMPTED"
        probe_sym    = "HDFCBANK"

        if not auth_ok:
            if not auth["token_present"]:
                failure_reason = "NO_TOKEN"
            elif auth["token_expired"]:
                failure_reason = "TOKEN_EXPIRED"
            else:
                failure_reason = "NOT_CONNECTED"
        else:
            try:
                meta = self._lookup(probe_sym)
                if meta:
                    seg  = meta["segment"]
                    sid  = int(meta["security_id"])
                    _t1  = _time.time()
                    resp = self._dhan.quote_data(securities={seg: [sid]})
                    latency_ms = (_time.time() - _t1) * 1000
                    if resp is None:
                        resp_status = "none"
                        failure_reason = "ENDPOINT_FAILURE"
                    elif resp.get("status") == "failure":
                        resp_status = "failure"
                        resp_keys   = list(resp.keys())
                        failure_reason = "ENDPOINT_FAILURE"
                        self._emit_failure_classified("readiness_probe", resp, None)
                    elif isinstance(resp.get("data"), dict):
                        resp_status = "success"
                        resp_keys   = list(resp.keys())
                        quote_ok = True
                        _probe_data = resp["data"]
                        if isinstance(_probe_data.get("data"), dict):
                            _probe_data = _probe_data["data"]
                        seg_data = _probe_data.get(seg, {})
                        if not seg_data:
                            failure_reason = "EMPTY_SEGMENT"
                        else:
                            segment_ok = True
                            row = seg_data.get(str(sid), {})
                            if not row:
                                failure_reason = "NO_QUOTES"
                            else:
                                parse_ok = True
                                ltp = float(row.get("last_price", row.get("ltp", 0)) or 0)
                                if ltp > 0:
                                    freshness_ok = True
                                    failure_reason = "NONE"
                                else:
                                    failure_reason = "PARSE_FAILURE"
                    else:
                        resp_status = "unexpected"
                        failure_reason = "PARSE_FAILURE"
                else:
                    failure_reason = "SYMBOL_NOT_MAPPED"
            except Exception as _probe_exc:
                latency_ms = (_time.time() - _t0) * 1000
                failure_reason = "EXCEPTION"
                resp_status = "exception"

        equity_verified = auth_ok and quote_ok and parse_ok and freshness_ok and segment_ok
        # Options: passively derived from accumulated traffic (no active options probe)
        options_verified = self._dhan_opt_successes > 0

        # Update instance state
        self._equity_verified   = equity_verified
        self._options_verified  = options_verified
        self._readiness_verified = equity_verified  # backwards compat alias

        declared_live = equity_verified  # declared_live = equity gate (options is separate)
        result = {
            "auth_ok": auth_ok, "quote_ok": quote_ok,
            "parse_ok": parse_ok, "freshness_ok": freshness_ok,
            "segment_ok": segment_ok, "declared_live": declared_live,
            "equity_verified": equity_verified, "options_verified": options_verified,
        }
        self._readiness_probe_result = result

        # ── [ReadinessTrace] ──────────────────────────────────────────────
        log.info(
            "[ReadinessTrace] probe=equity_ohlc endpoint=ohlc_data"
            " response_status=%s response_keys=%s"
            " latency_ms=%.0f token_present=%s auth_ok=%s"
            " market_hours=%s result=%s failure_reason=%s"
            " equity_verified=%s options_verified=%s",
            resp_status, resp_keys or "[]",
            latency_ms, auth["token_present"], auth_ok,
            market_open, "PASS" if equity_verified else "FAIL", failure_reason,
            equity_verified, options_verified,
        )

        # ── [ReadinessFailure] — only when equity check fails ─────────────
        if not equity_verified and failure_reason not in ("NOT_ATTEMPTED",):
            log.warning(
                "[ReadinessFailure] probe_symbol=%s reason=%s"
                " auth_ok=%s quote_ok=%s parse_ok=%s freshness_ok=%s segment_ok=%s"
                " latency_ms=%.0f",
                probe_sym, failure_reason,
                auth_ok, quote_ok, parse_ok, freshness_ok, segment_ok,
                latency_ms,
            )

        # ── [ReadinessScore] ──────────────────────────────────────────────
        _auth_s  = 1.0 if auth_ok else 0.0
        _eq_s    = 1.0 if equity_verified else (0.5 if quote_ok else 0.0)
        _opt_s   = 1.0 if options_verified else 0.0
        _lat_s   = (1.0 if latency_ms < 500 else
                    0.8 if latency_ms < 2000 else
                    0.5 if latency_ms < 5000 else 0.2) if latency_ms > 0 else 0.5
        _overall = round(0.35 * _auth_s + 0.40 * _eq_s + 0.15 * _opt_s + 0.10 * _lat_s, 2)
        _runtime_mode = self.get_runtime_mode()
        log.info(
            "[ReadinessScore] auth=%.2f equity=%.2f options=%.2f latency=%.2f"
            " overall=%.2f classification=%s",
            _auth_s, _eq_s, _opt_s, _lat_s, _overall, _runtime_mode,
        )

        # ── [DhanReadinessAudit] — backward-compat tag ────────────────────
        log.info(
            "[DhanReadinessAudit] auth_ok=%s  quote_ok=%s  parse_ok=%s"
            "  freshness_ok=%s  segment_ok=%s  declared_live=%s  probe_symbol=%s"
            "  equity_verified=%s  options_verified=%s  runtime_mode=%s",
            auth_ok, quote_ok, parse_ok,
            freshness_ok, segment_ok, declared_live, probe_sym,
            equity_verified, options_verified, _runtime_mode,
        )
        # Phase 9: emit [DhanSessionState] with authoritative post-probe truth
        self._emit_session_state(trigger="readiness_probe")
        return result

    # ── Phase 9: Runtime-mode truth methods ───────────────────────────────

    def get_runtime_mode(self) -> str:
        """
        Phase 11 — Canonical 4-tier runtime-mode resolver.

        Hierarchy (most → least capable):
          LIVE_VERIFIED — token + equity verified + options confirmed
          PARTIAL_LIVE  — token + equity verified + options degraded/synthetic
          FALLBACK      — token present but equity NOT verified
          SIMULATION    — no token present; all data is yfinance/simulated
        """
        if not self._token_present:
            return "SIMULATION"
        if not self._equity_verified:
            return "FALLBACK"
        # Equity is verified. Check options (passive: from traffic counters).
        if not (self._options_verified or self._dhan_opt_successes > 0):
            return "PARTIAL_LIVE"
        return "LIVE_VERIFIED"

    def record_cycle_mode(self) -> None:
        """
        Increment the per-mode cycle counter for the current runtime mode.
        Called once per trading cycle by DataFeedManager.check_truth_governance().
        Used to produce [DhanRuntimeSummary] at EOD.
        Also emits [DhanModeTransition] when mode changes from previous value.
        """
        mode = self.get_runtime_mode()
        self._mode_cycle_counts[mode] = self._mode_cycle_counts.get(mode, 0) + 1
        # Transition detection
        if self._prev_runtime_mode is not None and mode != self._prev_runtime_mode:
            log.info(
                "[DhanModeTransition] from=%s to=%s reason=cycle_check",
                self._prev_runtime_mode, mode,
            )
        self._prev_runtime_mode = mode

    def check_market_open_readiness(self) -> None:
        """
        Phase 11 — Re-trigger readiness probe once per session when market opens.
        Called from DataFeedManager.check_truth_governance() every cycle.
        Fires only when:
          - Dhan is connected (_live=True)
          - equity is NOT yet verified (_equity_verified=False)
          - market is open
          - at least 5 minutes since last probe (rate-limit)
        This resolves the root cause of FALLBACK persisting after pre-market
        reconnects: the deferred probe never re-fires at 09:15.
        """
        import time as _time
        if (self._live
                and not self._equity_verified
                and self._is_market_open()
                and (_time.time() - self._last_readiness_probe_ts) > 300):
            log.info(
                "[ReadinessRetrigger] equity_verified=False live=True "
                "market_open=True — firing deferred readiness probe now",
            )
            self._readiness_probe()

    def _emit_session_state(self, trigger: str = "startup") -> None:
        """
        Phase 9/11 — Emit [DhanSessionState]: token/auth/readiness/mode truth.
        """
        try:
            auth     = self.auth_state()
            auth_ok  = auth["token_present"] and not auth.get("token_expired", False)
            mode     = self.get_runtime_mode()
            log.info(
                "[DhanSessionState] trigger=%s token_present=%s auth_ok=%s "
                "equity_verified=%s options_verified=%s runtime_mode=%s live=%s",
                trigger,
                auth["token_present"], auth_ok,
                self._equity_verified, self._options_verified, mode, self._live,
            )
            # Mode transition on explicit state re-emission
            if self._prev_runtime_mode is not None and mode != self._prev_runtime_mode:
                log.info(
                    "[DhanModeTransition] from=%s to=%s reason=%s",
                    self._prev_runtime_mode, mode, trigger,
                )
            self._prev_runtime_mode = mode
        except Exception:
            pass

    def emit_runtime_mode_tag(self, event: str, **extra) -> None:
        """
        Phase 9 — Emit [DhanRuntimeMode] at degradation/circuit-break/recovery events.
        event: short description, e.g. 'options_degraded', 'circuit_break', 'fallback'
        extra: any additional key=value context fields
        """
        try:
            auth     = self.auth_state()
            auth_ok  = auth["token_present"] and not auth.get("token_expired", False)
            mode     = self.get_runtime_mode()
            # options_live = readiness verified AND options probe succeeded
            opt_pr   = self._readiness_probe_result or {}
            opt_live = self._readiness_verified and opt_pr.get("declared_live", False)
            eq_live  = self._live and self._dhan_equity_successes > 0
            extra_str = "  ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
            log.info(
                "[DhanRuntimeMode] event=%s mode=%s token_present=%s "
                "readiness_verified=%s options_live=%s equity_live=%s%s",
                event, mode, auth["token_present"],
                self._readiness_verified, opt_live, eq_live,
                f"  {extra_str}" if extra_str else "",
            )
        except Exception:
            pass

    def get_runtime_context_str(self) -> str:
        """
        Phase 9 — Return a compact runtime context string for appending to alerts.
        Used by DataFeedManager to enrich OPTIONS CHAIN DEGRADED messages.
        """
        auth    = self.auth_state()
        auth_ok = auth["token_present"] and not auth.get("token_expired", False)
        mode    = self.get_runtime_mode()
        return (
            f"runtime_mode={mode}\n"
            f"token_present={auth['token_present']}\n"
            f"auth_valid={auth_ok}\n"
            f"readiness_verified={self._readiness_verified}\n"
            f"verified_live={mode == 'LIVE_VERIFIED'}"
        )

    def get_live_readiness_score(self) -> dict:
        """
        Phase 7 — Compute and log [DhanLiveReadiness] rolling metrics.
        Answers: 'Is Dhan reliable enough for live deployment?'
        """
        eq_rel  = (round(self._dhan_equity_successes / self._dhan_equity_attempts, 3)
                   if self._dhan_equity_attempts else 0.0)
        opt_rel = (round(self._dhan_opt_successes / self._dhan_opt_attempts, 3)
                   if self._dhan_opt_attempts else 0.0)
        auth    = self.auth_state()
        auth_ok = auth["token_present"] and not auth["token_expired"]
        fb_freq = (round(self._dhan_fallback_events / self._dhan_equity_attempts, 3)
                   if self._dhan_equity_attempts else 0.0)
        exec_ok = (self._live and
                   self._dhan_failure_counts.get("equity_batch", {}).get("AUTH_EXPIRED", 0) == 0)

        log.info(
            "[DhanLiveReadiness]"
            " equity_quote_reliability=%.1f%%"
            " options_reliability=%.1f%%"
            " auth_stability=%s"
            " fallback_frequency=%.1f%%"
            " execution_readiness=%s"
            " eq_attempts=%d  eq_successes=%d"
            " opt_attempts=%d  opt_successes=%d"
            " fallback_events=%d",
            eq_rel * 100, opt_rel * 100, auth_ok,
            fb_freq * 100, exec_ok,
            self._dhan_equity_attempts, self._dhan_equity_successes,
            self._dhan_opt_attempts,    self._dhan_opt_successes,
            self._dhan_fallback_events,
        )
        return {
            "equity_quote_reliability": eq_rel,
            "options_reliability":      opt_rel,
            "auth_stability":           auth_ok,
            "fallback_frequency":       fb_freq,
            "execution_readiness":      exec_ok,
        }

    def emit_daily_summary(self) -> None:
        """
        Phase 6 — Emit structured EOD telemetry for Dhan/NSE health analysis.
        Called by _do_eod_learning() in master_orchestrator.py.
        Tags: [DhanDailySummary], [OptionsDegradationCause], [DhanEnvironmentAudit]
        """
        import hashlib
        import socket

        auth       = self.auth_state()
        auth_ok    = auth["token_present"] and not auth["token_expired"]
        eq_at      = self._dhan_equity_attempts
        eq_ok      = self._dhan_equity_successes
        opt_at     = getattr(self, "_dhan_opt_attempts",   0)
        opt_ok     = getattr(self, "_dhan_opt_successes",  0)
        fb_events  = getattr(self, "_dhan_fallback_events", 0)
        synth_cyc  = getattr(self, "_synthetic_cycles",     0)

        eq_live_pct  = round(eq_ok  / eq_at  * 100, 1) if eq_at  else 0.0
        opt_live_pct = round(opt_ok / opt_at * 100, 1) if opt_at else 0.0
        auth_ok_pct  = 100.0 if auth_ok else 0.0

        log.info(
            "[DhanDailySummary] auth_ok_pct=%.1f eq_attempts=%d eq_live_pct=%.1f"
            " opt_attempts=%d opt_live_pct=%.1f fallback_events=%d synthetic_cycles=%d",
            auth_ok_pct, eq_at, eq_live_pct,
            opt_at, opt_live_pct, fb_events, synth_cyc,
        )

        # Options degradation breakdown
        nse_ok  = opt_ok > 0
        dhan_ok = auth_ok and eq_ok > 0
        fallback_type = (
            "synthetic"  if synth_cyc > 0 else
            "yahoo"      if fb_events > 0 else
            "none"
        )
        log.info(
            "[OptionsDegradationCause] token_present=%s auth_ok=%s "
            "nse_ok=%s dhan_ok=%s fallback=%s",
            auth["token_present"], auth_ok, nse_ok, dhan_ok, fallback_type,
        )

        # Environment fingerprint (IP hash only — no raw IP in logs)
        try:
            _host = socket.gethostname()
            _ip   = socket.gethostbyname(_host)
            _ip_h = hashlib.sha1(_ip.encode()).hexdigest()[:12]
        except Exception:
            _host, _ip_h = "unknown", "unknown"
        # Failure type this session
        _failure_types = sorted(set(
            k for counts in self._dhan_failure_counts.values() for k in counts
        ))
        log.info(
            "[DhanEnvironmentAudit] host=%s ip_hash=%s failure_types=%s",
            _host, _ip_h, _failure_types or "none",
        )

        # ── Phase 9/11: Runtime-mode summary ───────────────────────────────
        _lv  = self._mode_cycle_counts.get("LIVE_VERIFIED", 0)
        _pl  = self._mode_cycle_counts.get("PARTIAL_LIVE",  0)
        _sim = self._mode_cycle_counts.get("SIMULATION",    0)
        _fb  = self._mode_cycle_counts.get("FALLBACK",      0)
        _total = _lv + _pl + _sim + _fb
        log.info(
            "[DhanRuntimeSummary] live_verified_cycles=%d partial_live_cycles=%d "
            "simulation_cycles=%d fallback_cycles=%d total_cycles=%d",
            _lv, _pl, _sim, _fb, _total,
        )
        if _total > 0:
            _non_live = _sim + _fb
            _non_live_pct = _non_live / _total * 100
            if _non_live_pct > 80:
                log.warning(
                    "[DhanForensicContext] Most degradation today occurred under "
                    "SIMULATION/FALLBACK conditions (non_live_pct=%.0f%%). "
                    "Do not classify as verified-live broker instability. "
                    "live_verified=%d partial_live=%d simulation=%d fallback=%d",
                    _non_live_pct, _lv, _pl, _sim, _fb,
                )
            else:
                log.info(
                    "[DhanForensicContext] non_live_pct=%.0f%%  live_verified=%d "
                    "partial_live=%d simulation=%d fallback=%d",
                    _non_live_pct, _lv, _pl, _sim, _fb,
                )

        # ── Phase 11: Readiness resolution summary ──────────────────────
        _eq_attempts = max(getattr(self, "_dhan_equity_attempts", 0), 1)
        _eq_successes = getattr(self, "_dhan_equity_successes", 0)
        _opt_attempts = max(getattr(self, "_dhan_opt_attempts", 0), 1)
        _opt_successes = getattr(self, "_dhan_opt_successes", 0)
        _eq_fail_pct  = round((1 - _eq_successes / _eq_attempts) * 100, 1)
        _opt_fail_pct = round((1 - _opt_successes / _opt_attempts) * 100, 1)
        log.info(
            "[ReadinessResolutionSummary] live_verified_cycles=%d partial_live_cycles=%d "
            "fallback_cycles=%d equity_failure_pct=%.1f options_failure_pct=%.1f "
            "equity_verified_final=%s options_verified_final=%s",
            _lv, _pl, _fb,
            _eq_fail_pct, _opt_fail_pct,
            self._equity_verified, self._options_verified or self._dhan_opt_successes > 0,
        )

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
            # Build securities dict expected by quote_data
            sec_dict = {seg: [sid]}
            # ── [DhanPayload] observe-only telemetry ─────────────────
            log.debug(
                "[DhanPayload] method=get_quote endpoint=quote_data"
                " symbol=%s segment=%s security_id=%d total_sids=1",
                symbol, seg, sid,
            )
            resp = self._dhan.quote_data(securities=sec_dict)
            # ── [DhanResponseSummary] observe-only telemetry ─────────
            _gq_status   = (resp or {}).get("status", "none") if isinstance(resp, dict) else type(resp).__name__
            _gq_raw_data = (resp or {}).get("data", "") if isinstance(resp, dict) else ""
            _gq_data_obj = (_gq_raw_data.get("data", _gq_raw_data) if isinstance(_gq_raw_data, dict) else _gq_raw_data)
            _gq_data_type = type(_gq_data_obj).__name__
            _gq_seg_keys = list(_gq_data_obj.get(seg, {}).keys())[:5] if isinstance(_gq_data_obj, dict) else []
            log.debug(
                "[DhanResponseSummary] method=get_quote endpoint=quote_data"
                " symbol=%s segment=%s security_id=%d"
                " http_status=%r data_type=%s seg_keys_preview=%s row_present=%s",
                symbol, seg, sid,
                _gq_status, _gq_data_type, _gq_seg_keys,
                str(sid) in (list(_gq_data_obj.get(seg, {}).keys()) if isinstance(_gq_data_obj, dict) else []),
            )
            # ── Patch 3/4: classify before circuit-breaker decision ────────
            if not resp or resp.get("status") == "failure" or not isinstance(resp.get("data"), dict):
                _gq_ftype   = self._classify_dhan_response(resp, None)
                _gq_circuit = _gq_ftype in ("AUTH_EXPIRED", "AUTH_INVALID", "HTTP_FAILURE", "TIMEOUT")
                log.debug(
                    "[DhanClassifier] method=get_quote symbol=%s segment=%s"
                    " raw_status=%r classified=%s circuit_impact=%s",
                    symbol, seg,
                    (resp or {}).get("status", "none") if isinstance(resp, dict) else "none",
                    _gq_ftype, "YES" if _gq_circuit else "NO",
                )
                if _gq_circuit:
                    self._dhan_consecutive_failures += 1
                    if self._dhan_consecutive_failures >= self._DHAN_CIRCUIT_OPEN_AFTER:
                        self._trip_circuit()
                return self._yf_quote(symbol) or self._sim_quote(symbol)
            self._dhan_consecutive_failures = 0
            data = resp["data"]
            # quote_data returns double-nested: resp["data"]["data"][segment][str(sid)]
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                data = data["data"]
            seg_data = data.get(seg, data)
            row = seg_data.get(str(sid), {})
            if not row:
                # ── Patch 5: track IDX_I empty segment without auth penalty ──
                if seg == "IDX_I":
                    self._segment_health["IDX_I"] = "IDX_I_EMPTY"
                    log.debug(
                        "[DhanClassifier] method=get_quote symbol=%s segment=IDX_I"
                        " classified=IDX_I_EMPTY circuit_impact=NO",
                        symbol,
                    )
                return self._yf_quote(symbol) or self._sim_quote(symbol)
            self._segment_health[seg] = "LIVE"
            return self._row_to_quote(symbol, row)
        except Exception as exc:
            log.debug("[DhanFeed] get_quote(%s) error: %s", symbol, exc)
            return self._yf_quote(symbol) or self._sim_quote(symbol)

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Fetch OHLC quotes — Patch 2: batch mode (one quote_data call per segment)."""
        if not self._live:
            return {s: self._sim_quote(s) for s in symbols if self._sim_quote(s)}

        # Build segment → [(sym, sid), ...] mapping; collect unmapped separately
        seg_map: Dict[str, List[Tuple[str, int]]] = {}   # {seg: [(symbol, sid), ...]}
        missing: List[str] = []
        for sym in symbols:
            meta = self._lookup(sym)
            if not meta:
                missing.append(sym)
                continue
            _seg = meta["segment"]
            _sid = int(meta["security_id"])
            seg_map.setdefault(_seg, []).append((sym, _sid))

        result:      Dict[str, TickerQuote] = {}
        _attempted   = sum(len(v) for v in seg_map.values())
        _success     = 0
        _failed      = 0
        _seg_success: Dict[str, int] = {}
        _seg_failed:  Dict[str, int] = {}

        # ── [DhanRequestMode] ────────────────────────────────────────────
        log.info(
            "[DhanRequestMode] mode=BATCH_SEGMENT method=get_multiple_quotes"
            " symbol_count=%d segments=%d unmapped=%d",
            _attempted, len(seg_map), len(missing),
        )

        for seg, sym_sid_pairs in seg_map.items():
            sids       = [sid for _, sid in sym_sid_pairs]
            sym_by_sid = {str(sid): sym for sym, sid in sym_sid_pairs}

            self._dhan_equity_attempts += len(sids)

            log.debug(
                "[DhanPayload] method=get_multiple_quotes endpoint=quote_data"
                " segment=%s total_sids=%d sids_preview=%s",
                seg, len(sids), sids[:5],
            )

            try:
                resp = self._dhan.quote_data(securities={seg: sids})

                _ok = (
                    isinstance(resp, dict)
                    and resp.get("status") == "success"
                    and isinstance(resp.get("data"), dict)
                )

                if _ok:
                    data = resp["data"]
                    # quote_data double-nesting: resp["data"]["data"][seg][str(sid)]
                    if isinstance(data, dict) and isinstance(data.get("data"), dict):
                        data = data["data"]
                    seg_data = data.get(seg, {}) if isinstance(data, dict) else {}
                    returned_sids: set = set((seg_data or {}).keys())

                    for sid_str, row in (seg_data.items() if isinstance(seg_data, dict) else []):
                        sym = sym_by_sid.get(sid_str)
                        if not sym:
                            continue
                        if row:
                            result[sym] = self._row_to_quote(sym, row)
                            _success += 1
                            _seg_success[seg] = _seg_success.get(seg, 0) + 1
                            self._dhan_equity_successes += 1
                            self._dhan_consecutive_failures = 0
                            self._segment_health[seg] = "LIVE"
                            _win = self._market_time_window()
                            _wse = self._window_success_counts.setdefault(_win, {})
                            _wse["equity_single"] = _wse.get("equity_single", 0) + 1
                        else:
                            _failed += 1
                            _seg_failed[seg] = _seg_failed.get(seg, 0) + 1
                            _seg_class = "IDX_I_EMPTY" if seg == "IDX_I" else "EMPTY_SEGMENT"
                            self._segment_health[seg] = _seg_class
                            _fb = self._yf_quote(sym) or self._sim_quote(sym)
                            if _fb:
                                result[sym] = _fb

                    # Fallback for symbols not returned in batch response
                    for sym, sid in sym_sid_pairs:
                        if str(sid) not in returned_sids and sym not in result:
                            _failed += 1
                            _seg_failed[seg] = _seg_failed.get(seg, 0) + 1
                            _fb = self._yf_quote(sym) or self._sim_quote(sym)
                            if _fb:
                                result[sym] = _fb

                    log.debug(
                        "[DhanResponseSummary] method=get_multiple_quotes"
                        " segment=%s batch_size=%d returned=%d success=%d",
                        seg, len(sids), len(returned_sids), _success,
                    )

                else:
                    # ── Classify and protect circuit breaker ─────────────────
                    _ftype         = self._classify_dhan_response(resp, None)
                    _circuit_types = ("AUTH_EXPIRED", "AUTH_INVALID", "HTTP_FAILURE", "TIMEOUT")
                    _circuit_hit   = _ftype in _circuit_types
                    _failed        += len(sids)
                    _seg_failed[seg] = _seg_failed.get(seg, 0) + len(sids)
                    log.debug(
                        "[DhanResponseSummary] method=get_multiple_quotes"
                        " segment=%s batch_size=%d http_status=%r"
                        " classifier=%s circuit_impact=%s",
                        seg, len(sids),
                        (resp or {}).get("status", "none") if isinstance(resp, dict) else "none",
                        _ftype, "YES" if _circuit_hit else "NO",
                    )
                    self._emit_failure_classified("equity_batch", resp, None)
                    if _circuit_hit:
                        self._dhan_consecutive_failures += 1
                        if self._dhan_consecutive_failures >= self._DHAN_CIRCUIT_OPEN_AFTER:
                            self._trip_circuit()
                    # Fallback all symbols in this segment
                    for sym, _ in sym_sid_pairs:
                        _fb = self._yf_quote(sym) or self._sim_quote(sym)
                        if _fb:
                            result[sym] = _fb

            except Exception as _exc:
                _failed += len(sids)
                _seg_failed[seg] = _seg_failed.get(seg, 0) + len(sids)
                log.debug("[DhanFeed] batch quote error segment=%s: %s", seg, _exc)
                for sym, _ in sym_sid_pairs:
                    _fb = self._yf_quote(sym) or self._sim_quote(sym)
                    if _fb:
                        result[sym] = _fb

        # ── Fallback for unmapped symbols ─────────────────────────────────
        for sym in missing:
            q = self._sim_quote(sym)
            if q:
                result[sym] = q

        # ── [DhanPartialSuccess] ──────────────────────────────────────────
        if _attempted > 0:
            log.info(
                "[DhanPartialSuccess] method=get_multiple_quotes"
                " requested=%d success=%d failed=%d unmapped=%d match_rate=%.0f%%",
                _attempted, _success, _failed, len(missing),
                _success / _attempted * 100,
            )

        # ── [DhanSegmentHealth] ───────────────────────────────────────────
        if self._segment_health:
            log.info(
                "[DhanSegmentHealth] %s",
                "  ".join(f"{s}={h}" for s, h in sorted(self._segment_health.items())),
            )

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
            # Patch 3/4: classify before circuit-breaker decision — MULTI_SID_REJECTED is circuit_impact=NO
            if not resp or resp.get("status") == "failure" or not isinstance(resp.get("data"), dict):
                _ltp_ftype   = self._classify_dhan_response(resp, None)
                _ltp_circuit = _ltp_ftype in ("AUTH_EXPIRED", "AUTH_INVALID", "HTTP_FAILURE", "TIMEOUT")
                log.debug(
                    "[DhanClassifier] endpoint=ltp_single  raw_status=%r"
                    " classified=%s circuit_impact=%s",
                    (resp or {}).get("status", "none") if isinstance(resp, dict) else "none",
                    _ltp_ftype, "YES" if _ltp_circuit else "NO",
                )
                if _ltp_circuit:
                    self._dhan_consecutive_failures += 1
                    if self._dhan_consecutive_failures >= self._DHAN_CIRCUIT_OPEN_AFTER:
                        self._trip_circuit()
                return self._yf_ltp(symbol) or _SIM_PRICES.get(symbol.upper(), 100.0)
            self._dhan_consecutive_failures = 0
            data = resp["data"]
            # ticker_data/quote_data double-nesting: resp["data"]["data"][seg][str(sid)]
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                data = data["data"]
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
        dte_target: int = 20,
    ) -> Optional[OptionsChain]:
        """
        Fetch full options chain (all strikes, all expiries) via Dhan API.
        expiry format: "YYYY-MM-DD"  (nearest expiry used if None)
        dte_target: select the expiry closest to this many calendar days
        """
        if not self._live:
            return None   # caller falls back to NSEFeed simulation

        meta = self._lookup(symbol)
        if not meta or meta["segment"] != "IDX_I":
            log.debug("[DhanFeed] Options chain only supported for NSE indices.")
            return None

        # Determine nearest weekly expiry if not provided
        if expiry is None:
            # Use expiry_list() API to get actual listed expiry dates for this symbol.
            # Trust the API result — do NOT apply weekday validation since:
            #   - NIFTY: weekly on Tuesday
            #   - BANKNIFTY: MONTHLY ONLY on last Tuesday (weekly discontinued NSE 2024)
            #   - The API knows the correct schedule; weekday checks cause wrong overrides.
            # Fall back to _nearest_expiry(symbol) only if the API call fails/returns empty.
            try:
                _el = self._dhan.expiry_list(
                    under_security_id    = int(meta["security_id"]),
                    under_exchange_segment="IDX_I",
                )
                if isinstance(_el, dict) and _el.get("status") == "success":
                    _el_inner = _el.get("data", {})
                    _dates    = _el_inner.get("data", []) if isinstance(_el_inner, dict) else []
                    if _dates:
                        # Select expiry closest to dte_target (not always _dates[0])
                        _today_d   = date.today()
                        _best_exp  = _dates[0]
                        _best_diff = float("inf")
                        for _d in _dates:
                            try:
                                _d_dte  = (date.fromisoformat(_d) - _today_d).days
                                _d_diff = abs(_d_dte - dte_target)
                                if _d_diff < _best_diff:
                                    _best_diff = _d_diff
                                    _best_exp  = _d
                            except ValueError:
                                continue
                        expiry   = _best_exp
                        _sel_dte = (date.fromisoformat(_best_exp) - _today_d).days
                        _sel_rsn = "closest_to_dte_target" if len(_dates) > 1 else "only_available"
                        log.info(
                            "[ExpirySelectionAudit] source=DHAN  symbol=%s  "
                            "requested_dte_target=%d  available_expiries=%r  "
                            "selected_expiry=%s  selected_dte=%d  selection_reason=%s",
                            symbol, dte_target, _dates[:8], expiry, _sel_dte, _sel_rsn,
                        )
                    else:
                        expiry = self._nearest_expiry(symbol)
                    log.debug("[DhanFeed] expiry_list → %s for %s", expiry, symbol)
                else:
                    expiry = self._nearest_expiry(symbol)
            except Exception as _el_exc:
                log.debug("[DhanFeed] expiry_list failed (%s) — using fallback", _el_exc)
                expiry = self._nearest_expiry(symbol)

        self._dhan_opt_attempts += 1   # Phase 7: count every options API attempt
        # ── [DhanForensic] RAW PAYLOAD PARITY ANALYSIS ──────────────────────────────
        # Captures EXACT request state for NIFTY (works) vs BANKNIFTY (fails) comparison.
        _f_sid    = int(meta["security_id"])
        _f_cid    = id(self._dhan)
        _f_ctx_id = id(self._context) if self._context else None
        _f_tok = ""
        try:
            _, _f_tok_raw = _get_credentials()
            _f_tok = (_f_tok_raw or "")[-8:]
        except Exception:
            pass
        # Inspect DhanContext attributes for auth/session drift
        _f_ctx_info: dict = {}
        if self._context is not None:
            for _fa in ("client_id", "access_token", "dhan_session", "base_url"):
                _fv = getattr(self._context, _fa, None)
                if _fv is not None:
                    _f_ctx_info[_fa] = str(_fv)[-12:] if _fa == "access_token" else str(_fv)
        # Inspect dhan_http for session-level auth headers and cookies
        _f_http_id    = None
        _f_http_auth  = ""
        _f_http_cookies = ""
        _dh_http = getattr(self._dhan, "dhan_http", None)
        if _dh_http is not None:
            _f_http_id = id(_dh_http)
            for _hattr in ("headers", "_headers"):
                _hdrs = getattr(_dh_http, _hattr, None)
                if isinstance(_hdrs, dict):
                    _f_http_auth = str(_hdrs.get("access-token", _hdrs.get("Authorization", "")))[-12:]
                    break
            _http_sess = getattr(_dh_http, "session", getattr(_dh_http, "_session", None))
            if _http_sess is not None:
                _sess_h = getattr(_http_sess, "headers", {})
                if not _f_http_auth:
                    _f_http_auth = str(_sess_h.get("access-token", _sess_h.get("Authorization", "")))[-12:]
                _sess_c = getattr(_http_sess, "cookies", None)
                if _sess_c:
                    try:
                        _f_http_cookies = str(dict(_sess_c))[:80]
                    except Exception:
                        pass
        log.info(
            "[DhanForensic] PRE_CALL  symbol=%s  "
            "payload={'UnderlyingScrip':%d,'UnderlyingSeg':'IDX_I','Expiry':'%s'}"
            "  client_obj=%d  ctx_obj=%s  http_obj=%s  token_sfx=%s"
            "  ctx_attrs=%r  http_auth_sfx=%r  http_cookies=%r",
            symbol, _f_sid, expiry,
            _f_cid, _f_ctx_id, _f_http_id, _f_tok,
            _f_ctx_info, _f_http_auth, _f_http_cookies,
        )
        _t_opt0 = time.perf_counter()
        try:
            try:
                resp = self._dhan.option_chain(
                    under_security_id     = _f_sid,
                    under_exchange_segment= "IDX_I",
                    expiry                = expiry,
                )
            except Exception:
                log.warning(
                    "[DhanForensic] CALL_EXC  symbol=%s  latency_ms=%d",
                    symbol, int((time.perf_counter() - _t_opt0) * 1000),
                )
                raise
            _f_latency_ms = int((time.perf_counter() - _t_opt0) * 1000)
            log.info(
                "[DhanForensic] POST_CALL  symbol=%s  latency_ms=%d"
                "  resp_type=%s  status=%r  remarks=%r  data_preview=%r"
                "  client_drift=%s",
                symbol, _f_latency_ms,
                type(resp).__name__,
                resp.get("status", "?") if isinstance(resp, dict) else "N/A",
                resp.get("remarks") if isinstance(resp, dict) else "N/A",
                str(resp.get("data", ""))[:120] if isinstance(resp, dict) else str(resp)[:120],
                str(id(self._dhan) != _f_cid),
            )
            # ── Defensive protocol-level validation before parser ──────
            if not isinstance(resp, dict):
                log.info(
                    "[DhanOptionsProbe] endpoint=option_chain payload_type=%s "
                    "payload_len=%d payload_preview=%r — expected dict",
                    type(resp).__name__, len(str(resp)), str(resp)[:120],
                )
                self._emit_failure_classified("options_chain", resp, None)   # Phase 3
                log.info(
                    "[DhanOptionsAudit] symbol=%s  expiry=%s  chain_ok=False"
                    "  strike_count=0  oi_coverage=0%%  iv_coverage=0%%  pcr=0"
                    "  synthetic_fallback=True  failure_type=PARSE_FAILURE",
                    symbol, expiry,
                )
                return None
            _status = resp.get("status", "")
            if _status in ("failure", "failed"):
                log.info(
                    "[DhanOptionsProbe] endpoint=option_chain http_status=%s "
                    "remarks=%r data_type=%s data_preview=%r",
                    _status, resp.get("remarks"), type(resp.get("data")).__name__,
                    str(resp.get("data", ""))[:80],
                )
                _ftype = self._classify_dhan_response(resp, None)   # Phase 3
                self._emit_failure_classified("options_chain", resp, None)
                self._dhan_opt_consecutive_failures[symbol] = (
                    self._dhan_opt_consecutive_failures.get(symbol, 0) + 1
                )
                _sym_consec = self._dhan_opt_consecutive_failures[symbol]
                log.info(
                    "[DhanOptionsAudit] symbol=%s  expiry=%s  chain_ok=False"
                    "  strike_count=0  oi_coverage=0%%  iv_coverage=0%%  pcr=0"
                    "  synthetic_fallback=True  failure_type=%s  consecutive=%d",
                    symbol, expiry, _ftype, _sym_consec,
                )
                # Auto-reconnect: stale SDK sessions silently fail for hours;
                # recreate the client after threshold consecutive failures per symbol.
                if _sym_consec >= self._OPT_RECONNECT_THRESHOLD:
                    log.warning(
                        "[DhanOptReconnect] symbol=%s  %d consecutive option_chain failures — "
                        "recreating SDK client to clear stale session",
                        symbol, _sym_consec,
                    )
                    self._dhan_opt_consecutive_failures[symbol] = 0
                    try:
                        self._connect()
                    except Exception as _rc_exc:
                        log.warning("[DhanOptReconnect] reconnect failed: %s", _rc_exc)
                return None
            chain = self._parse_option_chain(symbol, resp, expiry)
            # Phase 6 — [DhanOptionsAudit] after every options chain attempt
            if chain:
                self._dhan_opt_successes += 1   # Phase 7
                self._dhan_opt_consecutive_failures[symbol] = 0   # reset on success
                _strikes   = len(set(c.strike for c in chain.contracts))
                _n         = max(len(chain.contracts), 1)
                _oi_cov    = sum(1 for c in chain.contracts if c.oi  > 0) / _n
                _iv_cov    = sum(1 for c in chain.contracts if c.iv  > 0) / _n
                log.info(
                    "[DhanOptionsAudit] symbol=%s  expiry=%s  chain_ok=True"
                    "  strike_count=%d  oi_coverage=%.1f%%  iv_coverage=%.1f%%"
                    "  pcr=%.3f  synthetic_fallback=False",
                    symbol, expiry,
                    _strikes, _oi_cov * 100, _iv_cov * 100,
                    chain.pcr or 0.0,
                )
            else:
                log.info(
                    "[DhanOptionsAudit] symbol=%s  expiry=%s  chain_ok=False"
                    "  strike_count=0  oi_coverage=0%%  iv_coverage=0%%  pcr=0"
                    "  synthetic_fallback=True  failure_type=PARSE_FAILURE",
                    symbol, expiry,
                )
            return chain
        except Exception as exc:
            self._emit_failure_classified("options_chain", None, exc)   # Phase 3
            log.info(
                "[DhanOptionsAudit] symbol=%s  expiry=%s  chain_ok=False"
                "  strike_count=0  oi_coverage=0%%  iv_coverage=0%%  pcr=0"
                "  synthetic_fallback=True  failure_type=HTTP_FAILURE  exc=%r",
                symbol, expiry, str(exc)[:80],
            )
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
        """Convert Dhan API quote_data/ohlc_data row → TickerQuote."""
        ltp    = float(row.get("last_price",    row.get("ltp",   0)) or 0)
        # Dhan API returns OHLC inside a nested "ohlc" dict; fall back to top-level keys
        _ohlc  = row.get("ohlc") or {}
        open_  = float(row.get("open",  _ohlc.get("open",  row.get("o",           ltp))) or ltp)
        high   = float(row.get("high",  _ohlc.get("high",  row.get("h",           ltp))) or ltp)
        low    = float(row.get("low",   _ohlc.get("low",   row.get("l",           ltp))) or ltp)
        close  = float(row.get("close", _ohlc.get("close", row.get("prev_close",  ltp))) or ltp)
        vol    = float(row.get("volume",        row.get("v",     0)) or 0)
        oi     = float(row.get("open_interest", row.get("oi",    0)) or 0)
        chg    = round(ltp - close, 2)
        chg_p  = round(chg / close * 100, 4) if close else 0.0
        return TickerQuote(
            symbol       = symbol,
            timestamp    = datetime.now(),
            ltp          = ltp,
            open         = open_,
            high         = high,
            low          = low,
            close        = close,
            change       = chg,
            change_pct   = chg_p,
            volume       = vol,
            oi           = oi,
            feed_source  = "DHAN",
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
            symbol       = symbol,
            timestamp    = datetime.fromtimestamp(tick.get("_ts", time.time())),
            ltp          = ltp,
            open         = open_,
            high         = high,
            low          = low,
            close        = close,
            change       = chg,
            change_pct   = chg_p,
            volume       = vol,
            oi           = oi,
            feed_source  = "DHAN_WS",
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
        """Parse Dhan option_chain response → OptionsChain.

        Actual SDK response structure (v2.1+):
            {'status': 'success', 'data': {
                'data': {'last_price': <spot>, 'oc': {
                    '<strike>': {'ce': {..., 'greeks': {...}}, 'pe': {..., 'greeks': {...}}}
                }},
                'status': 'success'
            }}
        """
        if not resp:
            return None
        try:
            # ── Hard type guard — never call .get() on a string ───────
            if not isinstance(resp, dict):
                log.debug(
                    "[DhanFeedFailure] endpoint=option_chain payload_type=%s payload_preview=%r",
                    type(resp).__name__, str(resp)[:120],
                )
                return None
            # Unwrap the double-nested data: resp['data']['data']
            outer = resp.get("data", {})
            inner = outer.get("data", outer) if isinstance(outer, dict) else {}
            # Guard: data field can be "" (empty string) on auth failure
            if not isinstance(inner, dict):
                log.debug(
                    "[DhanFeedFailure] endpoint=option_chain inner_type=%s "
                    "inner_preview=%r (auth failure or empty response)",
                    type(inner).__name__, str(inner)[:80],
                )
                return None

            spot = float(inner.get("last_price", inner.get("underlying_price", 22500)) or 22500)
            oc   = inner.get("oc", {})   # {strike_str: {"ce": {...}, "pe": {...}}}
            if not isinstance(oc, dict) or not oc:
                log.debug(
                    "[DhanFeedFailure] endpoint=option_chain oc_empty oc_type=%s",
                    type(oc).__name__,
                )
                return None

            contracts: List[OptionsContract] = []
            total_call_oi = total_put_oi = 0.0

            for strike_str, strike_data in oc.items():
                if not isinstance(strike_data, dict):
                    continue
                strike = float(strike_str)
                ce = strike_data.get("ce", {})
                pe = strike_data.get("pe", {})

                for opt_type, opt in (("CE", ce), ("PE", pe)):
                    if not isinstance(opt, dict) or not opt:
                        continue
                    greeks = opt.get("greeks", {})
                    greeks = greeks if isinstance(greeks, dict) else {}
                    oi = float(opt.get("oi", 0) or 0)
                    if opt_type == "CE":
                        total_call_oi += oi
                    else:
                        total_put_oi += oi
                    contracts.append(OptionsContract(
                        symbol      = symbol,
                        expiry      = expiry,
                        strike      = strike,
                        option_type = opt_type,
                        ltp         = float(opt.get("last_price", 0) or 0),
                        iv          = float(opt.get("implied_volatility", opt.get("iv", 0)) or 0),
                        delta       = float(greeks.get("delta", 0) or 0),
                        gamma       = float(greeks.get("gamma", 0) or 0),
                        theta       = float(greeks.get("theta", 0) or 0),
                        vega        = float(greeks.get("vega",  0) or 0),
                        oi          = oi,
                        volume      = float(opt.get("volume", 0) or 0),
                        bid         = float(opt.get("top_bid_price", opt.get("bid_price", 0)) or 0),
                        ask         = float(opt.get("top_ask_price", opt.get("ask_price", 0)) or 0),
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
    def _nearest_expiry(symbol: str = "NIFTY") -> str:
        """Return the nearest expiry date for the given NSE index as YYYY-MM-DD.

        Expiry schedule (NSE, post-2024 consolidation):
          NIFTY       → Tuesday  (weekday=1)  — weekly
          FINNIFTY    → Tuesday  (weekday=1)  — monthly only (weekly discontinued)
          MIDCAPNIFTY → Monday   (weekday=0)  — monthly only
          BANKNIFTY   → Tuesday  (weekday=1)  — monthly only (last Tue of month;
                                                weekly expiry discontinued by NSE 2024)
        Used only as fallback when expiry_list() API call is unavailable.
        For BANKNIFTY this returns the nearest Tuesday, which will usually match
        the actual monthly expiry (last Tuesday) or be close enough for a retry.
        """
        _EXPIRY_WEEKDAY = {
            "NIFTY":       1,   # Tuesday
            "FINNIFTY":    1,   # Tuesday
            "MIDCAPNIFTY": 0,   # Monday
            "BANKNIFTY":   1,   # Tuesday (monthly only, last Tue of month; weekly discontinued 2024)
        }
        target_wd = _EXPIRY_WEEKDAY.get(symbol.upper(), 1)  # default Tuesday
        today = date.today()
        days_until = (target_wd - today.weekday()) % 7
        next_expiry = today + timedelta(days=days_until)
        return next_expiry.strftime("%Y-%m-%d")

    # ── yfinance fallback ─────────────────────────────────────────────────

    def _yf_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Fetch OHLC quote from yfinance (used when Dhan Data API not subscribed)."""
        # Strip .NS/.BO suffix — _YF_TICKERS keys are bare symbol names (e.g. "COALINDIA")
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")
        ticker_sym = _YF_TICKERS.get(bare)
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
                symbol          = symbol,
                timestamp       = datetime.now(),
                ltp             = round(ltp, 2),
                open            = round(opn, 2),
                high            = round(high, 2),
                low             = round(low, 2),
                close           = round(prev, 2),
                change          = change,
                change_pct      = change_pct,
                volume          = vol,
                feed_source     = "YAHOO",
                fallback_active = True,
            )
        except Exception as exc:
            log.debug("[DhanFeed] yf_quote(%s) error: %s", symbol, exc)
            return None

    def _yf_ltp(self, symbol: str) -> Optional[float]:
        """Fetch LTP-only from yfinance."""
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")
        ticker_sym = _YF_TICKERS.get(bare)
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
        # Strip .NS/.BO — _SIM_PRICES keys are bare names; prevents 1000-default for Indian equities
        bare  = symbol.upper().replace(".NS", "").replace(".BO", "")
        base  = _SIM_PRICES.get(bare, 1000.0)
        noise = rng.uniform(-0.5, 0.5) / 100
        ltp   = round(base * (1 + noise), 2)
        return TickerQuote(
            symbol          = symbol,
            timestamp       = datetime.now(),
            ltp             = ltp,
            open            = round(ltp * 0.995, 2),
            high            = round(ltp * 1.005, 2),
            low             = round(ltp * 0.990, 2),
            close           = round(ltp * 0.998, 2),
            change          = round(ltp * noise, 2),
            change_pct      = round(noise * 100, 4),
            volume          = float(rng.randint(500_000, 5_000_000)),
            feed_source     = "SIM",
            feed_degraded   = True,
            fallback_active = True,
        )

    def _sim_history(self, symbol: str, days: int) -> List[PriceBar]:
        """Return simulated daily bars for dev/test."""
        import random
        bars  = []
        # Strip .NS/.BO — _SIM_PRICES keys are bare names
        bare  = symbol.upper().replace(".NS", "").replace(".BO", "")
        base  = _SIM_PRICES.get(bare, 1000.0)
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
