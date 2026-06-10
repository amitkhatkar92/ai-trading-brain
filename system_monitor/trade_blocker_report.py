"""
TradeDiagnosticEngine — Cycle-level self-diagnosis
====================================================
Answers "Why did I not take a trade today/this cycle?" without
requiring manual forensic investigation of individual log tags.

Each pipeline stage calls record_stage() after completing its gate.
At cycle end, generate() synthesises a single plain-English explanation.

Emits:
  [BlockerReport]           — per stage with signal attrition
  [TradeDiagnostic]         — plain-English root-cause sentence
  [TradeDiagnosticSummary]  — structured grep-friendly summary

Design constraints:
  • Observability only — zero impact on strategy, thresholds, or pipeline flow
  • Additive — no existing code is modified by this module itself
  • Single-cycle lifetime — create one instance per run_full_cycle()
"""
from __future__ import annotations
from dataclasses import dataclass
from utils import get_logger

log = get_logger(__name__)

# Default recommended actions per stage (overridable per record_stage() call)
_DEFAULT_ACTION: dict[str, str] = {
    "OpportunityEngine":   "Market conditions not met — check regime/VIX/liquidity/IV.",
    "StrategyLab":         "Strategies DISABLED or backtest gate failing. "
                           "Use /status to see which strategies are warming up.",
    "CapitalRiskEngine":   "Budget allocation issue — check CRE budget ratios.",
    "RiskControl":         "R:R below threshold or portfolio heat limit reached. "
                           "Check open positions consuming heat budget.",
    "OptionsQualityGate":  "Options blocked at C1–C6. Most common: C1 live-data "
                           "check or C2 confidence threshold. Check [OptionsDecisionTrace].",
    "MarketSimulation":    "Stability gate too strict for current volatility regime.",
    "RiskGuardian":        "Kill-switch or daily loss limit triggered. Check VIX and P&L.",
    "CorrelationEngine":   "Sector concentration too high — too many signals in same sector.",
    "SmartExecution":      "Position sizing or capital constraints filtered signals.",
    "DebateAndDecision":   "All signals scored below decision threshold (6.5). "
                           "Review confidence calibration.",
}


@dataclass
class _StageReport:
    stage: str
    health: str           # "OK" | "WARN" | "BLOCKED"
    coverage: str         # e.g. "2/28"
    primary_blocker: str  # e.g. "STRATEGY_DISABLED"
    impact_count: int     # signals dropped at this stage
    recommended_action: str


class TradeDiagnosticEngine:
    """
    Lifecycle: create one instance per ``run_full_cycle()``.
    Call ``record_stage()`` at each pipeline gate boundary.
    Call ``generate()`` once at cycle end.
    """

    def __init__(self) -> None:
        self._stages: list[_StageReport] = []
        self._total_generated: int = 0
        self._total_executed: int = 0
        self._options_in: int = 0
        self._options_placed: int = 0

    # ── Public API ─────────────────────────────────────────────────────────

    def record_stage(
        self,
        stage: str,
        signals_in: int,
        signals_out: int,
        primary_blocker: str = "",
        recommended_action: str = "",
    ) -> None:
        """
        Record the outcome of one pipeline gate.

        :param stage:              Gate name, e.g. "StrategyLab"
        :param signals_in:         Signal count entering this gate
        :param signals_out:        Signal count surviving this gate
        :param primary_blocker:    Short label for the dominant rejection reason
        :param recommended_action: Override the default action hint
        """
        dropped = signals_in - signals_out

        if signals_in == 0:
            health, coverage = "OK", "N/A"
        elif signals_out == 0 and signals_in > 0:
            health, coverage = "BLOCKED", f"0/{signals_in}"
        elif dropped > 0:
            health, coverage = "WARN", f"{signals_out}/{signals_in}"
        else:
            health, coverage = "OK", f"{signals_out}/{signals_in}"

        blocker = primary_blocker if primary_blocker else ("none" if dropped == 0 else "unknown")
        action  = recommended_action or _DEFAULT_ACTION.get(stage, "Investigate logs.")

        report = _StageReport(
            stage=stage,
            health=health,
            coverage=coverage,
            primary_blocker=blocker,
            impact_count=dropped,
            recommended_action=action,
        )
        self._stages.append(report)

        if dropped > 0:
            log.info(
                "[BlockerReport] stage=%-24s health=%-7s coverage=%-7s "
                "dropped=%-3d blocker=%s | action=%s",
                stage, health, coverage, dropped, blocker, action,
            )

    def set_totals(
        self,
        generated: int,
        executed: int,
        options_in: int = 0,
        options_fast_path_passed: int = 0,
    ) -> None:
        """Set cycle-level totals before calling generate()."""
        self._total_generated = generated
        self._total_executed  = executed
        self._options_in      = options_in
        self._options_placed  = options_fast_path_passed

    def generate(self) -> None:
        """
        Emit the synthesised "Why no trade?" explanation.
        Emits [TradeDiagnostic] and [TradeDiagnosticSummary] log lines.
        """
        executed  = self._total_executed
        generated = self._total_generated

        if executed > 0:
            log.info(
                "[TradeDiagnostic] %d trade(s) executed — pipeline healthy.",
                executed,
            )
            return

        if generated == 0:
            log.info(
                "[TradeDiagnostic] No trades. Root cause: OpportunityEngine emitted 0 "
                "signals — market conditions did not meet any strategy entry criteria "
                "(regime / VIX / IV / liquidity filter)."
            )
            log.info(
                "[TradeDiagnosticSummary] executed=0 generated=0 "
                "dominant_stage=OpportunityEngine "
                "dominant_blocker=NO_SIGNALS_GENERATED "
                "options_in=0 options_placed=0"
            )
            return

        blockers = [r for r in self._stages if r.impact_count > 0]
        if not blockers:
            log.info(
                "[TradeDiagnostic] No trades. %d signal(s) generated → 0 executed. "
                "Attrition stage undetermined — all stages reported 0 drops "
                "(check [SignalLifecycle] for the actual funnel).",
                generated,
            )
            return

        dominant    = max(blockers, key=lambda r: r.impact_count)
        secondaries = [r for r in blockers if r is not dominant]

        parts = [
            f"No trades this cycle. {generated} signal(s) generated → 0 executed.",
            f"Dominant blocker: [{dominant.stage}] {dominant.primary_blocker} "
            f"(dropped {dominant.impact_count}, coverage {dominant.coverage}).",
            f"Action: {dominant.recommended_action}",
        ]
        for r in secondaries:
            parts.append(
                f"Also: [{r.stage}] {r.primary_blocker} "
                f"dropped {r.impact_count} signal(s).",
            )
        if self._options_in > 0:
            opts_status = (
                f"{self._options_placed} reached execution"
                if self._options_placed > 0 else "0 reached execution"
            )
            parts.append(
                f"Options path: {self._options_in} signal(s) entered fast-path, "
                f"{opts_status}.",
            )

        log.info("[TradeDiagnostic] %s", " | ".join(parts))
        log.info(
            "[TradeDiagnosticSummary] executed=0 generated=%d "
            "dominant_stage=%s dominant_blocker=%s "
            "secondary_stages=%d options_in=%d options_placed=%d",
            generated,
            dominant.stage,
            dominant.primary_blocker.replace(" ", "_")[:60],
            len(secondaries),
            self._options_in,
            self._options_placed,
        )
