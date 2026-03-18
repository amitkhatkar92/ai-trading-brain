"""
Global Intelligence Layer — Market Distortion Scanner
======================================================
Runs before every trading cycle to detect macro distortions and
hidden market stress. Its DistortionResult gates strategy selection,
position sizing, and trade execution in the orchestrator.

Two-layer detection
-------------------
Layer 1 — Event Scanner (announced shocks)
  • Central bank meeting day  (Fed / RBI / ECB / BOJ today or tomorrow)
  • Energy shock              (crude oil > ±3 %)
  • Bond yield spike          (US 10Y move > 15 bps)
  • Equity panic              (S&P 500 futures < −1.5 %)
  • Safe-haven surge          (Gold > +1.5 % AND VIX rising)
  • Currency stress           (DXY > +0.8 % OR USD/INR > +0.4 %)
  • War / geopolitical flag   (manual toggle or extreme multi-signal)

Layer 2 — Hidden Market Stress Detector (HMSD)
  Quantifies hidden stress BEFORE headlines appear by scoring
  observable market signals.

  Indicator              Condition         Points
  ─────────────────────  ────────────────  ──────
  VIX level              > 20              +2
  VIX level              > 30              +1  (bonus; max 3 for VIX)
  S&P 500 futures        < −1.0 %          +2
  Gold move              > +1.0 %          +1
  Crude Brent move       > +3.0 %          +1
  US 10Y yield change    > +15 bps         +2
  DXY move               > +0.8 %          +1   ← safe-haven USD surge
  Maximum total                             10  (capped at 8 in scoring)

  Score  Risk Level   Behavior
  ─────  ──────────   ────────────────────────────────────────────
  0–2    NORMAL       Full trading, normal position sizes
  3–4    CAUTION      Position size halved, skip aggressive strategies
  5–6    HIGH         Position size ×0.25, hedge / defensive only
  7–8    EXTREME      No new trades — monitor only

Output: DistortionResult
  flags              : dict of individual bool signals
  stress_score       : int  0–8
  risk_level         : str  "NORMAL" | "CAUTION" | "HIGH" | "EXTREME"
  behavior_overrides : BehaviorOverrides
  sector_watches     : dict {sector: "watch" | "avoid"}
  report()           : human-readable dashboard string
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List

from utils import get_logger
from .global_data_ai  import GlobalSnapshot
from .macro_signal_ai import MacroSignals

log = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CENTRAL BANK CALENDAR  (extend quarterly)
# ─────────────────────────────────────────────────────────────────────────────
# Format: "YYYY-MM-DD" : institution
CENTRAL_BANK_DATES: Dict[str, str] = {
    # ── US Fed FOMC ──────────────────────────────────────────────────
    "2026-01-28": "US Fed FOMC",
    "2026-01-29": "US Fed FOMC",
    "2026-03-18": "US Fed FOMC",
    "2026-03-19": "US Fed FOMC",
    "2026-05-06": "US Fed FOMC",
    "2026-05-07": "US Fed FOMC",
    "2026-06-17": "US Fed FOMC",
    "2026-06-18": "US Fed FOMC",
    "2026-07-29": "US Fed FOMC",
    "2026-07-30": "US Fed FOMC",
    "2026-09-16": "US Fed FOMC",
    "2026-09-17": "US Fed FOMC",
    "2026-11-04": "US Fed FOMC",
    "2026-11-05": "US Fed FOMC",
    "2026-12-09": "US Fed FOMC",
    "2026-12-10": "US Fed FOMC",
    # ── RBI MPC ──────────────────────────────────────────────────────
    "2026-02-05": "RBI MPC",
    "2026-02-06": "RBI MPC",
    "2026-02-07": "RBI MPC",
    "2026-04-07": "RBI MPC",
    "2026-04-08": "RBI MPC",
    "2026-04-09": "RBI MPC",
    "2026-06-04": "RBI MPC",
    "2026-06-05": "RBI MPC",
    "2026-06-06": "RBI MPC",
    "2026-08-05": "RBI MPC",
    "2026-08-06": "RBI MPC",
    "2026-08-07": "RBI MPC",
    "2026-10-06": "RBI MPC",
    "2026-10-07": "RBI MPC",
    "2026-10-08": "RBI MPC",
    "2026-12-03": "RBI MPC",
    "2026-12-04": "RBI MPC",
    "2026-12-05": "RBI MPC",
    # ── ECB ──────────────────────────────────────────────────────────
    "2026-01-30": "ECB Rate Decision",
    "2026-03-05": "ECB Rate Decision",
    "2026-04-16": "ECB Rate Decision",
    "2026-06-04": "ECB Rate Decision",
    "2026-07-23": "ECB Rate Decision",
    "2026-09-10": "ECB Rate Decision",
    "2026-10-22": "ECB Rate Decision",
    "2026-12-10": "ECB Rate Decision",
    # ── US CPI / jobs ────────────────────────────────────────────────
    "2026-03-11": "US CPI Release",
    "2026-04-14": "US CPI Release",
    "2026-05-13": "US CPI Release",
    "2026-03-06": "US NFP",
    "2026-04-03": "US NFP",
    "2026-05-01": "US NFP",
}

# ─────────────────────────────────────────────────────────────────────────────
# SCORE THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────
SCORE_CAUTION = 3
SCORE_HIGH    = 5
SCORE_EXTREME = 7

# ─────────────────────────────────────────────────────────────────────────────
# RESULT DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BehaviorOverrides:
    """
    Concrete behavior constraints that the orchestrator enforces on every
    trade cycle when distortion / stress is detected.
    """
    trading_allowed:         bool  = True
    position_size_multiplier: float = 1.0    # scales TradeSignal.quantity
    max_new_trades:          int   = 10      # cap for the cycle
    breakout_allowed:        bool  = True
    aggressive_allowed:      bool  = True    # momentum, high-beta
    hedge_preferred:         bool  = False   # options hedges preferred
    reason:                  str   = ""

    def summary(self) -> str:
        return (
            f"Trading={'✅' if self.trading_allowed else '🚫'}  "
            f"SizeMultiplier={self.position_size_multiplier:.0%}  "
            f"MaxTrades={self.max_new_trades}  "
            f"Breakout={'on' if self.breakout_allowed else 'off'}  "
            f"Reason={self.reason}"
        )


@dataclass
class DistortionResult:
    """
    Output of the Market Distortion Scanner — consumed by the orchestrator
    before every trading cycle to enforce risk-appropriate behavior.
    """
    timestamp: datetime = field(default_factory=datetime.now)

    # ── Layer 1: Binary distortion flags ─────────────────────────────
    energy_shock:       bool = False     # crude > ±3 %
    central_bank_event: bool = False     # Fed / RBI / ECB today or tomorrow
    bond_yield_spike:   bool = False     # US 10Y > +15 bps
    equity_panic:       bool = False     # S&P futures < −1.5 %
    safe_haven_surge:   bool = False     # gold > +1.5 % AND VIX rising
    currency_stress:    bool = False     # DXY spike OR INR weakness
    war_escalation:     bool = False     # manual flag or multi-trigger extreme

    # Metadata from calendar
    central_bank_name:  str  = ""        # e.g. "US Fed FOMC"

    # ── Layer 2: Hidden Stress Detector ──────────────────────────────
    stress_score: int = 0                # 0–8  (higher = worse)

    # ── Composite risk level ──────────────────────────────────────────
    risk_level: str = "NORMAL"           # NORMAL | CAUTION | HIGH | EXTREME

    # ── Behavior instructions for orchestrator ────────────────────────
    behavior_overrides: BehaviorOverrides = field(
        default_factory=BehaviorOverrides)

    # ── Sector guidance ───────────────────────────────────────────────
    sector_watches: Dict[str, str] = field(default_factory=dict)
    # e.g. {"Airlines": "avoid", "Oil & Gas": "watch"}

    @property
    def flags(self) -> Dict[str, bool]:
        return {
            "energy_shock":       self.energy_shock,
            "central_bank_event": self.central_bank_event,
            "bond_yield_spike":   self.bond_yield_spike,
            "equity_panic":       self.equity_panic,
            "safe_haven_surge":   self.safe_haven_surge,
            "currency_stress":    self.currency_stress,
            "war_escalation":     self.war_escalation,
        }

    @property
    def any_distortion(self) -> bool:
        return any(self.flags.values())

    @property
    def active_flags(self) -> List[str]:
        return [k for k, v in self.flags.items() if v]

    def report(self) -> str:
        """Human-readable dashboard string."""
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║          GLOBAL MARKET DISTORTION REPORT                 ║",
            f"║  {self.timestamp.strftime('%Y-%m-%d  %H:%M:%S')}                              ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Hidden Stress Score : {self.stress_score}/8"
            f"{'  (' + self.central_bank_name + ')' if self.central_bank_name else ''}",
            f"║  Risk Level          : {self.risk_level}",
            "╠──────────────────────────────────────────────────────────╣",
            "║  DISTORTION FLAGS",
        ]
        for name, val in self.flags.items():
            icon  = "⚠️ TRUE " if val else "   false"
            label = name.replace("_", " ").title()
            lines.append(f"║    {icon}  {label}")
        if self.sector_watches:
            lines.append("╠──────────────────────────────────────────────────────────╣")
            lines.append("║  SECTOR GUIDANCE")
            for sector, action in self.sector_watches.items():
                lines.append(f"║    [{action.upper():>5}]  {sector}")
        lines.append("╠──────────────────────────────────────────────────────────╣")
        lines.append(f"║  ACTION: {self.behavior_overrides.reason}")
        lines.append(f"║  {self.behavior_overrides.summary()}")
        lines.append("╚══════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# SCANNER
# ─────────────────────────────────────────────────────────────────────────────

class MarketDistortionScanner:
    """
    Global Market Distortion Scanner.

    Runs before every trading cycle inside GlobalIntelligenceEngine.run().
    Produces a DistortionResult that the orchestrator uses to gate and
    scale every downstream step.

    Usage
    -----
    scanner = MarketDistortionScanner()
    result  = scanner.scan(snap, macro)      → DistortionResult
    print(result.report())
    """

    # ── Layer 1 thresholds ────────────────────────────────────────────
    OIL_SHOCK_PCT         = 3.0      # |crude_brent_change| > 3 %
    BOND_SPIKE_BPS        = 15.0     # us10y_change_bps > 15 bps
    EQUITY_PANIC_PCT      = -1.5     # sp500_change < -1.5 %
    SAFE_HAVEN_GOLD_PCT   = 1.5      # gold_change > 1.5 %
    DXY_STRESS_PCT        = 0.8      # dxy_change > 0.8 %
    INR_WEAK_PCT          = 0.4      # usdinr_change > 0.4 % (rupee weakens)

    # ── Layer 2 thresholds ────────────────────────────────────────────
    VIX_STRESS            = 20.0
    VIX_EXTREME           = 30.0
    SP500_STRESS_PCT      = -1.0
    GOLD_HMSD_PCT         = 1.0
    OIL_HMSD_PCT          = 3.0
    BOND_HMSD_BPS         = 15.0
    DXY_HMSD_PCT          = 0.8

    # War escalation: triggered automatically when ≥4 individual flags fire
    WAR_AUTO_THRESHOLD    = 4

    def __init__(self):
        log.info("[MarketDistortionScanner] Initialised. "
                 "Monitoring %d central bank calendar dates.", len(CENTRAL_BANK_DATES))

    # ── Public API ────────────────────────────────────────────────────

    def scan(self, snap: GlobalSnapshot, macro: MacroSignals) -> DistortionResult:
        """
        Run the full two-layer distortion scan.

        Parameters
        ----------
        snap  : GlobalSnapshot  — raw global market data
        macro : MacroSignals    — pre-computed macro interpretation

        Returns
        -------
        DistortionResult  — flags + stress score + behavior overrides
        """
        result = DistortionResult()

        # ── Layer 1: Binary distortion flags ─────────────────────────
        result.energy_shock       = self._detect_energy_shock(snap)
        result.central_bank_event, result.central_bank_name = \
            self._detect_central_bank_event()
        result.bond_yield_spike   = self._detect_bond_spike(snap)
        result.equity_panic       = self._detect_equity_panic(snap)
        result.safe_haven_surge   = self._detect_safe_haven_surge(snap)
        result.currency_stress    = self._detect_currency_stress(snap)

        # Auto-escalate to war/geopolitical flag if many signals fire
        active_count = sum(self.flags_as_list(result))
        result.war_escalation = active_count >= self.WAR_AUTO_THRESHOLD

        # ── Layer 2: Hidden Market Stress Score ───────────────────────
        result.stress_score = self._compute_stress_score(snap)

        # ── Composite risk level ──────────────────────────────────────
        result.risk_level = self._classify_risk(result.stress_score, result)

        # ── Sector guidance ───────────────────────────────────────────
        result.sector_watches = self._build_sector_guidance(snap, result)

        # ── Behavior overrides ────────────────────────────────────────
        result.behavior_overrides = self._build_behavior_overrides(result)

        # ── Logging ───────────────────────────────────────────────────
        if result.any_distortion or result.stress_score >= SCORE_CAUTION:
            log.warning(
                "[MarketDistortionScanner] 🚨 Risk=%s  Score=%d/8  "
                "Flags=%s",
                result.risk_level,
                result.stress_score,
                result.active_flags or "none",
            )
        else:
            log.info(
                "[MarketDistortionScanner] ✅ NORMAL  Score=%d/8  "
                "No distortions detected.",
                result.stress_score,
            )
        return result

    # ── Layer 1: Event detectors ──────────────────────────────────────

    def _detect_energy_shock(self, snap: GlobalSnapshot) -> bool:
        return abs(snap.crude_brent_change) >= self.OIL_SHOCK_PCT

    def _detect_central_bank_event(self):
        today     = date.today()
        today_str = today.isoformat()
        if today_str in CENTRAL_BANK_DATES:
            return True, CENTRAL_BANK_DATES[today_str]
        return False, ""

    def _detect_bond_spike(self, snap: GlobalSnapshot) -> bool:
        return snap.us10y_change_bps >= self.BOND_SPIKE_BPS

    def _detect_equity_panic(self, snap: GlobalSnapshot) -> bool:
        return snap.sp500_change <= self.EQUITY_PANIC_PCT

    def _detect_safe_haven_surge(self, snap: GlobalSnapshot) -> bool:
        return snap.gold_change >= self.SAFE_HAVEN_GOLD_PCT and snap.cboe_vix > 18.0

    def _detect_currency_stress(self, snap: GlobalSnapshot) -> bool:
        return (snap.dxy_change >= self.DXY_STRESS_PCT or
                snap.usdinr_change >= self.INR_WEAK_PCT)

    # ── Layer 2: Hidden Market Stress Detector ────────────────────────

    def _compute_stress_score(self, snap: GlobalSnapshot) -> int:
        score = 0

        # VIX (max 3 points)
        if snap.cboe_vix > self.VIX_EXTREME:
            score += 3
        elif snap.cboe_vix > self.VIX_STRESS:
            score += 2

        # S&P 500 futures drop
        if snap.sp500_change <= self.SP500_STRESS_PCT:
            score += 2

        # Gold surge (safe-haven buying)
        if snap.gold_change >= self.GOLD_HMSD_PCT:
            score += 1

        # Crude spike (inflation / supply shock)
        if snap.crude_brent_change >= self.OIL_HMSD_PCT:
            score += 1

        # Bond yield spike (liquidity stress)
        if snap.us10y_change_bps >= self.BOND_HMSD_BPS:
            score += 2

        # Safe-haven USD surge
        if snap.dxy_change >= self.DXY_HMSD_PCT:
            score += 1

        return min(score, 8)   # cap at 8

    # ── Risk level ────────────────────────────────────────────────────

    @staticmethod
    def _classify_risk(score: int, result: DistortionResult) -> str:
        # War escalation or equity panic always → at least HIGH
        if result.war_escalation or result.equity_panic:
            if score < SCORE_HIGH:
                score = SCORE_HIGH
        if score >= SCORE_EXTREME:
            return "EXTREME"
        if score >= SCORE_HIGH:
            return "HIGH"
        if score >= SCORE_CAUTION:
            return "CAUTION"
        return "NORMAL"

    # ── Sector guidance ───────────────────────────────────────────────

    @staticmethod
    def _build_sector_guidance(
        snap: GlobalSnapshot, result: DistortionResult
    ) -> Dict[str, str]:
        guidance: Dict[str, str] = {}
        if result.energy_shock:
            if snap.crude_brent_change > 0:
                guidance["Airlines"]    = "avoid"
                guidance["Paints"]      = "avoid"
                guidance["Auto"]        = "avoid"
                guidance["Oil & Gas"]   = "watch"
            else:
                guidance["Airlines"]    = "watch"
                guidance["Auto"]        = "watch"
                guidance["Oil & Gas"]   = "avoid"
        if result.bond_yield_spike:
            guidance["Banks"]           = "avoid"
            guidance["Realty"]          = "avoid"
            guidance["NBFCs"]           = "avoid"
        if result.safe_haven_surge:
            guidance["Gold ETF"]        = "watch"
            guidance["Pharma"]          = "watch"
            guidance["FMCG"]            = "watch"
            guidance["IT"]              = "avoid"
        if result.central_bank_event:
            guidance["Banking"]         = "watch"
            guidance["Rate Sensitives"] = "watch"
        return guidance

    # ── Behavior overrides ────────────────────────────────────────────

    @staticmethod
    def _build_behavior_overrides(result: DistortionResult) -> BehaviorOverrides:
        level = result.risk_level
        if level == "EXTREME":
            return BehaviorOverrides(
                trading_allowed=False,
                position_size_multiplier=0.0,
                max_new_trades=0,
                breakout_allowed=False,
                aggressive_allowed=False,
                hedge_preferred=True,
                reason="EXTREME stress — all new trades halted. Monitor only.",
            )
        if level == "HIGH":
            return BehaviorOverrides(
                trading_allowed=True,
                position_size_multiplier=0.25,
                max_new_trades=2,
                breakout_allowed=False,
                aggressive_allowed=False,
                hedge_preferred=True,
                reason="HIGH stress — defensive mode, 25% size, hedging preferred.",
            )
        if level == "CAUTION":
            return BehaviorOverrides(
                trading_allowed=True,
                position_size_multiplier=0.5,
                max_new_trades=5,
                breakout_allowed=True,
                aggressive_allowed=False,
                hedge_preferred=False,
                reason="CAUTION — 50% position size, no aggressive strategies.",
            )
        # NORMAL
        flags_on = result.active_flags
        reason   = "NORMAL — full trading active."
        if flags_on:
            reason = f"NORMAL (minor flags: {', '.join(flags_on)}) — standard rules."
        return BehaviorOverrides(
            trading_allowed=True,
            position_size_multiplier=1.0,
            max_new_trades=10,
            breakout_allowed=True,
            aggressive_allowed=True,
            hedge_preferred=False,
            reason=reason,
        )

    # ── Helper ────────────────────────────────────────────────────────

    @staticmethod
    def flags_as_list(result: DistortionResult) -> List[bool]:
        return [
            result.energy_shock,
            result.central_bank_event,
            result.bond_yield_spike,
            result.equity_panic,
            result.safe_haven_surge,
            result.currency_stress,
        ]
