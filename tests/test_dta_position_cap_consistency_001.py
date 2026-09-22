"""
tests/test_dta_position_cap_consistency_001.py
=================================================
DTA-POSITION-CAP-CONSISTENCY-001

Root cause (found during a forensic rejection audit, 2026-09-22): the
system had 3 independent, non-derived position-count caps:
  config.MAX_POSITIONS                    = 5   (capital-tier-scaled)
  execution_engine/order_manager.py:
      MAX_OPEN_POSITIONS = max(15, MAX_POSITIONS+5)   (already derived)
  risk_guardian/risk_guardian.py:
      MAX_OPEN_TRADES = 8                              (bare hardcoded)

Real consequence confirmed in production data: on 2026-09-17 the account
reached 8 open positions (60% over the intended tier budget of 5) --
RiskGuardian's hardcoded 8 was the only thing that stopped further
entries, purely by coincidence of its value, not by design.

Fix: MAX_OPEN_TRADES now derives from config.MAX_POSITIONS with the same
"+buffer, floor" shape order_manager.py already uses, so all 3 position
caps move together if the capital tier ever changes. At today's tier
(MAX_POSITIONS=5) this resolves to exactly 8 -- zero behavior change.
"""
from __future__ import annotations

import importlib


def test_t01_current_tier_unchanged_at_8():
    """At today's capital tier (MAX_POSITIONS=5), MAX_OPEN_TRADES must
    still resolve to exactly 8 -- zero behavior change."""
    from risk_guardian import risk_guardian as rg
    from config import MAX_POSITIONS
    assert MAX_POSITIONS == 5, "test assumes the current ₹50k tier (MAX_POSITIONS=5)"
    assert rg.MAX_OPEN_TRADES == 8


def test_t02_derives_from_config_max_positions(monkeypatch):
    """If config.MAX_POSITIONS were higher, MAX_OPEN_TRADES must scale up
    with it (buffer of +3), not stay frozen at the old hardcoded 8."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "MAX_POSITIONS", 10, raising=False)
    from risk_guardian import risk_guardian as rg
    importlib.reload(rg)
    try:
        assert rg.MAX_OPEN_TRADES == 13   # max(8, 10+3)
    finally:
        importlib.reload(rg)  # restore real config-derived value for other tests


def test_t03_never_drops_below_floor_of_8(monkeypatch):
    """Even if MAX_POSITIONS were very small, MAX_OPEN_TRADES must never
    drop below the safety floor of 8."""
    import config as _cfg
    monkeypatch.setattr(_cfg, "MAX_POSITIONS", 1, raising=False)
    from risk_guardian import risk_guardian as rg
    importlib.reload(rg)
    try:
        assert rg.MAX_OPEN_TRADES == 8   # max(8, 1+3) == 8
    finally:
        importlib.reload(rg)


def test_t04_stays_looser_than_cre_tighter_than_order_manager():
    """RiskGuardian's cap must sit strictly between CRE's tier budget and
    OrderManager's own last-resort cap -- a meaningful defense-in-depth
    checkpoint, not a duplicate or a tighter gate than the primary budget."""
    from risk_guardian import risk_guardian as rg
    from execution_engine.order_manager import MAX_OPEN_POSITIONS
    from config import MAX_POSITIONS
    assert MAX_POSITIONS < rg.MAX_OPEN_TRADES < MAX_OPEN_POSITIONS
