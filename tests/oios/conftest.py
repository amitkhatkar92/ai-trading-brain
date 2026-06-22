"""
tests/oios/conftest.py
Shared fixtures for Phase A0 acceptance tests.
Uses an in-memory SQLite database via OIOS_DB_PATH=:memory: env variable.
"""

import os
import sqlite3
import uuid
import pytest

os.environ["OIOS_DB_PATH"] = ":memory:"

from oios.db.migrations import apply_phase_a0
from oios.domain.models import Opportunity, SignalBirth, OpportunityState


@pytest.fixture
def conn():
    """Fresh in-memory DB, fully migrated, for each test."""
    c = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON;")
    apply_phase_a0(conn=c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_opportunity(
    symbol: str = "BEL.NS",
    direction: str = "LONG",
    sector: str = "Defence",
    conviction_score: float = 0.0,
    birth_ttl_days: int = 18,
    age_trading_days: int = 0,
    state: str = OpportunityState.DISCOVERED,
    position_exists: bool = False,
    position_size_pct: float = 0.0,
    consecutive_conflict_days: int = 0,
    edge_consumed_pct: float = 0.0,
) -> Opportunity:
    opp_id = str(uuid.uuid4())
    # discovered_expires_at = birth + floor(ttl × 0.5) trading days
    # For tests we just use a fixed date far enough ahead or past as needed
    return Opportunity(
        opportunity_id       = opp_id,
        symbol               = symbol,
        direction            = direction,
        sector               = sector,
        created_at           = "2026-06-01",
        regime_at_birth      = "BULL",
        birth_ttl_days       = birth_ttl_days,
        effective_ttl_days   = birth_ttl_days,
        age_trading_days     = age_trading_days,
        discovered_expires_at= "2026-06-12",   # 9 trading days after 2026-06-01
        conviction_score     = conviction_score,
        current_state        = state,
        position_exists      = position_exists,
        position_size_pct    = position_size_pct,
        consecutive_conflict_days = consecutive_conflict_days,
        edge_consumed_pct    = edge_consumed_pct,
    )


def make_signal(
    symbol: str = "BEL.NS",
    archetype_id: str = "DNA_1B_QUIET_ACC",
    signal_type: str = "1B",
    base_score: float = 7.5,
    opportunity_id: str = None,
) -> SignalBirth:
    return SignalBirth(
        signal_id               = str(uuid.uuid4()),
        opportunity_id          = opportunity_id,
        symbol                  = symbol,
        archetype_id            = archetype_id,
        signal_type             = signal_type,
        detected_at             = "2026-06-01",
        birth_price             = 245.50,
        base_score              = base_score,
        regime_at_birth         = "BULL",
        expected_ttl_days       = 18,
        expected_move_direction = "LONG",
    )
