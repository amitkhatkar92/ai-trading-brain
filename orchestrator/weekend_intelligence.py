"""
Weekend Intelligence Engine
============================
Implements the WEEKEND_INTELLIGENCE_OPERATING_PRINCIPLE.

Weekend periods are high-value intelligence accumulation windows, not idle time.

Saturday — deep market intelligence accumulation
Sunday   — Monday tactical preparation

GOVERNANCE INVARIANT:
    This engine is STRICTLY READ-AND-REPORT.  It MUST NOT:
      - modify EXPLORATION_BUDGET_PCT or EXPLORATION_THRESHOLD
      - enable or disable any strategy
      - alter scoring weights or thresholds
      - bypass mutation freeze (MIN_CLEAN_PREPARED_TRADES)
      - call any adaptive learning mutation function
      - alter Layer 5+ governance parameters

    All output is observational telemetry.
    The only write permitted is run_scan() which produces daily_candidates.json
    — the same write that happens on weekday post-market scans.

Telemetry tags emitted:
    [WeekendResearch]         — Saturday main banner + sub-tasks
    [MondayPreparation]       — Sunday main banner + sub-tasks
    [SectorLeadership]        — top sector leaders identified
    [ExplorationReview]       — exploration stats from current session
    [PreparedUniverseRefresh] — candidate store refresh result
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

if TYPE_CHECKING:
    from orchestrator.master_orchestrator import MasterOrchestrator


# ── Governance sentinel — called at start of every mutation-adjacent path ───
def _assert_read_only(context: str) -> None:
    """
    Documents the governance invariant at the call site.
    Does not raise — intentionally a marker, not a guard.
    The WeekendIntelligenceEngine is read-only by design; no mutation
    function should ever be called from this module.
    """
    log.debug("[WeekendResearch] READ-ONLY assertion at: %s", context)


class WeekendIntelligenceEngine:
    """
    Drives Saturday and Sunday intelligence cycles.

    Instantiated once by MasterOrchestrator.__init__() and wired into
    the scheduler via _run_saturday_intelligence() and
    _run_sunday_intelligence().
    """

    def __init__(self, orchestrator: "MasterOrchestrator") -> None:
        self._orch = orchestrator

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINTS
    # ─────────────────────────────────────────────────────────────────────────

    def run_saturday_cycle(self) -> None:
        """
        Saturday: full deep market intelligence accumulation.

        Tasks (all observational except Phase D rescan which writes candidates):
          1. Phase D full Nifty500 rescan  → refreshes daily_candidates.json
          2. Sector rotation analysis
          3. Volatility regime snapshot
          4. Leadership mapping (top candidates by score)
          5. Sector concentration review
          6. Exploration telemetry review
          7. Prepared-universe health review
          8. Stale candidate cleanup check
          9. Scanner coverage validation
        """
        import config as cfg

        if not getattr(cfg, "WEEKEND_INTELLIGENCE_ENABLED", True):
            log.info("[WeekendResearch] WEEKEND_INTELLIGENCE_ENABLED=False — Saturday cycle skipped.")
            return

        _assert_read_only("saturday_cycle_start")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        log.info("━" * 60)
        log.info("  [WeekendResearch] SATURDAY INTELLIGENCE CYCLE — %s", ts)
        log.info("  Objective: deep accumulation for preparedness")
        log.info("━" * 60)

        # ── Task 1: Full Nifty500 rescan (Phase D) ────────────────────
        self._saturday_rescan()

        # ── Task 2 + 3: Sector rotation + volatility regime ───────────
        market_data = self._fetch_market_data()
        if market_data:
            self._saturday_sector_analysis(market_data)
            self._saturday_regime_snapshot(market_data)

        # ── Task 4 + 5: Leadership + concentration from candidate store ──
        self._saturday_leadership_and_concentration()

        # ── Task 6: Exploration telemetry review ──────────────────────
        self._saturday_exploration_telemetry()

        # ── Task 7 + 8 + 9: Prepared-universe health + staleness + coverage ─
        self._saturday_prepared_universe_health()

        log.info("━" * 60)
        log.info("  [WeekendResearch] SATURDAY COMPLETE — %s",
                 datetime.now().strftime("%H:%M"))
        log.info("  Next: Sunday 09:00 IST Monday preparation cycle")
        log.info("━" * 60)

    def run_sunday_cycle(self) -> None:
        """
        Sunday: Monday tactical preparation.

        Tasks:
          1. Global market context refresh (pre-warms GlobalDataAI for Monday)
          2. Macro context summary (global intelligence snapshot)
          3. Top Monday candidate ranking (from candidate store)
          4. Regime-bias preparation
          5. Sector prioritization
          6. Risk concentration check
          7. Exploration focus planning (which sectors to watch)
          8. Premarket readiness summary
        """
        import config as cfg

        if not getattr(cfg, "WEEKEND_INTELLIGENCE_ENABLED", True):
            log.info("[MondayPreparation] WEEKEND_INTELLIGENCE_ENABLED=False — Sunday cycle skipped.")
            return

        _assert_read_only("sunday_cycle_start")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        log.info("━" * 60)
        log.info("  [MondayPreparation] SUNDAY INTELLIGENCE CYCLE — %s", ts)
        log.info("  Objective: Monday tactical preparation")
        log.info("━" * 60)

        # ── Task 1 + 2: Global context refresh + macro summary ────────
        global_snapshot = self._sunday_global_refresh()

        # ── Task 3: Monday candidate ranking ─────────────────────────
        self._sunday_monday_ranking()

        # ── Task 4 + 5: Regime bias + sector prioritization ───────────
        market_data = self._fetch_market_data()
        if market_data:
            self._sunday_regime_bias(market_data, global_snapshot)
            self._sunday_sector_priority(market_data)

        # ── Task 6: Risk concentration check ─────────────────────────
        self._sunday_concentration_check()

        # ── Task 7: Exploration focus planning ────────────────────────
        self._sunday_exploration_focus()

        # ── Task 8: Premarket readiness summary + Telegram ────────────
        self._sunday_readiness_summary(global_snapshot)

        log.info("━" * 60)
        log.info("  [MondayPreparation] SUNDAY COMPLETE — %s",
                 datetime.now().strftime("%H:%M"))
        log.info("  System is prepared for Monday market open.")
        log.info("━" * 60)

    # ─────────────────────────────────────────────────────────────────────────
    # SATURDAY TASK IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _saturday_rescan(self) -> None:
        """Run Phase D full Nifty500 scan to refresh daily_candidates.json."""
        log.info("[WeekendResearch] Task 1 — Full Nifty500 rescan (Phase D)")
        try:
            from opportunity_engine.market_scanner import run_scan
            success = run_scan()
            if success:
                log.info("[PreparedUniverseRefresh] Phase D rescan COMPLETE — candidate store updated.")
            else:
                log.warning("[PreparedUniverseRefresh] Phase D rescan returned failure — store unchanged.")
        except Exception as exc:
            log.error("[WeekendResearch] Phase D rescan crashed: %s", exc, exc_info=True)

    def _saturday_sector_analysis(self, market_data: Dict[str, Any]) -> None:
        """Run sector rotation analysis and log sector leaders."""
        log.info("[WeekendResearch] Task 2 — Sector rotation analysis")
        try:
            result = self._orch.sector_rotation_ai.analyse(market_data)
            log.info("[SectorLeadership] %s", result.summary)
            sector_data = result.data or {}
            leaders = sector_data.get("leaders", [])
            laggards = sector_data.get("laggards", [])
            if leaders:
                log.info("[SectorLeadership] Leading sectors: %s",
                         ", ".join(str(s) for s in leaders[:5]))
            if laggards:
                log.info("[SectorLeadership] Lagging sectors: %s",
                         ", ".join(str(s) for s in laggards[:5]))
        except Exception as exc:
            log.warning("[WeekendResearch] Sector analysis failed: %s", exc)

    def _saturday_regime_snapshot(self, market_data: Dict[str, Any]) -> None:
        """Run volatility/regime classification and log snapshot."""
        log.info("[WeekendResearch] Task 3 — Volatility regime snapshot")
        try:
            global_snapshot = self._orch.global_intelligence.data_ai.fetch()
            global_bias = getattr(global_snapshot, "bias", "neutral") \
                if global_snapshot else "neutral"
            global_score = getattr(global_snapshot, "sentiment_score", 0.0) \
                if global_snapshot else 0.0
            result = self._orch.market_regime_ai.classify(
                market_data,
                global_bias=str(global_bias),
                global_sentiment_score=float(global_score),
            )
            vix  = result.data.get("vix", 0.0) if result.data else 0.0
            pcr  = result.data.get("pcr", 0.0) if result.data else 0.0
            regime = str(result.data.get("regime", "unknown")) if result.data else "unknown"
            vol    = str(result.data.get("volatility", "unknown")) if result.data else "unknown"
            log.info(
                "[WeekendResearch] Regime=%s  Volatility=%s  VIX=%.1f  PCR=%.2f",
                regime, vol, vix, pcr,
            )
        except Exception as exc:
            log.warning("[WeekendResearch] Regime snapshot failed: %s", exc)

    def _saturday_leadership_and_concentration(self) -> None:
        """Read candidate store and log top candidates + sector concentration."""
        log.info("[WeekendResearch] Tasks 4+5 — Leadership mapping + concentration review")
        try:
            from opportunity_engine.candidate_store import CandidateStore
            candidates = CandidateStore.read()
            if not candidates:
                log.info("[WeekendResearch] Candidate store empty or stale — no leadership data.")
                return

            # Sort by score descending
            sorted_cands = sorted(
                candidates,
                key=lambda c: float(c.get("score", 0.0)),
                reverse=True,
            )
            top_n = sorted_cands[:10]
            log.info("[SectorLeadership] Top 10 prepared candidates by score:")
            for i, c in enumerate(top_n, 1):
                log.info(
                    "[SectorLeadership]   %2d. %-18s  score=%.2f  sector=%-20s  rsi=%.1f",
                    i,
                    c.get("symbol", "?"),
                    float(c.get("score", 0.0)),
                    c.get("sector", "?"),
                    float(c.get("rsi", 0.0)),
                )

            # Sector concentration
            sector_counts = Counter(c.get("sector", "UNKNOWN") for c in candidates)
            total = len(candidates)
            log.info("[WeekendResearch] Sector concentration (%d candidates):", total)
            for sector, count in sector_counts.most_common(10):
                pct = count / total * 100
                log.info("[WeekendResearch]   %-25s  %2d  (%.0f%%)", sector, count, pct)

        except Exception as exc:
            log.warning("[WeekendResearch] Leadership/concentration analysis failed: %s", exc)

    def _saturday_exploration_telemetry(self) -> None:
        """Log exploration session stats and rejection analysis."""
        log.info("[WeekendResearch] Task 6 — Exploration telemetry review")
        try:
            from opportunity_engine.equity_scanner_ai import _EXPLORE_STATS
            evaluated         = _EXPLORE_STATS.get("evaluated", 0)
            signals_generated = _EXPLORE_STATS.get("signals_generated", 0)
            hit_rate = signals_generated / evaluated if evaluated > 0 else 0.0

            log.info(
                "[ExplorationReview] Session exploration stats:"
                "  evaluated=%d  signals=%d  hit_rate=%.1f%%",
                evaluated, signals_generated, hit_rate * 100,
            )

            import config as cfg
            budget_pct = getattr(cfg, "EXPLORATION_BUDGET_PCT", -1)
            threshold  = getattr(cfg, "EXPLORATION_THRESHOLD", -1.0)
            log.info(
                "[ExplorationReview] Config: EXPLORATION_BUDGET_PCT=%d  "
                "EXPLORATION_THRESHOLD=%.1f",
                budget_pct, threshold,
            )

        except Exception as exc:
            log.warning("[WeekendResearch] Exploration telemetry review failed: %s", exc)

    def _saturday_prepared_universe_health(self) -> None:
        """Validate candidate store freshness, coverage, and staleness."""
        log.info("[WeekendResearch] Tasks 7+8+9 — Prepared-universe health + stale check + coverage")
        try:
            from opportunity_engine.candidate_store import (
                CandidateStore,
                STORE_FILE,
                MAX_AGE_HOURS,
            )
            from opportunity_engine.equity_scanner_ai import _LAST_PREPARED_STATS

            is_fresh = CandidateStore.is_fresh()
            log.info(
                "[PreparedUniverseRefresh] Candidate store fresh=%s  file=%s",
                is_fresh, STORE_FILE,
            )

            if _LAST_PREPARED_STATS:
                log.info("[PreparedUniverseRefresh] Last prepared stats: %s", _LAST_PREPARED_STATS)

            # Read raw payload for detailed stats
            if STORE_FILE.exists():
                try:
                    payload = json.loads(STORE_FILE.read_text(encoding="utf-8"))
                    stats   = payload.get("scanner_stats", {})
                    prepared_at = payload.get("prepared_at", "unknown")
                    coverage = float(stats.get("coverage_pct", 0.0))
                    n_candidates = len(payload.get("candidates", []))
                    log.info(
                        "[PreparedUniverseRefresh] prepared_at=%s  coverage=%.1f%%  "
                        "candidates=%d  max_age=%dh",
                        prepared_at, coverage, n_candidates, MAX_AGE_HOURS,
                    )
                    if coverage < 80.0:
                        log.warning(
                            "[PreparedUniverseRefresh] Coverage %.1f%% below 80%% — "
                            "scanner universe may need attention.",
                            coverage,
                        )
                except Exception as _je:
                    log.debug("[PreparedUniverseRefresh] Payload read error: %s", _je)
            else:
                log.warning("[PreparedUniverseRefresh] No candidate store file found at %s", STORE_FILE)

        except Exception as exc:
            log.warning("[WeekendResearch] Prepared-universe health check failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # SUNDAY TASK IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _sunday_global_refresh(self) -> Optional[Any]:
        """Force-refresh GlobalDataAI and return snapshot for downstream use."""
        log.info("[MondayPreparation] Task 1+2 — Global market context refresh")
        try:
            snapshot = self._orch.global_intelligence.data_ai.fetch(force=True)
            if snapshot:
                bias  = getattr(snapshot, "bias", "unknown")
                score = getattr(snapshot, "sentiment_score", 0.0)
                log.info(
                    "[MondayPreparation] Global snapshot: bias=%s  sentiment_score=%.2f",
                    bias, score,
                )
                # Log any notable global signals available on the snapshot
                _fields = ["sp500_change", "nikkei_change", "dxy_level",
                           "crude_price", "usdinr", "vix_global"]
                for field in _fields:
                    val = getattr(snapshot, field, None)
                    if val is not None:
                        log.info("[MondayPreparation]   %s = %s", field, val)
            return snapshot
        except Exception as exc:
            log.warning("[MondayPreparation] Global refresh failed: %s", exc)
            return None

    def _sunday_monday_ranking(self) -> None:
        """Read candidate store and rank top candidates for Monday focus."""
        log.info("[MondayPreparation] Task 3 — Monday candidate ranking")
        try:
            from opportunity_engine.candidate_store import CandidateStore
            candidates = CandidateStore.read()
            if not candidates:
                log.info("[MondayPreparation] No valid candidates for Monday ranking — "
                         "will rely on Saturday rescan or static watchlist.")
                return

            sorted_cands = sorted(
                candidates,
                key=lambda c: float(c.get("score", 0.0)),
                reverse=True,
            )
            top_n = sorted_cands[:15]
            log.info("[MondayPreparation] Top 15 Monday candidates (pre-market review):")
            for i, c in enumerate(top_n, 1):
                log.info(
                    "[MondayPreparation]   %2d. %-18s  score=%.2f  sector=%-20s  "
                    "resist=%.2f  support=%.2f  rsi=%.1f",
                    i,
                    c.get("symbol", "?"),
                    float(c.get("score", 0.0)),
                    c.get("sector", "?"),
                    float(c.get("resistance", 0.0)),
                    float(c.get("support", 0.0)),
                    float(c.get("rsi", 0.0)),
                )

        except Exception as exc:
            log.warning("[MondayPreparation] Monday ranking failed: %s", exc)

    def _sunday_regime_bias(
        self,
        market_data: Dict[str, Any],
        global_snapshot: Optional[Any],
    ) -> None:
        """Classify weekend regime for Monday bias preparation."""
        log.info("[MondayPreparation] Task 4 — Regime-bias preparation")
        try:
            global_bias  = "neutral"
            global_score = 0.0
            if global_snapshot:
                global_bias  = str(getattr(global_snapshot, "bias", "neutral"))
                global_score = float(getattr(global_snapshot, "sentiment_score", 0.0))

            result = self._orch.market_regime_ai.classify(
                market_data,
                global_bias=global_bias,
                global_sentiment_score=global_score,
            )
            regime = str(result.data.get("regime", "unknown")) if result.data else "unknown"
            vol    = str(result.data.get("volatility", "unknown")) if result.data else "unknown"
            vix    = result.data.get("vix", 0.0) if result.data else 0.0
            log.info(
                "[MondayPreparation] Monday regime bias: regime=%s  volatility=%s  "
                "vix=%.1f  global_bias=%s",
                regime, vol, vix, global_bias,
            )
        except Exception as exc:
            log.warning("[MondayPreparation] Regime-bias preparation failed: %s", exc)

    def _sunday_sector_priority(self, market_data: Dict[str, Any]) -> None:
        """Run sector rotation for Monday sector prioritization."""
        log.info("[MondayPreparation] Task 5 — Sector prioritization")
        try:
            result = self._orch.sector_rotation_ai.analyse(market_data)
            leaders  = (result.data or {}).get("leaders",  [])
            laggards = (result.data or {}).get("laggards", [])
            log.info("[MondayPreparation] %s", result.summary)
            if leaders:
                log.info("[MondayPreparation] Priority sectors Monday: %s",
                         ", ".join(str(s) for s in leaders[:5]))
            if laggards:
                log.info("[MondayPreparation] Avoid / underweight sectors: %s",
                         ", ".join(str(s) for s in laggards[:5]))
        except Exception as exc:
            log.warning("[MondayPreparation] Sector prioritization failed: %s", exc)

    def _sunday_concentration_check(self) -> None:
        """Check sector concentration risk in prepared candidate universe."""
        log.info("[MondayPreparation] Task 6 — Risk concentration check")
        try:
            from opportunity_engine.candidate_store import CandidateStore
            import config as cfg
            candidates = CandidateStore.read()
            if not candidates:
                log.info("[MondayPreparation] No candidates for concentration check.")
                return

            sector_counts = Counter(c.get("sector", "UNKNOWN") for c in candidates)
            total = len(candidates)
            log.info("[MondayPreparation] Sector concentration (%d candidates):", total)
            warned = False
            for sector, count in sector_counts.most_common(10):
                pct = count / total * 100
                flag = " ⚠️  CONCENTRATED" if pct > 30.0 else ""
                log.info(
                    "[MondayPreparation]   %-25s  %2d  (%.0f%%)%s",
                    sector, count, pct, flag,
                )
                if pct > 30.0:
                    warned = True

            if warned:
                log.warning(
                    "[MondayPreparation] High sector concentration detected. "
                    "Observational only — governance review recommended before "
                    "increasing EXPLORATION_BUDGET_PCT further.",
                )
        except Exception as exc:
            log.warning("[MondayPreparation] Concentration check failed: %s", exc)

    def _sunday_exploration_focus(self) -> None:
        """Log which sectors have most exploration activity for Monday focus."""
        log.info("[MondayPreparation] Task 7 — Exploration focus planning")
        try:
            from opportunity_engine.candidate_store import CandidateStore
            import config as cfg

            candidates = CandidateStore.read()
            if not candidates:
                return

            # Exploration candidates are those NOT already in the prepared core.
            # We identify them as lower-score candidates not appearing in the top tier.
            sorted_cands  = sorted(candidates, key=lambda c: float(c.get("score", 0.0)), reverse=True)
            prepared_core = set(c.get("symbol") for c in sorted_cands[:30])
            explore_cands = [c for c in candidates if c.get("symbol") not in prepared_core]

            if explore_cands:
                e_sectors = Counter(c.get("sector", "UNKNOWN") for c in explore_cands)
                budget_pct = getattr(cfg, "EXPLORATION_BUDGET_PCT", 20)
                log.info(
                    "[ExplorationReview] Exploration focus (budget=%d%%)  "
                    "exploration_pool=%d  sector spread:",
                    budget_pct, len(explore_cands),
                )
                for sector, count in e_sectors.most_common(5):
                    log.info("[ExplorationReview]   %-25s  %d opportunities", sector, count)
            else:
                log.info("[ExplorationReview] Exploration pool empty — all candidates in prepared core.")

        except Exception as exc:
            log.warning("[MondayPreparation] Exploration focus planning failed: %s", exc)

    def _sunday_readiness_summary(self, global_snapshot: Optional[Any]) -> None:
        """Log + Telegram premarket readiness summary."""
        log.info("[MondayPreparation] Task 8 — Premarket readiness summary")
        try:
            from opportunity_engine.candidate_store import CandidateStore
            candidates = CandidateStore.read()
            cand_count = len(candidates) if candidates else 0
            is_fresh   = CandidateStore.is_fresh()

            import config as cfg
            _mode = "🧪 Paper" if getattr(cfg, "PAPER_TRADING", False) else "💵 Live"
            budget_pct = getattr(cfg, "EXPLORATION_BUDGET_PCT", 20)
            threshold  = getattr(cfg, "EXPLORATION_THRESHOLD", 7.2)

            log.info(
                "[MondayPreparation] READINESS: mode=%s  candidates=%d  "
                "store_fresh=%s  exploration_budget=%d%%  threshold=%.1f",
                _mode, cand_count, is_fresh, budget_pct, threshold,
            )

            try:
                from notifications import get_notifier
                global_bias  = str(getattr(global_snapshot, "bias", "N/A")) \
                    if global_snapshot else "N/A"
                global_score = float(getattr(global_snapshot, "sentiment_score", 0.0)) \
                    if global_snapshot else 0.0

                notifier = get_notifier()
                notifier.market_alert(
                    "📅 Monday Preparation Complete",
                    f"Mode: {_mode}\n"
                    f"Prepared candidates: {cand_count}  (store fresh: {is_fresh})\n"
                    f"Global bias: {global_bias}  (score: {global_score:+.2f})\n"
                    f"Exploration budget: {budget_pct}%  threshold: {threshold}\n"
                    f"Pre-market init: 08:00  |  First cycle: 09:45\n"
                    f"Intelligence accumulation complete — ready for Monday open.",
                )
            except Exception as _te:
                log.debug("[MondayPreparation] Telegram readiness notification failed: %s", _te)

        except Exception as exc:
            log.warning("[MondayPreparation] Readiness summary failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # SHARED HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _fetch_market_data(self) -> Optional[Dict[str, Any]]:
        """
        Fetch market data for regime / sector analysis.
        On weekends markets are closed; yfinance still returns the last
        available price bar (Friday close), which is sufficient for
        weekend regime snapshots.
        """
        try:
            data = self._orch.market_data_ai.fetch()
            return data
        except Exception as exc:
            log.warning("[WeekendResearch] MarketDataAI.fetch() failed: %s", exc)
            return None
