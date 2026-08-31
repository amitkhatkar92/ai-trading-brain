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

import csv
import enum
import pathlib
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .yahoo_feed    import YahooFeed
from .nse_feed      import NSEFeed
from .dhan_feed     import DhanFeed
from .base_feed     import TickerQuote, PriceBar, OptionsChain
try:
    from .angelone_feed import AngelOneFeed as _AngelOneFeedCls
    _HAS_ANGELONE = True
except ImportError:
    _AngelOneFeedCls = None  # type: ignore[assignment]
    _HAS_ANGELONE = False
from utils       import get_logger

log = get_logger(__name__)

# ── Market Truth Level ────────────────────────────────────────────────────

class FeedTruthLevel(str, enum.Enum):
    """
    Represents the trustworthiness of market data used in the current cycle.

    LIVE      — ≤30% synthetic  → full confidence
    DEGRADED  — 31–60% synthetic → slight confidence reduction
    CRITICAL  — 61–99% synthetic → position sizes capped
    SYNTHETIC — 100% synthetic   → new trade approvals suppressed
    """
    LIVE      = "LIVE"
    DEGRADED  = "DEGRADED"
    CRITICAL  = "CRITICAL"
    SYNTHETIC = "SYNTHETIC"


_TRUTH_MODIFIERS: Dict[FeedTruthLevel, float] = {
    FeedTruthLevel.LIVE:      1.0,
    FeedTruthLevel.DEGRADED:  0.9,
    FeedTruthLevel.CRITICAL:  0.7,
    FeedTruthLevel.SYNTHETIC: 0.4,
}


class OptionsTruthLevel(str, enum.Enum):
    """
    Options-chain data quality — tracked separately from equity truth.

    LIVE           — live chain fetched <10 min ago (Dhan or NSE API)
    DEGRADED_CACHE — cached live chain, 10–60 min old (still usable)
    SYNTHETIC      — Black-Scholes sim or >60 min stale cache
    """
    LIVE           = "LIVE"
    DEGRADED_CACHE = "DEGRADED_CACHE"
    SYNTHETIC      = "SYNTHETIC"


_OPTIONS_TRUTH_MODIFIERS: Dict[OptionsTruthLevel, float] = {
    OptionsTruthLevel.LIVE:           1.00,
    OptionsTruthLevel.DEGRADED_CACHE: 0.85,
    OptionsTruthLevel.SYNTHETIC:      0.70,
}

# Options chain cache windows
_OPT_CACHE_LIVE_SEC  = 600    # 10 min  — serve cached chain, still count as LIVE
_OPT_CACHE_STALE_SEC = 3600   # 60 min  — cache too old → DEGRADED_CACHE


class _FeedCycleStats:
    """Lightweight per-cycle counter — reset by orchestrator at cycle start."""
    __slots__ = ("dhan_hits", "yahoo_hits", "angelone_hits", "cache_hits", "sim_hits", "nodata_hits", "total")

    def __init__(self) -> None:
        self.dhan_hits     = 0
        self.yahoo_hits    = 0
        self.angelone_hits = 0
        self.cache_hits    = 0  # CACHE-sourced quotes (stale LTP from router cache)
        self.sim_hits      = 0
        self.nodata_hits   = 0  # symbols requested but returned no quote at all
        self.total         = 0

    def record(self, quote: Optional[TickerQuote]) -> None:
        if quote is None:
            return
        self.total += 1
        src = (quote.feed_source or "").upper()
        if src.startswith("DHAN"):
            self.dhan_hits += 1
        elif src == "YAHOO":
            self.yahoo_hits += 1
        elif src == "ANGELONE":
            self.angelone_hits += 1
        elif src == "CACHE":
            self.cache_hits += 1
        else:
            self.sim_hits += 1

    def record_nodata(self, count: int = 1) -> None:
        """Record symbols that were requested but returned no data from any feed."""
        self.nodata_hits += count

    # ── Truth level ────────────────────────────────────────────────────

    def truth_level(self) -> FeedTruthLevel:
        """Classify feed quality for the current cycle."""
        if not self.total:
            return FeedTruthLevel.LIVE   # no data yet — don't penalise early
        sim_pct = self.sim_hits / self.total
        if sim_pct >= 1.0:
            return FeedTruthLevel.SYNTHETIC
        elif sim_pct > 0.60:
            return FeedTruthLevel.CRITICAL
        elif sim_pct > 0.30:
            return FeedTruthLevel.DEGRADED
        return FeedTruthLevel.LIVE

    def truth_modifier(self) -> float:
        """Decision-score modifier: 1.0 (live) → 0.4 (synthetic)."""
        return _TRUTH_MODIFIERS[self.truth_level()]

    def sim_pct(self) -> float:
        return (self.sim_hits / self.total) if self.total else 0.0

    def live_pct(self) -> float:
        live = self.dhan_hits + self.yahoo_hits + self.angelone_hits
        return (live / self.total) if self.total else 0.0

    def summary(self) -> str:
        if not self.total and not self.nodata_hits:
            return "[FeedSummary] feed_summary: no quotes fetched this cycle"
        lvl  = self.truth_level()
        live = self.dhan_hits + self.yahoo_hits + self.angelone_hits
        total_req = self.total + self.nodata_hits
        pct = lambda n: f"{round(n / total_req * 100)}%" if total_req else "0%"
        return (
            f"[FeedSummary] requested={total_req}  "
            f"live={live}({pct(live)})  dhan={self.dhan_hits}  yahoo={self.yahoo_hits}  "
            f"angelone={self.angelone_hits}  "
            f"cache={self.cache_hits}  sim={self.sim_hits}  nodata={self.nodata_hits}  "
            f"truth={lvl}"
        )

# Singleton instance — created once, shared across all components
_INSTANCE: Optional["DataFeedManager"] = None
_INSTANCE_LOCK = threading.Lock()


def get_feed_manager() -> "DataFeedManager":
    global _INSTANCE
    if _INSTANCE is None:
        with _INSTANCE_LOCK:
            if _INSTANCE is None:   # double-checked locking — safe across threads
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


class _DisabledAngelOne:
    """Fallback stub used when angelone_feed module is not installed.

    All callers guard on ``self.angelone.is_live`` before using any methods,
    so a stub with ``is_live = False`` silently routes through to Yahoo/Dhan
    without any code path changes.
    """
    is_live: bool = False

    def get_quote(self, *args, **kwargs):         return None
    def get_multiple_quotes(self, *args, **kwargs): return {}
    def get_history(self, *args, **kwargs):        return []
    def get_options_chain(self, *args, **kwargs):  return None
    def emit_daily_summary(self, *args, **kwargs): pass


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
        self.yahoo    = YahooFeed()
        self.nse      = NSEFeed()
        self.dhan     = DhanFeed()      # PRIMARY Indian data source + order execution
        self.angelone = _AngelOneFeedCls() if _HAS_ANGELONE else _DisabledAngelOne()  # FALLBACK Indian data source (optional)
        self._stats = _FeedCycleStats()
        self._last_yahoo_refresh: Optional[datetime] = None   # Phase 2: track last successful Yahoo refresh
        self._options_synthetic: bool = False   # legacy flag — kept for backward compat
        # Per-symbol options chain state — tracks source, freshness, live/synthetic origin
        # schema: {"chain": OptionsChain|None, "fetched_at": datetime, "source": str, "is_live": bool}
        self._options_chain_state: Dict[str, dict] = {}
        log.info("[DataFeedManager] Initialised. %s", self.status().summary())
        # Hard startup validation — alert explicitly when Dhan is absent
        self._startup_feed_validation()

    def _startup_feed_validation(self) -> None:
        """Log a structured feed validation block at startup."""
        # Dhan is primary — always log its status first
        state = self.dhan.auth_state()
        if not state["token_present"]:
            log.warning(
                "[FeedValidation] Dhan token absent — send /token <token> via Telegram to restore. "
                "Falling back to AngelOne/yfinance for data."
            )
        elif state["token_expired"]:
            log.warning(
                "[FeedValidation] Dhan token EXPIRED — api_mode=FALLBACK. "
                "DTA-001 cron runs at 02:00 IST to refresh automatically."
            )
        else:
            log.info(
                "[FeedValidation] Dhan feed (PRIMARY): token_present=%s  api_mode=%s  expires_in=%s",
                state["token_present"], state["api_mode"], state["expires_in_h"],
            )
        # AngelOne is secondary (TOTP auto-refresh, no daily manual token)
        ao_live = getattr(self.angelone, "is_live", False)
        log.info(
            "[FeedValidation] AngelOne feed (SECONDARY/FALLBACK): is_live=%s",
            ao_live,
        )
        if not ao_live:
            log.info(
                "[FeedValidation] AngelOne not live — set ANGELONE_API_KEY / "
                "ANGELONE_CLIENT_ID / ANGELONE_TOTP_SECRET in .env to activate."
            )
        # Singleton audit — confirm only one instance of each feed is active
        log.info(
            "[FeedSingletonAudit] YahooFeed instances=1  NSEFeed instances=1  "
            "DhanFeed instances=1  DataFeedManager instances=1 — all via get_feed_manager() singleton"
        )

    # ── Status ─────────────────────────────────────────────────────────────

    def status(self) -> FeedStatus:
        return FeedStatus(
            yahoo_live = self.yahoo.is_live,
            nse_live   = self.nse.is_live,
            nse_mode   = self.nse.name,
            dhan_live  = self.dhan.is_live,
        )

    # ── Cycle feed-health tracking ─────────────────────────────────────────

    def reset_cycle_stats(self) -> None:
        """Call at the start of each trading cycle to reset per-cycle counters."""
        self._stats = _FeedCycleStats()

    def get_cycle_stats_summary(self) -> dict:
        """Phase 9: Raw cycle stats dict for Telegram /cycle and orchestrator report."""
        live = self._stats.dhan_hits + self._stats.yahoo_hits + self._stats.angelone_hits
        return {
            "total":    self._stats.total,
            "live":     live,
            "dhan":     self._stats.dhan_hits,
            "yahoo":    self._stats.yahoo_hits,
            "angelone": self._stats.angelone_hits,
            "cache":    self._stats.cache_hits,
            "sim":      self._stats.sim_hits,
            "nodata":   self._stats.nodata_hits,
            "live_pct": round(self._stats.live_pct() * 100),
            "sim_pct":  round(self._stats.sim_pct() * 100),
            "last_yahoo_refresh": (
                self._last_yahoo_refresh.strftime("%H:%M:%S")
                if self._last_yahoo_refresh else None
            ),
        }

    def get_cycle_feed_summary(self) -> str:
        """Return a human-readable per-cycle feed health string for the log."""
        state = self.dhan.auth_state()
        mode  = f"api_mode={state['api_mode']}  expires_in={state['expires_in_h']}"
        opts_lvl, _ = self.get_options_truth_level("NIFTY")
        nifty_state = self._options_chain_state.get("NIFTY", {})
        opts_src    = nifty_state.get("source", "unknown")
        opts_at     = nifty_state.get("fetched_at")
        opts_age    = (
            f"age={int((datetime.now() - opts_at).total_seconds() / 60)}m"
            if opts_at else "age=unknown"
        )
        opts_tag = f"options: src={opts_src} {opts_age} truth={opts_lvl}"
        # Phase 9: add last Yahoo refresh age for operator visibility
        if self._last_yahoo_refresh:
            _age_s = int((datetime.now() - self._last_yahoo_refresh).total_seconds())
            refresh_tag = f"last_yahoo={_age_s}s ago"
        else:
            refresh_tag = "last_yahoo=never_this_cycle"
        return f"{self._stats.summary()}  {mode}  | {opts_tag}  | {refresh_tag}"

    # ── Market Truth Governance (Phase 2) ──────────────────────────────────

    def get_current_truth_level(self) -> Tuple[FeedTruthLevel, float]:
        """Return (truth_level, confidence_modifier) for this cycle's feed stats."""
        lvl = self._stats.truth_level()
        return lvl, _TRUTH_MODIFIERS[lvl]

    @property
    def options_synthetic(self) -> bool:
        """True when both Dhan and NSE option chains are unavailable (Phase 5)."""
        return self._options_synthetic

    def get_options_truth_level(
        self, symbol: str = "NIFTY"
    ) -> Tuple["OptionsTruthLevel", float]:
        """
        Return (OptionsTruthLevel, confidence_modifier) for the named index.

        Source mapping:
          DHAN / NSE                       → LIVE           (1.00)
          CACHE, fetched_at ≤10 min ago    → LIVE           (1.00)
          CACHE, fetched_at >10 min ago    → DEGRADED_CACHE (0.85)
          NSE_SIM / SYNTHETIC / unknown    → SYNTHETIC      (0.70)
        """
        state    = self._options_chain_state.get(symbol, {})
        source   = state.get("source", "SYNTHETIC")
        fetched  = state.get("fetched_at")
        is_live  = state.get("is_live", False)

        if source in ("DHAN", "NSE", "ANGELONE"):
            lvl = OptionsTruthLevel.LIVE
        elif source == "CACHE":
            if fetched and is_live:
                age = (datetime.now() - fetched).total_seconds()
                lvl = (OptionsTruthLevel.LIVE
                       if age <= _OPT_CACHE_LIVE_SEC
                       else OptionsTruthLevel.DEGRADED_CACHE)
            else:
                lvl = OptionsTruthLevel.DEGRADED_CACHE
        else:  # NSE_SIM, SYNTHETIC, or unknown
            lvl = OptionsTruthLevel.SYNTHETIC

        return lvl, _OPTIONS_TRUTH_MODIFIERS[lvl]

    def get_options_capability(self, symbol: str = "NIFTY") -> dict:
        """
        Return per-symbol options capability state.

        chain_live=True only when the source is a real-time feed (Dhan or NSE).
        strategies_enabled follows chain_live — synthetic chains do NOT generate
        options signals (they corrupt IV/OI signals with made-up data).

        Callers should use this instead of a global options_synthetic flag so
        that one index failing never suppresses options intelligence for the other.
        """
        state  = self._options_chain_state.get(symbol, {})
        source = state.get("source", "SYNTHETIC")
        is_live = state.get("is_live", False)

        # ── Lazy live-chain probe ────────────────────────────────────────────
        # get_options_chain(symbol) is NOT always called during a cycle for every
        # symbol — options_feed._warm_loop maintains its own cache independently
        # of _options_chain_state.  If state is SYNTHETIC (empty, or never updated
        # this cycle), probe once via the angelone 300s result cache (fast dict
        # lookup) so the capability report reflects the true feed state.
        if not is_live:
            try:
                _chain = self.get_options_chain(symbol)
                if _chain is not None:
                    state   = self._options_chain_state.get(symbol, {})
                    source  = state.get("source", "SYNTHETIC")
                    is_live = state.get("is_live", False)
            except Exception:
                pass

        chain_live         = bool(is_live and source in ("DHAN", "NSE", "ANGELONE"))
        fallback_synthetic = not chain_live
        strategies_enabled = chain_live

        lvl, modifier = self.get_options_truth_level(symbol)
        return {
            "symbol":             symbol,
            "chain_live":         chain_live,
            "fallback_synthetic": fallback_synthetic,
            "strategies_enabled": strategies_enabled,
            "truth_level":        lvl,
            "modifier":           modifier,
            "source":             source,
        }

    def check_truth_governance(self) -> None:
        """
        Called at end of each cycle.  Emits structured logs and fires targeted
        Telegram alerts — equity truth and options truth are reported separately
        so that options degradation never masks healthy equity feed status.
        """
        equity_lvl, _ = self.get_current_truth_level()
        sim_pct       = self._stats.sim_pct() * 100
        opts_lvl, _   = self.get_options_truth_level("NIFTY")

        # ── Per-index options capability summary ──────────────────────
        _nifty_cap = self.get_options_capability("NIFTY")
        _bnk_cap   = self.get_options_capability("BANKNIFTY")
        log.info(
            "[OptionsCapability] NIFTY chain_live=%-5s strategies_enabled=%-5s source=%-10s "
            "| BANKNIFTY chain_live=%-5s strategies_enabled=%-5s source=%s",
            _nifty_cap["chain_live"], _nifty_cap["strategies_enabled"], _nifty_cap["source"],
            _bnk_cap["chain_live"],   _bnk_cap["strategies_enabled"],   _bnk_cap["source"],
        )

        # ── EQUITY TRUTH ALERTS ────────────────────────────────────────
        if equity_lvl == FeedTruthLevel.SYNTHETIC:
            # Phase 2: log snapshot timing to detect false-SYNTHETIC from timing race
            if self._last_yahoo_refresh:
                _age_s = (datetime.now() - self._last_yahoo_refresh).total_seconds()
                log.info(
                    "[FeedSnapshotTiming] truth=SYNTHETIC last_yahoo_refresh=%s "
                    "refresh_age_s=%.1f yahoo_hits=%d sim_hits=%d nodata=%d",
                    self._last_yahoo_refresh.strftime("%H:%M:%S"), _age_s,
                    self._stats.yahoo_hits, self._stats.sim_hits, self._stats.nodata_hits,
                )
            else:
                log.info(
                    "[FeedSnapshotTiming] truth=SYNTHETIC no_yahoo_refresh_this_cycle "
                    "yahoo_hits=%d sim_hits=%d nodata=%d",
                    self._stats.yahoo_hits, self._stats.sim_hits, self._stats.nodata_hits,
                )

            # Phase 3: single synchronous refresh attempt before declaring suppression
            # Only trigger when we have ZERO live hits (not merely majority-sim)
            if self._stats.yahoo_hits == 0 and self._stats.dhan_hits == 0 and self._stats.angelone_hits == 0:
                self._try_emergency_equity_refresh()
                # Re-evaluate — if refresh recovered live data, stand down
                equity_lvl, _ = self.get_current_truth_level()
                if equity_lvl != FeedTruthLevel.SYNTHETIC:
                    log.info(
                        "[FeedGovernance] Emergency refresh resolved SYNTHETIC → %s "
                        "— suppression cancelled", equity_lvl,
                    )
                    return

            msg = (
                f"⚠️ EQUITY_TRUTH_SYNTHETIC\n"
                f"Synthetic equity usage: {sim_pct:.0f}%\n"
                f"Dhan unavailable · Yahoo unavailable\n"
                f"New equity trade approvals SUPPRESSED until live data restored."
            )
            log.warning(
                "[MarketTruthGovernor] EQUITY_SYNTHETIC (%.0f%% sim) "
                "— new equity trade approvals SUPPRESSED",
                sim_pct,
            )
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().market_alert("⚠️ EQUITY TRUTH SYNTHETIC", msg)
            except Exception:
                pass

        elif equity_lvl == FeedTruthLevel.CRITICAL:
            log.warning(
                "[MarketTruthGovernor] EQUITY_CRITICAL (%.0f%% sim) "
                "— FULL trades downgraded to PARTIAL",
                sim_pct,
            )
        elif equity_lvl == FeedTruthLevel.DEGRADED:
            log.info(
                "[MarketTruthGovernor] EQUITY_DEGRADED (%.0f%% sim) — score modifier=0.9",
                sim_pct,
            )
        else:  # LIVE
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().mark_alert_cleared("EQUITY_TRUTH")
            except Exception:
                pass

        # ── OPTIONS TRUTH ALERTS (separate domain) ────────────────────
        if opts_lvl == OptionsTruthLevel.SYNTHETIC:
            if equity_lvl in (FeedTruthLevel.LIVE, FeedTruthLevel.DEGRADED):
                # Options degraded but equity healthy — targeted alert
                # Phase 9: append Dhan runtime context so alert explains WHY
                _dhan_ctx = ""
                try:
                    if hasattr(self, "dhan") and hasattr(self.dhan, "get_runtime_context_str"):
                        _dhan_ctx = "\n" + self.dhan.get_runtime_context_str()
                except Exception:
                    pass
                _degraded_indices = [
                    sym for sym in ("NIFTY", "BANKNIFTY")
                    if not self.get_options_capability(sym)["chain_live"]
                ]
                _live_indices = [
                    sym for sym in ("NIFTY", "BANKNIFTY")
                    if self.get_options_capability(sym)["chain_live"]
                ]
                opts_msg = (
                    "⚠️ OPTIONS CHAIN DEGRADED\n"
                    f"Degraded: {', '.join(_degraded_indices) or 'none'}\n"
                    f"Live:     {', '.join(_live_indices) or 'none'}\n"
                    "Equity prices remain LIVE.\n"
                    "Using synthetic options intelligence (Black-Scholes IV/OI).\n"
                    f"Options strategies suppressed for: {', '.join(_degraded_indices) or 'none'}."
                    + _dhan_ctx
                )
                log.warning(
                    "[OptionsGovernance] OPTIONS_TRUTH_SYNTHETIC "
                    "degraded=%s live=%s "
                    "— equity=%s healthy; equity trades continue with 60%% size cap",
                    _degraded_indices, _live_indices, equity_lvl,
                )
                # Phase 9: tag runtime mode at point of options degradation
                try:
                    if hasattr(self, "dhan") and hasattr(self.dhan, "emit_runtime_mode_tag"):
                        self.dhan.emit_runtime_mode_tag("options_chain_degraded")
                except Exception:
                    pass
                try:
                    from notifications.notifier_manager import get_notifier
                    get_notifier().market_alert("⚠️ OPTIONS CHAIN DEGRADED", opts_msg)
                except Exception:
                    pass
            else:
                # Both equity and options degraded
                log.warning(
                    "[OptionsGovernance] FULL_MARKET_SYNTHETIC "
                    "— equity=%s options=SYNTHETIC; all trade approvals suppressed",
                    equity_lvl,
                )
        elif opts_lvl == OptionsTruthLevel.DEGRADED_CACHE:
            log.info(
                "[OptionsGovernance] OPTIONS_DEGRADED_CACHE "
                "— serving cached chain; options confidence modifier=0.85",
            )
        else:  # LIVE
            try:
                from notifications.notifier_manager import get_notifier
                get_notifier().mark_alert_cleared("OPTIONS_CHAIN")
            except Exception:
                pass

        # Phase 9: record current Dhan runtime mode once per check cycle
        try:
            if hasattr(self, "dhan") and hasattr(self.dhan, "record_cycle_mode"):
                self.dhan.record_cycle_mode()
        except Exception:
            pass

        # Phase 11: re-trigger readiness probe when market opens and equity not yet verified
        try:
            if hasattr(self, "dhan") and hasattr(self.dhan, "check_market_open_readiness"):
                self.dhan.check_market_open_readiness()
        except Exception:
            pass

    def _try_emergency_equity_refresh(self) -> None:
        """Phase 3: Single synchronous Yahoo probe when SYNTHETIC + zero live hits detected.

        Fetches 3 key symbols to determine if Yahoo is actually reachable.
        If quotes are recovered, they are added to _stats so truth_level()
        re-evaluates before the suppression alert fires.  Single attempt only —
        no infinite loops.
        """
        try:
            log.info(
                "[FeedGovernance] SYNTHETIC with 0 live hits — "
                "attempting single emergency Yahoo probe (3 symbols)…"
            )
            _probe = ["NIFTY", "HDFCBANK.NS", "RELIANCE.NS"]
            result = self.yahoo.get_multiple_quotes(_probe)
            recovered = 0
            for q in result.values():
                if q and getattr(q, "ltp", 0) > 0:
                    self._stats.record(q)
                    recovered += 1
            if recovered:
                self._last_yahoo_refresh = datetime.now()
                log.info(
                    "[FeedGovernance] Emergency probe recovered %d/%d Yahoo quotes "
                    "— re-evaluating truth level",
                    recovered, len(_probe),
                )
            else:
                log.warning(
                    "[FeedGovernance] Emergency probe returned 0 live quotes "
                    "— Yahoo genuinely unavailable. SYNTHETIC suppression stands."
                )
        except Exception as _e:
            log.debug("[FeedGovernance] Emergency probe failed: %s", _e)

    def write_cycle_audit(self) -> None:
        """Phase 7: append per-cycle feed stats to a persistent CSV for post-hoc analysis."""
        try:
            _root = pathlib.Path("/app/data") if pathlib.Path("/app").exists() else pathlib.Path("data")
            audit_path = _root / "feed_audit.csv"
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            lvl, mod = self.get_current_truth_level()
            opts_lvl, _ = self.get_options_truth_level("NIFTY")
            nifty_st    = self._options_chain_state.get("NIFTY", {})
            row = {
                "ts":              datetime.now(timezone.utc).isoformat(),
                "total":           self._stats.total,
                "dhan":            self._stats.dhan_hits,
                "yahoo":           self._stats.yahoo_hits,
                "angelone":        self._stats.angelone_hits,
                "cache":           self._stats.cache_hits,
                "sim":             self._stats.sim_hits,
                "nodata":          self._stats.nodata_hits,
                "live":            self._stats.dhan_hits + self._stats.yahoo_hits + self._stats.angelone_hits,
                "sim_pct":         round(self._stats.sim_pct() * 100, 1),
                "live_pct":        round(self._stats.live_pct() * 100, 1),
                "equity_truth":    lvl.value,
                "modifier":        mod,
                "opts_truth":      opts_lvl.value,
                "opts_source":     nifty_st.get("source", "unknown"),
                "opts_is_live":    int(nifty_st.get("is_live", False)),
                "last_yahoo_refresh": (
                    self._last_yahoo_refresh.strftime("%H:%M:%S")
                    if self._last_yahoo_refresh else ""
                ),
            }
            is_new = not audit_path.exists()
            with audit_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if is_new:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            log.debug("[FeedAudit] Write failed: %s", e)

    # ── Quotes ─────────────────────────────────────────────────────────────

    # Global symbols that AngelOne cannot serve — routed directly to Yahoo
    _GLOBAL_SYMBOLS = frozenset({
        "SP500", "NASDAQ", "DOW", "NIKKEI", "HANGSENG",
        "SHANGHAI", "KOSPI", "USDINR", "DXY", "EURUSD",
        "GBPUSD", "GOLD", "SILVER", "CRUDE_WTI", "CRUDE_BRENT",
        "NATURAL_GAS", "US10Y", "VIX",
    })

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Get a market quote. Indian symbols: AngelOne → Dhan → Yahoo. Global: Yahoo."""
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")
        if bare not in self._GLOBAL_SYMBOLS:
            # Dhan: primary Indian data source
            from .dhan_feed import DHAN_SECURITY_MAP
            if self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP:
                q = self.dhan.get_quote(symbol)
                if q and q.ltp > 0:
                    self._stats.record(q)
                    return q
            # AngelOne: fallback for Indian symbols
            if self.angelone.is_live:
                q = self.angelone.get_quote(bare)
                if q and q.ltp > 0:
                    self._stats.record(q)
                    return q
        q = self.yahoo.get_quote(symbol)
        self._stats.record(q)
        return q

    def get_indian_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Get an Indian market quote — Dhan primary, AngelOne fallback, then NSEFeed."""
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")
        if self.dhan.is_live:
            q = self.dhan.get_quote(symbol)
            if q and q.ltp > 0:
                self._stats.record(q)
                return q
        if self.angelone.is_live:
            q = self.angelone.get_quote(bare)
            if q and q.ltp > 0:
                self._stats.record(q)
                return q
        q = self.nse.get_quote(symbol)
        self._stats.record(q)
        return q

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Batch fetch quotes. Indian symbols: Dhan → AngelOne → Yahoo. Global: Yahoo.

        Dhan is the primary Indian feed (also used for order execution).
        AngelOne is fallback for symbols Dhan misses. Yahoo handles global symbols.

        Phase 1 (FeedTrace): emits [FeedTrace] DEBUG logs at each stage.
        Phase 2 (Timing):    tracks self._last_yahoo_refresh on any Yahoo hit.
        Phase 4 (NoData):    records symbols that return no quote from any feed.
        """
        import time as _t

        def _bare(s: str) -> str:
            return s.upper().replace(".NS", "").replace(".BO", "")

        _t0 = _t.monotonic()
        result: Dict[str, TickerQuote] = {}

        # Split: global symbols always go to Yahoo; Indian symbols try AngelOne first
        global_ = [s for s in symbols if _bare(s) in self._GLOBAL_SYMBOLS]
        indian  = [s for s in symbols if _bare(s) not in self._GLOBAL_SYMBOLS]

        # ── Dhan: primary for all Indian symbols ─────────────────────────────
        if self.dhan.is_live and indian:
            from .dhan_feed import DHAN_SECURITY_MAP
            dhan_candidates = [s for s in indian if _bare(s) in DHAN_SECURITY_MAP]
            if dhan_candidates:
                dhan_result = self.dhan.get_multiple_quotes(dhan_candidates)
                result.update(dhan_result)
                log.debug("[FeedTrace] stage=DHAN_PRIMARY requested=%d returned=%d",
                          len(dhan_candidates), len(dhan_result))
            ao_missed = [s for s in indian if s not in result]
        else:
            ao_missed = indian

        # ── AngelOne: fallback for what Dhan missed ───────────────────────────
        if ao_missed and self.angelone.is_live:
            ao_result = self.angelone.get_multiple_quotes(ao_missed)
            result.update(ao_result)
            log.debug("[FeedTrace] stage=ANGELONE_FALLBACK requested=%d returned=%d",
                      len(ao_missed), len(ao_result))
            ao_missed = [s for s in ao_missed if s not in ao_result]

        # ── Yahoo: global symbols + any Indian still missed ───────────────────
        yahoo_targets = global_ + ao_missed
        if yahoo_targets:
            result.update(self.yahoo.get_multiple_quotes(yahoo_targets))

        # Phase 2: track last time Yahoo actually delivered a live quote
        if any((getattr(q, "feed_source", "") or "").upper() == "YAHOO"
               for q in result.values()):
            self._last_yahoo_refresh = datetime.now()

        # Phase 4: count symbols that returned no quote from any feed
        nodata = len(symbols) - len(result)
        if nodata > 0:
            self._stats.record_nodata(nodata)

        for q in result.values():
            self._stats.record(q)

        # Phase 1 FeedTrace aggregate — logged at DEBUG to avoid cycle spam
        _live   = sum(1 for q in result.values()
                      if (getattr(q, "feed_source", "") or "").upper() in ("DHAN", "YAHOO", "ANGELONE"))
        _sim    = sum(1 for q in result.values()
                      if (getattr(q, "feed_source", "") or "").upper() == "SIM")
        _ms     = int((_t.monotonic() - _t0) * 1000)
        log.debug(
            "[FeedTrace] stage=ROUTER_AGGREGATE requested=%d result=%d "
            "live=%d sim=%d nodata=%d elapsed_ms=%d",
            len(symbols), len(result), _live, _sim, nodata, _ms,
        )
        return result

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
        Priority: AngelOneFeed → DhanFeed → NSEFeed (indian) → YahooFeed.
        """
        bare = symbol.upper().replace(".NS", "").replace(".BO", "")
        # Dhan: primary for NSE equities and indices (skip for long-period requests
        # — Dhan supports ~1 year max; fall through to Yahoo for historical replay)
        _MAX_DHAN_DAYS = 365
        from .dhan_feed import DHAN_SECURITY_MAP
        if (self.dhan.is_live and symbol.upper() in DHAN_SECURITY_MAP
                and bare not in self._GLOBAL_SYMBOLS and days <= _MAX_DHAN_DAYS):
            bars = self.dhan.get_history(symbol, days, interval)
            if bars:
                return bars
        # AngelOne: fallback for Indian symbols
        if self.angelone.is_live and bare not in self._GLOBAL_SYMBOLS:
            ao_bars = self.angelone.get_history(bare, days, interval)
            if ao_bars:
                return ao_bars
        if indian:
            return self.nse.get_history(symbol, days, interval)
        return self.yahoo.get_history(symbol, days, interval)

    # ── Options ────────────────────────────────────────────────────────────

    def get_options_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> Optional[OptionsChain]:
        """Get options chain.

        Fallback hierarchy (phases 3-4):
          1. Dhan live chain
          2. NSE live chain (is_live=True only)
          3. Cached live chain ≤10 min old (DEGRADED_CACHE but still usable)
          4. NSE sim chain (Black-Scholes synthetic)

        State is recorded in self._options_chain_state[symbol] for
        downstream truth governance queries.
        """
        now   = datetime.now()
        state = self._options_chain_state.get(symbol, {})
        cached_chain = state.get("chain")
        cached_at    = state.get("fetched_at")
        cached_live  = state.get("is_live", False)
        cache_age    = (now - cached_at).total_seconds() if cached_at else float("inf")

        # ── 60-second intra-cycle cache — avoids duplicate Dhan calls ─
        # If we fetched a live chain within the last 60 s (same cycle),
        # return the cached result immediately without a new API hit.
        if cached_live and cached_chain is not None and cache_age <= 60:
            return cached_chain

        # ── Try AngelOne live chain (primary — TOTP auto-reconnects) ────────
        # Do NOT gate on is_live: get_options_chain() calls _refresh_if_needed()
        # internally which auto-reconnects expired sessions.
        live_chain, live_source = None, None
        try:
            live_chain = self.angelone.get_options_chain(symbol, expiry)
            if live_chain:
                live_source = "ANGELONE"
                # ── OI Trace: chain_builder stage ────────────────────────────
                _cb_with_oi = sum(1 for c in live_chain.contracts if (c.oi or 0) > 0)
                log.debug(
                    "[OptionsOITrace] stage=chain_builder symbol=%s source=ANGELONE "
                    "contracts=%d contracts_with_oi=%d total_oi=%.0f pcr=%.4f",
                    symbol, len(live_chain.contracts),
                    _cb_with_oi, live_chain.total_oi or 0, live_chain.pcr or 0,
                )
        except Exception as _ao_exc:
            log.debug("[FeedManager] AngelOne options chain %s failed: %s", symbol, _ao_exc)

        # ── Try Dhan live chain (fallback) ────────────────────────────
        if live_chain is None and self.dhan.is_live:
            live_chain = self.dhan.get_options_chain(symbol, expiry)
            if live_chain:
                live_source = "DHAN"

        # ── Try NSE live chain ─────────────────────────────────────────
        nse_chain = None
        if live_chain is None:
            nse_chain = self.nse.get_options_chain(symbol, expiry)
            if nse_chain and getattr(nse_chain, "is_live", False):
                live_chain   = nse_chain
                live_source  = "NSE"

        # ── Got a live chain — update cache and return ─────────────────
        if live_chain is not None:
            self._options_chain_state[symbol] = {
                "chain": live_chain, "fetched_at": now,
                "source": live_source, "is_live": True,
            }
            self._options_synthetic = False
            log.info(
                "[OptionsTruth] symbol=%s source=%s state=LIVE",
                symbol, live_source,
            )
            return live_chain

        # ── No live chain — check 10-min cache ────────────────────────
        if cached_chain is not None and cached_live and cache_age <= _OPT_CACHE_LIVE_SEC:
            age_m = int(cache_age / 60)
            log.info(
                "[OptionsTruth] symbol=%s source=CACHE age=%dm state=DEGRADED_CACHE",
                symbol, age_m,
            )
            self._options_chain_state[symbol] = dict(state, source="CACHE")
            self._options_synthetic = False
            return cached_chain

        # ── Cache stale/absent — fall back to NSE sim chain ───────────
        sim_chain = nse_chain if nse_chain is not None else self.nse.get_options_chain(symbol, expiry)
        if sim_chain is None:
            self._options_synthetic = True
            self._options_chain_state[symbol] = {
                "chain": None, "fetched_at": now,
                "source": "SYNTHETIC", "is_live": False,
            }
            log.info(
                "[OptionsTruth] symbol=%s source=SYNTHETIC state=SYNTHETIC "
                "— no live chain or usable cache",
                symbol,
            )
        else:
            self._options_synthetic = False
            self._options_chain_state[symbol] = {
                "chain": sim_chain, "fetched_at": now,
                "source": "NSE_SIM", "is_live": False,
            }
            log.info(
                "[OptionsTruth] symbol=%s source=NSE_SIM state=SYNTHETIC",
                symbol,
            )
        return sim_chain

    def get_pcr(self, symbol: str = "NIFTY") -> float:
        """Put-Call Ratio — from live options chain (updates state tracking)."""
        chain = self.get_options_chain(symbol)
        if chain and chain.pcr:
            return chain.pcr
        return 0.85  # neutral default

    def get_cached_pcr(self, symbol: str = "NIFTY") -> tuple:
        """Read PCR from the in-memory options chain cache — ZERO network I/O.

        Does NOT call get_options_chain() or trigger any HTTP request.
        Reads directly from _options_chain_state which is populated by the
        background AngelOne refresh loop (~every 9 min during market hours).

        Returns:
            (pcr: float | None, age_seconds: float, source: str)
            pcr is None when no cached chain exists or PCR value is invalid.
        """
        from datetime import datetime as _dt
        state      = self._options_chain_state.get(symbol, {})
        chain      = state.get("chain")
        fetched_at = state.get("fetched_at")
        source     = state.get("source", "NONE")

        age_seconds = (
            (_dt.now() - fetched_at).total_seconds()
            if fetched_at is not None
            else float("inf")
        )

        if chain is not None and chain.pcr and 0.1 < chain.pcr < 5.0:
            return (round(chain.pcr, 4), age_seconds, source)
        return (None, age_seconds, source)

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
            "usdinr_rate":     (self.dhan.get_ltp("USDINR") if self.dhan.is_live else 0)
                               or q("USDINR") or 83.5,
            "usdinr_change":   chg("USDINR"),
            "dxy_level":       q("DXY"),          # was "dxy" — field name fix
            "dxy_change":      chg("DXY"),
            "eurusd":          q("EURUSD"),
            # Commodities
            "gold_price":      q("GOLD"),
            "gold_change":     chg("GOLD"),
            "crude_wti":       q("CRUDE_WTI"),
            "crude_wti_change": chg("CRUDE_WTI"),  # was "crude_change" — field name fix
            "crude_brent":     q("CRUDE_BRENT"),
            "crude_brent_change": chg("CRUDE_BRENT"),
            # Vol / Bonds
            "cboe_vix":        q("VIX"),          # was "vix" — field name fix
            "us10y_yield":     q("US10Y"),         # was "us_10y_yield" — field name fix
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
