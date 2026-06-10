"""
Research Integrity — Adaptive Maturity Protection
===================================================
Patches 19-24: Dynamic legacy weight decay, contamination telemetry,
clean research readiness gate, and adaptive mutation freeze.

Architectural principle
───────────────────────
The PREPARED_UNIVERSE_V1 architecture produces structurally different
telemetry than LEGACY_STATIC (broader universe, deterministic levels,
no proxy ATR, diversified opportunities). Adaptive intelligence must
NOT be driven by legacy data during the maturation phase.

  • LEGACY_STATIC weight decays as prepared telemetry grows (Patch 19).
  • Adaptive mutations are frozen until prepared_trade_count >= 100 (Patch 21/24).
  • [ResearchContamination] quantifies the telemetry blend at EOD (Patch 20).
  • [CleanResearchState] makes the mutation gate status explicit (Patch 22).

Public API
──────────
  compute_legacy_weight(prepared_trade_count)  → float
  get_system_prepared_trade_count()            → int
  is_clean_research_ready()                   → bool
  emit_contamination_telemetry(legacy_count, prepared_count, source)
  emit_clean_research_state(source)
"""

from __future__ import annotations

import math

from utils import get_logger

log = get_logger(__name__)

# ── Constants (imported from config, with fallbacks) ──────────────────────────
try:
    from config import (
        MIN_CLEAN_PREPARED_TRADES as _MIN_CLEAN_CFG,
        RESEARCH_WEIGHT_LEGACY_STATIC as _LEGACY_W_CFG,
    )
    MIN_CLEAN_PREPARED_TRADES: int = _MIN_CLEAN_CFG
    _LEGACY_W_BASE: float          = _LEGACY_W_CFG
except Exception:
    MIN_CLEAN_PREPARED_TRADES: int = 100
    _LEGACY_W_BASE: float          = 0.25

_LEGACY_W_FLOOR: float = 0.10   # floor: legacy still has execution/governance value
_LEGACY_DECAY_K: float = 100.0  # e-folding length in prepared trade count


# ─────────────────────────────────────────────────────────────────────────────
# Patch 19 — Dynamic Legacy Weight Decay
# ─────────────────────────────────────────────────────────────────────────────

def compute_legacy_weight(prepared_trade_count: int) -> float:
    """
    Decay the legacy research weight as prepared telemetry accumulates.

    Formula:
        legacy_weight = max(floor=0.10, base=0.25 × exp(-prepared / 100))

    Progression
    -----------
      prepared=0   →  0.2500  (epoch start — legacy still operationally useful)
      prepared=50  →  0.1516
      prepared=100 →  0.0920  → capped at 0.10
      prepared=200 →  0.0338  → capped at 0.10
      prepared=300 →  0.0125  → capped at 0.10

    The floor (0.10) is intentional: legacy trades still contain execution
    lessons, governance behaviour, and operational resilience data that remain
    directionally useful even if structurally contaminated.
    """
    raw = _LEGACY_W_BASE * math.exp(-prepared_trade_count / _LEGACY_DECAY_K)
    return round(max(_LEGACY_W_FLOOR, raw), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Patch 21/24 — Clean Research Readiness Gate
# ─────────────────────────────────────────────────────────────────────────────

def get_system_prepared_trade_count() -> int:
    """
    Return the total PREPARED_UNIVERSE_V1 trade count across ALL tracked strategies.
    Used to evaluate the system-wide adaptive mutation gate.
    """
    try:
        # Late import to avoid circular dependency at module load time.
        from learning_system.strategy_performance_tracker import get_performance_tracker
        stats = get_performance_tracker().get_all_stats()
        return sum(s.prepared_universe_trades for s in stats.values())
    except Exception:
        return 0


def is_clean_research_ready() -> bool:
    """
    System-wide adaptive mutation gate (Patch 21/24).

    Returns True ONLY when total system prepared trade count
    meets MIN_CLEAN_PREPARED_TRADES (default: 100).

    UNTIL True, the following MUST be blocked by callers:
      • strategy auto-disabling
      • adaptive threshold mutation
      • exploration budget auto-expansion
      • overlay amplification
      • confidence auto-scaling
      • adaptive demotion / suppression logic

    The following are ALWAYS permitted regardless of readiness:
      • telemetry emission
      • monitoring and reporting
      • ranking
      • statistical observation
    """
    return get_system_prepared_trade_count() >= MIN_CLEAN_PREPARED_TRADES


# ─────────────────────────────────────────────────────────────────────────────
# Patch 20 — Research Contamination Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def emit_contamination_telemetry(
    legacy_count: int,
    prepared_count: int,
    source: str = "EOD",
) -> dict:
    """
    Emit [ResearchContamination] telemetry (Patch 20).

    Quantifies how much legacy architecture still influences the research pool,
    using the dynamic legacy weight. Purely observational — does not block anything.

    Returns a dict of the computed values (for report embedding).
    """
    lw           = compute_legacy_weight(prepared_count)
    legacy_wt    = legacy_count  * lw
    prepared_wt  = prepared_count * 1.0
    total_wt     = legacy_wt + prepared_wt

    if total_wt > 0:
        legacy_wpct   = round(legacy_wt   / total_wt * 100, 1)
        prepared_wpct = round(prepared_wt / total_wt * 100, 1)
    else:
        legacy_wpct   = 0.0
        prepared_wpct = 0.0

    log.info(
        "[ResearchContamination] source=%s  "
        "legacy_trade_count=%d  prepared_trade_count=%d  "
        "effective_legacy_weight=%.4f  "
        "legacy_weighted_pct=%.1f  prepared_weighted_pct=%.1f",
        source,
        legacy_count, prepared_count,
        lw,
        legacy_wpct, prepared_wpct,
    )

    return {
        "legacy_trade_count":      legacy_count,
        "prepared_trade_count":    prepared_count,
        "effective_legacy_weight": lw,
        "legacy_weighted_pct":     legacy_wpct,
        "prepared_weighted_pct":   prepared_wpct,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Patch 22 — Clean Research State Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def emit_clean_research_state(source: str = "EOD") -> dict:
    """
    Emit [CleanResearchState] telemetry (Patch 22).

    Makes the adaptive mutation gate status explicit in the log.
    Returns a dict of gate state (for report embedding).
    """
    prepared_count = get_system_prepared_trade_count()
    ready          = prepared_count >= MIN_CLEAN_PREPARED_TRADES
    frozen         = not ready

    log.info(
        "[CleanResearchState] source=%s  "
        "prepared_trade_count=%d  required=%d  "
        "ready=%s  adaptive_mutation_blocked=%s",
        source,
        prepared_count, MIN_CLEAN_PREPARED_TRADES,
        ready, frozen,
    )

    return {
        "prepared_trade_count":    prepared_count,
        "required":                MIN_CLEAN_PREPARED_TRADES,
        "ready":                   ready,
        "adaptive_mutation_blocked": frozen,
    }
