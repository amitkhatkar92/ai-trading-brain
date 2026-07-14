"""iios/investment/decision/reasoning/signal_interpreter.py
SignalInterpreter — overrides NEUTRAL signal directions with rule-based interpretations.
Rules are pluggable via a dict injection.  Unknown keys remain NEUTRAL.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import (
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step

# ---------------------------------------------------------------------------
# Default rule set
# Rule: (key) → Callable[[value], (SignalDirection, interpretation_str)]
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rsi_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "RSI value non-numeric."
    if f > 70:
        return SignalDirection.NEGATIVE, f"RSI={f:.1f} in overbought zone (>70)."
    if f < 30:
        return SignalDirection.POSITIVE, f"RSI={f:.1f} in oversold zone (<30)."
    return SignalDirection.NEUTRAL, f"RSI={f:.1f} in neutral zone (30–70)."


def _win_rate_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "Win rate non-numeric."
    pct = f * 100 if f <= 1.0 else f
    if pct > 55:
        return SignalDirection.POSITIVE, f"Win rate {pct:.1f}% above 55% threshold."
    if pct < 40:
        return SignalDirection.NEGATIVE, f"Win rate {pct:.1f}% below 40% threshold."
    return SignalDirection.NEUTRAL, f"Win rate {pct:.1f}% in neutral range (40–55%)."


def _risk_score_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "Risk score non-numeric."
    if f > 70:
        return SignalDirection.NEGATIVE, f"Risk score {f:.0f} elevated (>70)."
    if f < 30:
        return SignalDirection.POSITIVE, f"Risk score {f:.0f} low (<30)."
    return SignalDirection.NEUTRAL, f"Risk score {f:.0f} moderate (30–70)."


def _signal_strength_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "Signal strength non-numeric."
    if f > 70:
        return SignalDirection.POSITIVE, f"Signal strength {f:.1f} strong (>70)."
    if f < 30:
        return SignalDirection.NEGATIVE, f"Signal strength {f:.1f} weak (<30)."
    return SignalDirection.NEUTRAL, f"Signal strength {f:.1f} moderate (30–70)."


def _sharpe_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "Sharpe ratio non-numeric."
    if f >= 1.0:
        return SignalDirection.POSITIVE, f"Sharpe ratio {f:.2f} ≥1.0 (risk-adjusted returns attractive)."
    if f < 0.5:
        return SignalDirection.NEGATIVE, f"Sharpe ratio {f:.2f} <0.5 (poor risk-adjusted returns)."
    return SignalDirection.NEUTRAL, f"Sharpe ratio {f:.2f} in borderline range (0.5–1.0)."


def _pe_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "P/E ratio non-numeric."
    if f > 45:
        return SignalDirection.NEGATIVE, f"P/E {f:.1f} elevated (>45)."
    if f < 12:
        return SignalDirection.POSITIVE, f"P/E {f:.1f} low (<12)."
    return SignalDirection.NEUTRAL, f"P/E {f:.1f} within normal range (12–45)."


def _roe_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "ROE non-numeric."
    if f > 15:
        return SignalDirection.POSITIVE, f"ROE {f:.1f}% strong (>15%)."
    if f < 5:
        return SignalDirection.NEGATIVE, f"ROE {f:.1f}% weak (<5%)."
    return SignalDirection.NEUTRAL, f"ROE {f:.1f}% moderate (5–15%)."


def _revenue_growth_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "Revenue growth non-numeric."
    if f > 10:
        return SignalDirection.POSITIVE, f"Revenue growth {f:.1f}% strong (>10%)."
    if f < -5:
        return SignalDirection.NEGATIVE, f"Revenue growth {f:.1f}% negative (<-5%)."
    return SignalDirection.NEUTRAL, f"Revenue growth {f:.1f}% moderate (-5% to 10%)."


def _news_sentiment_rule(v: Any) -> Tuple[SignalDirection, str]:
    f = _safe_float(v)
    if f is None:
        return SignalDirection.NEUTRAL, "News sentiment non-numeric."
    if f > 60:
        return SignalDirection.POSITIVE, f"News sentiment score {f:.0f} positive (>60)."
    if f < 40:
        return SignalDirection.NEGATIVE, f"News sentiment score {f:.0f} negative (<40)."
    return SignalDirection.NEUTRAL, f"News sentiment score {f:.0f} neutral (40–60)."


_DEFAULT_RULES: Dict[str, Callable[[Any], Tuple[SignalDirection, str]]] = {
    "rsi_14":         _rsi_rule,
    "win_rate":       _win_rate_rule,
    "risk_score":     _risk_score_rule,
    "signal_strength": _signal_strength_rule,
    "sharpe_ratio":   _sharpe_rule,
    "pe_ratio":       _pe_rule,
    "roe":            _roe_rule,
    "revenue_growth": _revenue_growth_rule,
    "earnings_growth": _revenue_growth_rule,  # same logic
    "news_sentiment": _news_sentiment_rule,
    "portfolio_risk_pct": lambda v: (
        (SignalDirection.NEGATIVE, f"Portfolio risk {v}% elevated (>3%).") if (_safe_float(v) or 0) > 3
        else (SignalDirection.POSITIVE, f"Portfolio risk {v}% contained (<1%).") if (_safe_float(v) or 99) < 1
        else (SignalDirection.NEUTRAL, f"Portfolio risk {v}% moderate (1–3%).")
    ),
}


class SignalInterpreter:
    """
    Applies rule-based direction labels to interpreted signals.
    Rules are injected; defaults are provided for well-known evidence keys.
    """

    def __init__(
        self,
        extra_rules: Optional[Dict[str, Callable[[Any], Tuple[SignalDirection, str]]]] = None,
    ) -> None:
        self._rules: Dict[str, Callable[[Any], Tuple[SignalDirection, str]]] = {
            **_DEFAULT_RULES,
            **(extra_rules or {}),
        }

    def interpret(self, signal: InterpretedSignal) -> InterpretedSignal:
        rule = self._rules.get(signal.key)
        if rule is None:
            return signal   # direction stays NEUTRAL
        try:
            direction, interpretation = rule(signal.value)
        except Exception:
            return signal   # on rule failure, stay NEUTRAL
        return replace(signal, direction=direction, interpretation=interpretation)

    def interpret_all(
        self,
        signals: List[InterpretedSignal],
        order:   int = 2,
    ) -> Tuple[List[InterpretedSignal], ReasoningStep]:
        interpreted = [self.interpret(s) for s in signals]
        pos = sum(1 for s in interpreted if s.direction == SignalDirection.POSITIVE)
        neg = sum(1 for s in interpreted if s.direction == SignalDirection.NEGATIVE)
        step = make_step(
            step_type=ReasoningStepType.SIGNAL_INTERPRETATION,
            description=f"Applied signal direction rules to {len(interpreted)} signals.",
            intermediate_conclusion=(
                f"Signal interpretation complete: {pos} positive, {neg} negative, "
                f"{len(interpreted) - pos - neg} neutral signals identified."
            ),
            evidence_trace_ids=tuple(s.trace_id for s in interpreted),
            confidence=75.0,
            order=order,
            module_name="SignalInterpreter",
        )
        return interpreted, step
