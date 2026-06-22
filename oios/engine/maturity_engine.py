"""
oios/engine/maturity_engine.py

Sub-B: Maturity Engine
Layer 5 — Edge Lifecycle Engine

Computes three independent maturity dimensions per MAS v1.2 Section 5, Sub-B:

    Temporal  = age / effective_ttl
    Path      = EC percentile (linear ratio in Phase C)
    Conviction = confirming source count

Each dimension maps to one of five stages:
    SEED | EMERGING | DEVELOPING | MATURE | LATE_STAGE

maturity_combined = most conservative (earliest-stage) of the three dimensions.

"Most conservative" means:
    If Temporal=DEVELOPING and Path=SEED and Conviction=EMERGING
    → maturity_combined = SEED  (earliest stage wins)

NO DB WRITES in this module. Pure computation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Maturity stage constants — ordered from earliest to latest
# ---------------------------------------------------------------------------

SEED        = "SEED"
EMERGING    = "EMERGING"
DEVELOPING  = "DEVELOPING"
MATURE      = "MATURE"
LATE_STAGE  = "LATE_STAGE"

# Ordered list — used for "most conservative" comparison
_STAGE_ORDER: list[str] = [SEED, EMERGING, DEVELOPING, MATURE, LATE_STAGE]

# Thresholds (fraction) for Temporal and Path dimensions
# (SEED: 0–20%, EMERGING: 20–40%, DEVELOPING: 40–60%, MATURE: 60–80%, LATE_STAGE: >80%)
_FRACTION_THRESHOLDS: list[tuple[float, str]] = [
    (0.20, SEED),
    (0.40, EMERGING),
    (0.60, DEVELOPING),
    (0.80, MATURE),
    (1.01, LATE_STAGE),   # 1.01 ensures anything >= 0.80 falls into LATE_STAGE
]

# Confirming count → maturity stage mapping
# (MAS v1.2 Section 5, Sub-B Conviction dimension table)
_CONVICTION_MAP: list[tuple[int, str]] = [
    (1, SEED),
    (2, EMERGING),
    (3, DEVELOPING),
    (4, MATURE),
]
# confirming_count >= 5 and declining → LATE_STAGE (handled separately)
_CONVICTION_LATE_THRESHOLD = 4  # at and above this, LATE_STAGE applies


# ---------------------------------------------------------------------------
# Individual dimension functions
# ---------------------------------------------------------------------------

def _fraction_to_stage(fraction: float) -> str:
    """Map a 0–1 fraction to a maturity stage using the threshold table."""
    for threshold, stage in _FRACTION_THRESHOLDS:
        if fraction < threshold:
            return stage
    return LATE_STAGE


def temporal_maturity(age_trading_days: int, effective_ttl_days: int) -> str:
    """
    Temporal dimension: age / effective_ttl.

    If effective_ttl_days <= 0, treats the opportunity as LATE_STAGE
    (it should have been expired already).
    """
    if effective_ttl_days <= 0:
        return LATE_STAGE
    fraction = age_trading_days / effective_ttl_days
    return _fraction_to_stage(fraction)


def path_maturity(ec_path: float) -> str:
    """
    Path dimension: EC_path (linear ratio in Phase C, percentile in Phase D+).

    ec_path ranges 0.0–1.0. Maps to stages using the same fraction thresholds.
    """
    return _fraction_to_stage(max(0.0, min(1.0, ec_path)))


def conviction_maturity(confirming_count: int) -> str:
    """
    Conviction dimension: confirming source count.

    MAS table:
        1 confirming  → SEED
        2 confirming  → EMERGING
        3 confirming  → DEVELOPING
        4 confirming  → MATURE
        4+ confirming → LATE_STAGE

    Note: "4+ declining" in the MAS spec means that once confirming signals start
    to be contradicted, we move to LATE_STAGE. Phase C does not track per-signal
    decline — it uses count only. Phase D will add the declining-signal detector.
    """
    if confirming_count <= 0:
        return SEED
    for threshold, stage in _CONVICTION_MAP:
        if confirming_count <= threshold:
            return stage
    # confirming_count > 4 → LATE_STAGE
    return LATE_STAGE


# ---------------------------------------------------------------------------
# Combined maturity
# ---------------------------------------------------------------------------

def most_conservative(*stages: str) -> str:
    """
    Return the earliest (most conservative) of the supplied maturity stages.

    "Most conservative" = earliest position in _STAGE_ORDER.
    Ensures the combined maturity never overstates the opportunity's development.
    """
    if not stages:
        return SEED
    orders = [_STAGE_ORDER.index(s) if s in _STAGE_ORDER else 0 for s in stages]
    return _STAGE_ORDER[min(orders)]


def compute_maturity(
    age_trading_days: int,
    effective_ttl_days: int,
    ec_path: float,
    confirming_count: int,
) -> str:
    """
    Compute maturity_combined from the three independent dimensions.

    Returns the most conservative (earliest) stage across:
        - Temporal (age vs TTL)
        - Path (EC_path ratio)
        - Conviction (confirming count)

    This is the value written to signal_births.maturity_combined and
    opportunities.maturity_combined on each daily ELE cycle.
    """
    t_stage = temporal_maturity(age_trading_days, effective_ttl_days)
    p_stage = path_maturity(ec_path)
    c_stage = conviction_maturity(confirming_count)
    return most_conservative(t_stage, p_stage, c_stage)
