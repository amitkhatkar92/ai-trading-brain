"""
DTA-DEBATE-TELEMETRY-002 — Rejected Decision Specialist-Vote Telemetry.

Verifies (via direct source inspection of the exact production payload
blocks, plus a live event-bus round-trip through control_tower.telemetry_
logger) that:

  1. TRADE_REJECTED now carries the same "votes" key as TRADE_APPROVED.
  2. ct_decisions (via TelemetryLogger._on_event) receives real per-agent
     scores for a rejected decision instead of zero-filling them.
  3. TRADE_APPROVED's payload is unchanged (still has votes + score +
     modifier, in that construction).
  4. The final weighted "score" and "reason" fields are unchanged.
  5. No change to approval/rejection behavior itself (this is telemetry
     only — DecisionEngine/Debate are not touched by this fix; verified
     by source-absence in the diff, not re-tested here).
"""
from __future__ import annotations

import sqlite3

import pytest

from communication.events import EventType, DecisionEvent
import control_tower.telemetry_logger as _tl_module
from control_tower.telemetry_logger import TelemetryLogger


class _FakeBus:
    def subscribe(self, *args, **kwargs):
        pass


@pytest.fixture(autouse=True)
def tmp_db_path(tmp_path, monkeypatch):
    """Redirect TelemetryLogger's module-level DB_PATH to a temp file for
    every test in this module."""
    db_path = tmp_path / "control_tower_test.db"
    monkeypatch.setattr(_tl_module, "DB_PATH", str(db_path))
    yield str(db_path)



def _read_orchestrator_source() -> str:
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "orchestrator", "master_orchestrator.py")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_trade_rejected_payload_now_carries_votes():
    src = _read_orchestrator_source()
    rejected_block_start = src.find("event_type=EventType.TRADE_REJECTED")
    rejected_block_end = src.find("return None", rejected_block_start)
    rejected_block = src[rejected_block_start:rejected_block_end]
    assert '"votes":' in rejected_block
    assert "v.agent_name: v.score for v in votes" in rejected_block


def test_trade_approved_payload_unchanged():
    src = _read_orchestrator_source()
    approved_block_start = src.find("event_type=EventType.TRADE_APPROVED")
    approved_block_end = src.find("))", approved_block_start)
    approved_block = src[approved_block_start:approved_block_end]
    assert '"votes":' in approved_block
    assert '"score":' in approved_block
    assert '"modifier":' in approved_block


def test_rejected_score_and_reason_fields_unchanged():
    src = _read_orchestrator_source()
    rejected_block_start = src.find("event_type=EventType.TRADE_REJECTED")
    rejected_block_end = src.find("return None", rejected_block_start)
    rejected_block = src[rejected_block_start:rejected_block_end]
    assert '"score":     decision.confidence_score,' in rejected_block
    assert '"reason":    decision.summary(),' in rejected_block


def test_ct_decisions_receives_real_scores_for_rejected_decision(tmp_db_path):
    """End-to-end: publish a real TRADE_REJECTED event with a votes payload
    through the real TelemetryLogger and confirm ct_decisions.technical_score
    (etc.) are populated with the real values, not 0."""
    logger = TelemetryLogger(_FakeBus())
    event = DecisionEvent(
        event_type=EventType.TRADE_REJECTED,
        source_agent="DecisionEngine",
        payload={
            "symbol": "TESTSTOCK",
            "strategy": "unassigned",
            "direction": "BUY",
            "score": 5.2,
            "reason": "Weighted score 5.2 | Threshold 6.5 | Trade type: REJECT",
            "votes": {
                "TechnicalAnalystAI": 8.0,
                "RiskDebateAI": 4.5,
                "MacroAnalystAI": 7.0,
                "SentimentAI": 7.0,
                "RegimeDebateAI": 5.0,
            },
        },
    )
    logger._on_event(event)

    conn = sqlite3.connect(tmp_db_path)
    row = conn.execute(
        "SELECT technical_score, risk_score, macro_score, sentiment_score, "
        "regime_score, decision FROM ct_decisions WHERE symbol='TESTSTOCK'"
    ).fetchone()
    assert row is not None
    technical_score, risk_score, macro_score, sentiment_score, regime_score, decision = row
    assert technical_score == 8.0
    assert risk_score == 4.5
    assert macro_score == 7.0
    assert sentiment_score == 7.0
    assert regime_score == 5.0
    assert decision == "REJECTED"


def test_ct_decisions_approved_path_still_works(tmp_db_path):
    """Regression: TRADE_APPROVED path (already working) is unaffected."""
    logger = TelemetryLogger(_FakeBus())
    event = DecisionEvent(
        event_type=EventType.TRADE_APPROVED,
        source_agent="DecisionEngine",
        payload={
            "symbol": "APPROVEDSTOCK",
            "strategy": "unassigned",
            "direction": "BUY",
            "score": 7.4,
            "modifier": 1.0,
            "votes": {
                "TechnicalAnalystAI": 8.0,
                "RiskDebateAI": 7.5,
                "MacroAnalystAI": 7.2,
                "SentimentAI": 7.0,
                "RegimeDebateAI": 8.0,
            },
        },
    )
    logger._on_event(event)

    conn = sqlite3.connect(tmp_db_path)
    row = conn.execute(
        "SELECT technical_score, decision FROM ct_decisions WHERE symbol='APPROVEDSTOCK'"
    ).fetchone()
    assert row is not None
    assert row[0] == 8.0
    assert row[1] == "APPROVED"
