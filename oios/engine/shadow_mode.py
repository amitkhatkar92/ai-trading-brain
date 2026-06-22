"""
oios/engine/shadow_mode.py

Single source of truth for Phase D shadow mode.

Shadow mode ON (SHADOW_MODE = True):
    - All Phase D modules run normally — data accumulates every trading day
    - Layer 6 (Adaptive Intelligence) computes proposals but does NOT write to
      pending_adjustments
    - archetype_outcome_distributions rows are written but is_distribution_active
      is never set to 1 (no downstream consumption of distributions)
    - Velocity, transition probabilities, and counterfactual reports are computed
      and stored — purely for observation
    - Phase C deterministic RE + state machine logic is unchanged and unaffected

Shadow mode OFF (SHADOW_MODE = False):
    - Layer 6 writes proposals to pending_adjustments with full guardrails
    - is_distribution_active flips to 1 when observation_count_weighted >= 20
    - Phase D is live — only turn off after D-Ready gates pass and explicit
      authorization is given

To turn OFF shadow mode (requires explicit human action):
    1. python check_phase_d_ready.py  — verify all 5 D-Ready gates pass
    2. Edit this file: set SHADOW_MODE = False
    3. Restart the scheduler

Default: SHADOW_MODE = True for all Phase D deployments.
"""

# ---------------------------------------------------------------------------
# Shadow mode control
# ---------------------------------------------------------------------------

# Set to False ONLY after D-Ready-1 through D-Ready-5 all pass.
# Changing this to False activates live adaptive behavior (Layer 6 proposals).
SHADOW_MODE: bool = True

# Minimum observation count before any distribution is marked active.
# MAS_v1.2.md Layer 6 activation gate: >= 30 complete lifecycles per (archetype, regime)
# For is_distribution_active: >= 20 observation_count_weighted (Table 10 spec).
MIN_DISTRIBUTION_OBSERVATIONS: int = 20

# Layer 6 guardrails
TTL_FLOORS: dict[str, int] = {
    "1A":  5,
    "1B":  8,
    "1.5": 14,
}
MAX_TTL_CHANGE_PCT:    float = 0.20   # ±20% per cycle
MAX_WEIGHT_CHANGE_PCT: float = 0.15   # ±15% per cycle
MAX_HL_CHANGE_PCT:     float = 0.20   # ±20% per cycle
PROPOSAL_TTL_DAYS:     int   = 14     # proposals expire in 14 days
MIN_OBS_FOR_PROPOSAL:  int   = 30     # Layer 6 gate: 30 complete lifecycles
