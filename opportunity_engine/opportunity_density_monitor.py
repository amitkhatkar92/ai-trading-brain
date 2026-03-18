"""
Opportunity Density Monitor (ODM) — Layer 3 Control Layer
===========================================================
Monitors the ratio of approved trades to generated signals over a rolling
window.  When density falls below threshold tiers, ODM adjusts the scanning
behaviour of the Opportunity Engine for the next cycle — without ever
bypassing Risk Management or the Decision Engine.

Pipeline position::

    Opportunity Engine
        ↓
    ODM  ← you are here
        ↓
    Strategy Lab → Debate → Risk → Execution

Density tiers and actions
──────────────────────────
  > 5%   NORMAL    — standard operation  (vol_ratio ≥ 2.0, NIFTY100 universe)
  3-5%   MONITOR   — watch closely       (vol_ratio ≥ 1.8)
  1-3%   EXPAND    — widen search        (vol_ratio ≥ 1.6, extended universe)
  < 1%   SECONDARY — activate pullback   (vol_ratio ≥ 1.4, extended universe +
                                          Pullback_Trend strategy enabled)

Key principles
──────────────
  • ODM never forces trades — it only adjusts scanning scope.
  • Risk Management and Debate layers still filter every signal.
  • Directive is advisory; scanners may still produce zero signals.
  • State persists across restarts (data/odm_state.json).
"""

from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Deque, List, Optional, Tuple

from models.market_data import MarketSnapshot, RegimeLabel
from utils import get_logger

log = get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
ROLLING_WINDOW   = 10     # number of cycles in rolling density window
TIER_NORMAL_PCT  = 5.0    # >  5% → NORMAL
TIER_MONITOR_PCT = 3.0    # 3–5% → MONITOR
TIER_EXPAND_PCT  = 1.0    # 1–3% → EXPAND
                          # <  1% → SECONDARY

ODM_STATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "odm_state.json"
)


@dataclass
class ODMDirective:
    """
    Instructions produced by ODM for the Opportunity Engine to consume.

    Fields
    ------
    tier              — density classification string
    density_pct       — rolling density % (approved / signals × 100)
    volume_ratio_min  — minimum volume_ratio for setup 1 (Breakout_Volume)
    extra_strategies  — extra strategy names to inject into MSC active set
    expand_universe   — when True, scanner also iterates extended watchlist
    message           — human-readable explanation for logs/Telegram
    """
    tier:             str
    density_pct:      float
    volume_ratio_min: float
    extra_strategies: List[str]
    expand_universe:  bool
    message:          str


# ── Default directive (returned when no history yet) ──────────────────────────
_DIRECTIVE_NORMAL = ODMDirective(
    tier             = "NORMAL",
    density_pct      = 100.0,
    volume_ratio_min = 2.0,
    extra_strategies = [],
    expand_universe  = False,
    message          = "Opportunity density normal — standard scanning.",
)


class OpportunityDensityMonitor:
    """
    Tracks rolling scan density and emits scan directives.

    Usage::
        odm = OpportunityDensityMonitor()

        # Before each scan:
        directive = odm.get_directive(snapshot)

        # After each cycle completes:
        odm.record_cycle(signals_generated=23, approved_trades=2)

        # For Telegram / dashboard:
        print(odm.get_status())
    """

    def __init__(self) -> None:
        # Each entry: (signals_generated, trades_approved)
        self._history: Deque[Tuple[int, int]] = deque(maxlen=ROLLING_WINDOW)
        self._current_tier: str = "NORMAL"
        self._load_state()
        log.info("[ODM] Initialised. Window=%d | tiers: NORMAL>%.0f%% | "
                 "MONITOR>%.0f%% | EXPAND>%.0f%% | SECONDARY≤%.0f%%",
                 ROLLING_WINDOW,
                 TIER_NORMAL_PCT, TIER_MONITOR_PCT, TIER_EXPAND_PCT,
                 TIER_EXPAND_PCT)

    # ── Public API ────────────────────────────────────────────────────────────

    def record_cycle(self, signals_generated: int, approved_trades: int) -> None:
        """
        Record the outcome of a completed scan cycle.
        Call this AFTER the full pipeline has run so we count actual executions.
        """
        self._history.append((signals_generated, approved_trades))
        density = self._rolling_density()
        tier    = self._classify(density)
        self._current_tier = tier

        log.info("[ODM] Cycle recorded: signals=%d  approved=%d  "
                 "rolling_density=%.1f%%  tier=%s",
                 signals_generated, approved_trades, density, tier)
        self._save_state()

    def get_directive(self, snapshot: Optional[MarketSnapshot] = None) -> ODMDirective:
        """
        Return the scanning directive for the NEXT cycle, based on
        rolling density and current market regime.
        """
        if len(self._history) == 0:
            return _DIRECTIVE_NORMAL

        density = self._rolling_density()
        tier    = self._classify(density)

        # In bear market: never expand strategies to avoid false breakouts
        if snapshot and snapshot.regime == RegimeLabel.BEAR_MARKET:
            if tier in ("EXPAND", "SECONDARY"):
                log.info("[ODM] Override: BEAR_MARKET — capping at MONITOR tier.")
                tier = "MONITOR"

        return self._build_directive(tier, density, snapshot)

    def get_status(self) -> dict:
        """Snapshot of current ODM state — for dashboard / Telegram."""
        density = self._rolling_density()
        total_s  = sum(s for s, _ in self._history)
        total_a  = sum(a for _, a in self._history)
        return {
            "tier":             self._current_tier,
            "density_pct":      round(density, 2),
            "rolling_window":   ROLLING_WINDOW,
            "cycles_recorded":  len(self._history),
            "total_signals":    total_s,
            "total_approved":   total_a,
            "last_updated":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def format_report(self) -> str:
        """Human-readable ODM report for logs / Telegram."""
        s   = self.get_status()
        bar = self._density_bar(s["density_pct"])
        tier_icon = {
            "NORMAL":    "✅",
            "MONITOR":   "👁️",
            "EXPAND":    "🔍",
            "SECONDARY": "⚡",
        }.get(s["tier"], "❓")
        directive = self.get_directive()
        lines = [
            "═" * 56,
            "  OPPORTUNITY DENSITY MONITOR",
            "═" * 56,
            f"  Tier         : {tier_icon} {s['tier']}",
            f"  Density      : {bar}  {s['density_pct']:.1f}%",
            f"  Window       : last {s['cycles_recorded']}/{ROLLING_WINDOW} cycles",
            f"  Signals      : {s['total_signals']}  →  Approved: {s['total_approved']}",
            "─" * 56,
            "  Active Directive:",
            f"    vol_ratio_min    = {directive.volume_ratio_min}",
            f"    expand_universe  = {directive.expand_universe}",
            f"    extra_strategies = {directive.extra_strategies or 'none'}",
            f"    {directive.message}",
            "═" * 56,
        ]
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _rolling_density(self) -> float:
        if not self._history:
            return 100.0
        total_signals  = sum(s for s, _ in self._history)
        total_approved = sum(a for _, a in self._history)
        if total_signals == 0:
            return 100.0
        return round(total_approved / total_signals * 100.0, 2)

    @staticmethod
    def _classify(density: float) -> str:
        if density > TIER_NORMAL_PCT:
            return "NORMAL"
        elif density > TIER_MONITOR_PCT:
            return "MONITOR"
        elif density > TIER_EXPAND_PCT:
            return "EXPAND"
        else:
            return "SECONDARY"

    @staticmethod
    def _build_directive(tier: str, density: float,
                         snapshot: Optional[MarketSnapshot]) -> ODMDirective:
        regime_label = (snapshot.regime.value if snapshot else "unknown")

        if tier == "NORMAL":
            return ODMDirective(
                tier             = "NORMAL",
                density_pct      = density,
                volume_ratio_min = 2.0,
                extra_strategies = [],
                expand_universe  = False,
                message          = f"Density {density:.1f}% — standard scanning.",
            )

        if tier == "MONITOR":
            return ODMDirective(
                tier             = "MONITOR",
                density_pct      = density,
                volume_ratio_min = 1.8,
                extra_strategies = [],
                expand_universe  = False,
                message          = (f"Density {density:.1f}% in {regime_label} — "
                                    "monitoring, volume threshold relaxed to 1.8×."),
            )

        if tier == "EXPAND":
            return ODMDirective(
                tier             = "EXPAND",
                density_pct      = density,
                volume_ratio_min = 1.6,
                extra_strategies = [],
                expand_universe  = True,
                message          = (f"Density {density:.1f}% — expanding universe "
                                    "and lowering volume threshold to 1.6×."),
            )

        # SECONDARY
        extra = ["Pullback_Trend"]
        # Add continuation strategy in bull trend
        if snapshot and snapshot.regime == RegimeLabel.BULL_TREND:
            extra.append("Continuation_Pullback")
        return ODMDirective(
            tier             = "SECONDARY",
            density_pct      = density,
            volume_ratio_min = 1.4,
            extra_strategies = extra,
            expand_universe  = True,
            message          = (f"Density {density:.1f}% critically low — "
                                f"extended universe + secondary strategies: "
                                f"{extra}"),
        )

    @staticmethod
    def _density_bar(density: float, width: int = 20) -> str:
        filled = min(width, int(density / 5.0))
        return "[" + "█" * filled + "░" * (width - filled) + "]"

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        try:
            os.makedirs(os.path.dirname(ODM_STATE_PATH), exist_ok=True)
            state = {
                "history":      list(self._history),
                "current_tier": self._current_tier,
                "saved_at":     datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            with open(ODM_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            log.warning("[ODM] Could not save state: %s", exc)

    def _load_state(self) -> None:
        if not os.path.exists(ODM_STATE_PATH):
            return
        try:
            with open(ODM_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            for entry in state.get("history", []):
                if isinstance(entry, list) and len(entry) == 2:
                    self._history.append((int(entry[0]), int(entry[1])))
            self._current_tier = state.get("current_tier", "NORMAL")
            log.info("[ODM] State restored: %d cycles loaded, tier=%s",
                     len(self._history), self._current_tier)
        except Exception as exc:
            log.warning("[ODM] Could not load state: %s", exc)
