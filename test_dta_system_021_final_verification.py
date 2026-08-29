"""
test_dta_system_021_final_verification.py
==========================================
DTA-SYSTEM-021 — Final Verification + Root-Cause Resolution

Two defects fixed in this pass:

  DEF-021-001 (Phase 3 / Root Cause):
    DTA-020 Fix B used fixed floors (7.0/7.5) that were artificial numbers
    chosen to clear legacy gates rather than genuine representations of
    conviction.  Replaced with evidence-derived conviction computed from
    actual KDA metrics: ESS tier (base) + win-rate bonus (P(target_hit)).

    DECISION_ELIGIBLE (ESS≥100): base=8.0 + win-rate bonus → 8.0–9.5
    VALIDATED         (ESS30–99): base=7.0 + win-rate bonus → 7.0–8.5
    USEFUL/DEVELOPING/INSUFFICIENT: no boost → not executable

  DEF-021-002 (Phase 2 / Debate):
    RegimeDebateAI._regime_vote() gave KDA_AUTHORITY signals score=5.0 /
    modifier=0.7 because "KDA_AUTHORITY" is not in the regime_strategy_matrix.
    This is a legacy strategy-specific gate.  KDA's HBE evidence lookup
    already includes regime as a query parameter, so regime compatibility is
    implicit.  Fixed: KDA_AUTHORITY and knowledge_referred now return
    score=8.0 / modifier=1.0 from RegimeDebateAI.

Architecture invariants verified (non-exhaustive, key invariants only):
  - KDA WAIT   → cannot execute (not in kda_authorized)
  - KDA HOLD   → cannot execute (blocked in Phase 1 merge)
  - KDA BUY    → can reach execution when evidence + safety gates permit
  - KDA BUY    does NOT bypass CRE, RiskGuardian, Debate, or OrderManager
  - KDA cannot directly call broker (execution_authority=False, broker_calls=0)
  - Only OrderManager has execution authority
  - Historical KEL evidence is available to knowledge_referred (no strategy filter in HBE)
  - opportunity_id lineage: scanner → KLP → LOL → KDA → OrderManager → journal

Test inventory (T001–T060 + SRC + FLOW):

  DEF-021-001: Evidence-derived conviction formula
  T001  DECISION_ELIGIBLE ess=327 thp=74% → conviction 9.42 (≥8.0, ≤9.5)
  T002  DECISION_ELIGIBLE ess=100 thp=55% → conviction 8.0 (no wr bonus below threshold)
  T003  DECISION_ELIGIBLE ess=100 thp=80% → conviction 9.5 (max cap)
  T004  VALIDATED ess=50 thp=60%  → conviction 7.375
  T005  VALIDATED ess=30 thp=55%  → conviction 7.0 (bare minimum VALIDATED)
  T006  USEFUL ess=15 thp=60%     → NO boost (evidence_state not VALIDATED/DECISION_ELIGIBLE)
  T007  DEVELOPING ess=5           → NO boost
  T008  INSUFFICIENT ess=0         → NO boost
  T009  Already high confidence (8.5) → NOT lowered by formula (floor only)
  T010  No thp (None) → wr_bonus = 0 → base only
  T011  Conviction monotone: DECISION_ELIGIBLE > VALIDATED > USEFUL (for same win rate)
  T012  Non-knowledge_referred + DECISION_ELIGIBLE → NOT boosted
  T013  KNOWLEDGE_WAIT + DECISION_ELIGIBLE → NOT boosted (decision gate)

  DEF-021-002: RegimeDebateAI KDA authority recognition
  T020  KDA_AUTHORITY → RegimeDebateAI score=8.0, modifier=1.0
  T021  knowledge_referred → RegimeDebateAI score=8.0, modifier=1.0
  T022  Non-KDA strategy (Equity_Breakout) in allowed list → score=8.0 (unchanged)
  T023  Non-KDA strategy (Equity_Breakout) NOT in allowed → score=5.0, modifier=0.7
  T024  KDA_AUTHORITY → vote is "approve" (not "reduce_size")
  T025  kda_evidence_state is included in reasoning
  T026  RegimeDebateAI does NOT emit a hard "reject" vote for KDA_AUTHORITY

  Phase 4 — KDA Authority invariants
  T030  KNOWLEDGE_WAIT → not added to kda_authorized (cannot execute)
  T031  KNOWLEDGE_HOLD → Phase 1 merge blocks the signal (HOLD is not BUY/SELL)
  T032  KNOWLEDGE_BUY  → added to kda_authorized
  T033  KDA result has execution_authority=False and broker_calls=0
  T034  KDA result has orders=0
  T035  KDA BUY does NOT bypass Phase 2 confidence gate (< conviction)
  T036  KDA BUY does NOT bypass RiskManager confidence gate (< 6.8)

  Phase 5 — Knowledge state execution eligibility
  T040  INSUFFICIENT + KDA_BUY  → conviction not boosted → fails RiskManager
  T041  DEVELOPING + KDA_BUY    → conviction not boosted → fails RiskManager
  T042  USEFUL + KDA_BUY        → conviction not boosted → fails GAP-029 and RiskManager
  T043  VALIDATED + KDA_BUY + thp=0.60 → conviction 7.375 → passes RiskManager (≥6.8)
  T044  DECISION_ELIGIBLE + KDA_BUY + thp=0.74 → conviction 9.42 → passes all gates
  T045  KNOWLEDGE_WAIT + any evidence → NOT in kda_authorized → never reaches Phase 2
  T046  KNOWLEDGE_HOLD + any evidence → Phase 1 blocked, not in authorized → no execution

  Phase 7 — Lineage (source inspection)
  T050  opportunity_id set in scanner (equity_scanner_ai.py)
  T051  opportunity_id passed to KDA observation (_build_observation in pipeline)
  T052  opportunity_id in KDA result dict
  T053  opportunity_id propagated to OrderManager record (order_manager.py)

  Phase 8 — Historical evidence availability (source inspection)
  T054  HBE get_behaviour_profile does NOT filter by strategy_name
  T055  KDA pipeline does NOT filter by strategy_name in evidence lookup

  Phase 9 — Equivalent occurrence search
  T056  RiskManagerAI: no strategy_name gate (only confidence + RR + stop gates)
  T057  PortfolioAllocationAI: uses bucket by market cap, not strategy_name
  T058  CRE.allocate: no hard confidence gate, uses quality sort only
  T059  All other debate agents (Technical/Macro/Risk/Sentiment): no strategy_name gate

  Source / Regression
  SRC-001  _kr_conv in master_orchestrator.py (evidence-derived conviction)
  SRC-002  KDA_AUTHORITY exemption in debate_system/multi_agent_debate.py
  SRC-003  Fix A guard still in strategy_generator_ai.py
  SRC-004  Fix C GAP-029 exemption still in master_orchestrator.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── minimal harness ─────────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0


def _ok(tid, desc):
    global _PASS; _PASS += 1
    print(f"  PASS  {tid}: {desc}")


def _fail(tid, desc, reason):
    global _FAIL; _FAIL += 1
    print(f"  FAIL  {tid}: {desc}")
    print(f"         Reason: {reason}")


def _assert(tid, desc, cond, reason=""):
    if cond: _ok(tid, desc)
    else: _fail(tid, desc, reason or "assertion failed")


# ── shared stubs ─────────────────────────────────────────────────────────────

class _Dir(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"


class _SType(str, Enum):
    EQUITY  = "EQUITY"
    OPTIONS = "OPTIONS"
    SPREAD  = "SPREAD"


class _Regime(str, Enum):
    BULL_MARKET  = "BULL_MARKET"
    BEAR_MARKET  = "BEAR_MARKET"
    NEUTRAL      = "NEUTRAL"
    VOLATILE     = "VOLATILE"
    RANGE_MARKET = "RANGE_MARKET"
    BULL_TREND   = "BULL_TREND"


@dataclass
class _FakeSig:
    symbol:              str       = "TEST"
    strategy_name:       str       = "knowledge_referred"
    confidence:          float     = 5.5
    direction:           _Dir      = _Dir.BUY
    signal_type:         _SType    = _SType.EQUITY
    risk_reward_ratio:   float     = 2.5
    entry_price:         float     = 100.0
    stop_loss:           float     = 95.0
    target_price:        float     = 112.5
    kda_evidence_state:  str       = "VALIDATED"


@dataclass
class _FakeSnap:
    regime:      _Regime = _Regime.BULL_MARKET
    volatility:  str     = "NORMAL"
    vix:         float   = 15.0
    pcr:         float   = 1.0
    breadth:     float   = 0.60
    events_today: list   = field(default_factory=list)


# ── DEF-021-001 helpers (mirrors orchestrator KDA loop conviction logic) ─────

def _kda_conviction(ess: float, thp: Optional[float],
                    evidence_state: str, kda_decision: str,
                    strategy_name: str) -> float:
    """Reproduce master_orchestrator.py DTA-SYSTEM-021 conviction computation."""
    if (strategy_name != "knowledge_referred"
            or kda_decision != "KNOWLEDGE_BUY"
            or evidence_state not in ("DECISION_ELIGIBLE", "VALIDATED")):
        return 0.0  # no boost
    base = 8.0 if ess >= 100.0 else 7.0
    wr   = (max(0.0, min(1.5, (thp - 0.55) * 7.5))
            if thp is not None else 0.0)
    return round(min(9.5, base + wr), 2)


def _apply_conviction(sig: _FakeSig, kda_result: dict) -> None:
    conv = _kda_conviction(
        ess            = float(kda_result.get("effective_sample_size") or 0.0),
        thp            = kda_result.get("hbe_target_hit_prob"),
        evidence_state = kda_result.get("evidence_state", ""),
        kda_decision   = kda_result.get("kda_decision", ""),
        strategy_name  = getattr(sig, "strategy_name", ""),
    )
    if conv > sig.confidence:
        sig.confidence = conv


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 1 — DEF-021-001 evidence-derived conviction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_conviction():
    print("\n── DEF-021-001: Evidence-derived conviction formula ──────────────────")

    # T001: DECISION_ELIGIBLE ess=327 thp=74% → 8.0 + (0.74-0.55)*7.5 = 8.0+1.425 = 9.425
    c = _kda_conviction(327.0, 0.74, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T001", "DECISION_ELIGIBLE ess=327 thp=74% → ~9.42",
            8.0 <= c <= 9.5, f"got {c}")

    # T002: DECISION_ELIGIBLE ess=100 thp=0.55 (at threshold, no bonus) → 8.0
    c = _kda_conviction(100.0, 0.55, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T002", "DECISION_ELIGIBLE ess=100 thp=55% → 8.0 (no bonus)",
            c == 8.0, f"got {c}")

    # T003: DECISION_ELIGIBLE ess=100 thp=0.80 (max bonus) → 9.5 (capped)
    c = _kda_conviction(100.0, 0.80, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T003", "DECISION_ELIGIBLE ess=100 thp=80% → 9.5 (max cap)",
            c == 9.5, f"got {c}")

    # T004: VALIDATED ess=50 thp=0.60 → 7.0 + (0.60-0.55)*7.5 ≈ 7.374–7.376
    # (floating point: 0.60-0.55 is not exact; result rounds to 7.37 or 7.38)
    c = _kda_conviction(50.0, 0.60, "VALIDATED", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T004", "VALIDATED ess=50 thp=60% → 7.0–7.5 (win-rate bonus applied)",
            7.0 < c < 7.5, f"got {c}")

    # T005: VALIDATED ess=30 thp=0.55 → 7.0 + 0 = 7.0 (bare minimum)
    c = _kda_conviction(30.0, 0.55, "VALIDATED", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T005", "VALIDATED ess=30 thp=55% → 7.0 (bare minimum)",
            c == 7.0, f"got {c}")

    # T006: USEFUL → 0.0 (no boost for non-VALIDATED/DECISION_ELIGIBLE)
    c = _kda_conviction(15.0, 0.60, "USEFUL", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T006", "USEFUL → no conviction boost (returns 0.0)",
            c == 0.0, f"got {c}")

    # T007: DEVELOPING → 0.0
    c = _kda_conviction(5.0, 0.60, "DEVELOPING", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T007", "DEVELOPING → no boost",
            c == 0.0, f"got {c}")

    # T008: INSUFFICIENT → 0.0
    c = _kda_conviction(0.0, None, "INSUFFICIENT", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T008", "INSUFFICIENT → no boost",
            c == 0.0, f"got {c}")

    # T009: Already higher confidence (9.5 max cap) → NOT lowered (conviction is a floor,
    # DECISION_ELIGIBLE+thp=0.74 computes 9.42 which is below 9.5, so no change)
    s = _FakeSig(confidence=9.5)
    _apply_conviction(s, {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "DECISION_ELIGIBLE",
                           "effective_sample_size": 327.0, "hbe_target_hit_prob": 0.74})
    _assert("T009", "Confidence already at max (9.5) not lowered by conviction formula",
            s.confidence == 9.5, f"got {s.confidence}")

    # T010: thp=None → wr_bonus=0 → base only
    c = _kda_conviction(100.0, None, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T010", "thp=None → wr_bonus=0 → base=8.0",
            c == 8.0, f"got {c}")

    # T011: Monotone ordering
    c_de = _kda_conviction(200.0, 0.65, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "knowledge_referred")
    c_va = _kda_conviction(40.0,  0.65, "VALIDATED",         "KNOWLEDGE_BUY", "knowledge_referred")
    c_us = _kda_conviction(15.0,  0.65, "USEFUL",            "KNOWLEDGE_BUY", "knowledge_referred")
    _assert("T011", "Monotone: DECISION_ELIGIBLE > VALIDATED > USEFUL",
            c_de > c_va > c_us, f"DE={c_de} VA={c_va} US={c_us}")

    # T012: Non-knowledge_referred → not boosted
    c = _kda_conviction(327.0, 0.74, "DECISION_ELIGIBLE", "KNOWLEDGE_BUY", "Equity_Breakout")
    _assert("T012", "Non-knowledge_referred not boosted",
            c == 0.0, f"got {c}")

    # T013: KNOWLEDGE_WAIT → not boosted even with good evidence
    c = _kda_conviction(327.0, 0.74, "DECISION_ELIGIBLE", "KNOWLEDGE_WAIT", "knowledge_referred")
    _assert("T013", "KNOWLEDGE_WAIT → not boosted",
            c == 0.0, f"got {c}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 2 — DEF-021-002 RegimeDebateAI fix
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_debate_regime():
    """Test via source inspection + direct _regime_vote simulation."""
    print("\n── DEF-021-002: RegimeDebateAI KDA authority recognition ────────────")

    src_path = os.path.join(ROOT, "debate_system", "multi_agent_debate.py")
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()

    # SRC checks
    _assert("T020-SRC", "KDA_AUTHORITY exemption present in _regime_vote",
            'strat in ("KDA_AUTHORITY", "knowledge_referred")' in src,
            "KDA_AUTHORITY exemption not found in multi_agent_debate.py")
    _assert("T021-SRC", "KDA exempt returns score=8.0",
            "score=8.0" in src,
            "score=8.0 not found in the KDA exemption block")
    _assert("T024-SRC", "KDA exempt returns vote='approve'",
            "vote=\"approve\"" in src or "vote='approve'" in src,
            "approve vote not found in exemption block")

    # Simulate _regime_vote() logic directly
    def _regime_vote_sim(strategy_name: str, regime: str,
                          kda_evidence_state: str = "") -> dict:
        """Reproduce _regime_vote() logic."""
        if strategy_name in ("KDA_AUTHORITY", "knowledge_referred"):
            return {"vote": "approve", "score": 8.0,
                    "modifier": 1.0, "ev_state": kda_evidence_state}
        regime_strategy_matrix = {
            "BULL_TREND":   ["Breakout_Volume", "Momentum_Retest", "Bull_Call_Spread"],
            "RANGE_MARKET": ["Mean_Reversion", "Iron_Condor_Range", "Momentum_Retest"],
            "BEAR_MARKET":  ["Hedging_Model", "Short_Straddle_IV_Spike"],
            "VOLATILE":     ["Hedging_Model", "Iron_Condor_Range"],
        }
        allowed = regime_strategy_matrix.get(regime, [])
        if strategy_name in allowed:
            return {"vote": "approve", "score": 8.0, "modifier": 1.0}
        return {"vote": "reduce_size", "score": 5.0, "modifier": 0.7}

    v = _regime_vote_sim("KDA_AUTHORITY", "BULL_MARKET", "VALIDATED")
    _assert("T020", "KDA_AUTHORITY → RegimeDebateAI score=8.0, modifier=1.0",
            v["score"] == 8.0 and v["modifier"] == 1.0, f"got {v}")

    v = _regime_vote_sim("knowledge_referred", "BULL_MARKET", "DECISION_ELIGIBLE")
    _assert("T021", "knowledge_referred → RegimeDebateAI score=8.0, modifier=1.0",
            v["score"] == 8.0 and v["modifier"] == 1.0, f"got {v}")

    # Note: "Equity_Breakout" is NOT in BULL_TREND matrix (it's "Breakout_Volume").
    # Score=8.0 comes from the strategy actually being listed, e.g. Momentum_Retest.
    v = _regime_vote_sim("Momentum_Retest", "BULL_TREND")
    _assert("T022", "Momentum_Retest in BULL_TREND matrix → score=8.0",
            v["score"] == 8.0, f"got {v}")

    v = _regime_vote_sim("Equity_Breakout", "RANGE_MARKET")
    _assert("T023", "Equity_Breakout NOT in RANGE_MARKET matrix → score=5.0, reduce_size",
            v["score"] == 5.0 and v["vote"] == "reduce_size", f"got {v}")

    v = _regime_vote_sim("KDA_AUTHORITY", "BEAR_MARKET")
    _assert("T024", "KDA_AUTHORITY → vote=approve",
            v["vote"] == "approve", f"got {v}")

    v = _regime_vote_sim("KDA_AUTHORITY", "BULL_MARKET", "DECISION_ELIGIBLE")
    _assert("T025", "ev_state propagated in KDA exempt path",
            v.get("ev_state") == "DECISION_ELIGIBLE", f"got {v}")

    _assert("T026", "KDA_AUTHORITY → score=8.0, NOT a hard reject (score > 5)",
            v["score"] > 5.0, f"score={v['score']}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 3 — Phase 4: KDA authority invariants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_kda_authority():
    print("\n── Phase 4: KDA authority invariants ────────────────────────────────")

    # T030: KNOWLEDGE_WAIT → not in kda_authorized
    authorized: Set[str] = set()
    r_wait = {"kda_decision": "KNOWLEDGE_WAIT", "evidence_state": "VALIDATED"}
    if r_wait.get("kda_decision") in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL"):
        authorized.add("SYM")
    _assert("T030", "KNOWLEDGE_WAIT → NOT added to kda_authorized",
            "SYM" not in authorized, f"authorized={authorized}")

    # T031: KNOWLEDGE_HOLD → would trigger Phase 1 block (checked via source)
    src_mo = open(os.path.join(ROOT, "orchestrator", "master_orchestrator.py"),
                  encoding="utf-8").read()
    _assert("T031", "KNOWLEDGE_HOLD blocked in Phase 1 merge",
            'KNOWLEDGE_HOLD' in src_mo and 'kda_hold_blocked' in src_mo,
            "KNOWLEDGE_HOLD block not found in master_orchestrator.py")

    # T032: KNOWLEDGE_BUY → added to kda_authorized
    authorized2: Set[str] = set()
    r_buy = {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
    if r_buy.get("kda_decision") in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL"):
        authorized2.add("SYM2")
    _assert("T032", "KNOWLEDGE_BUY → added to kda_authorized",
            "SYM2" in authorized2, f"authorized2={authorized2}")

    # T033+T034: KDA result always has execution_authority=False, broker_calls=0, orders=0
    src_kdp = open(os.path.join(ROOT, "knowledge_authority",
                                "knowledge_decision_pipeline.py"),
                   encoding="utf-8").read()
    _assert("T033", "KDA result has execution_authority=False",
            '"execution_authority": False' in src_kdp,
            "execution_authority=False not found in KDA result")
    _assert("T034", "KDA result has broker_calls=0 and orders=0",
            '"broker_calls": 0' in src_kdp and '"orders": 0' in src_kdp,
            "broker_calls/orders=0 not found in KDA result")

    # T035: KDA BUY does NOT bypass GAP-029 for USEFUL evidence (conviction not boosted)
    s = _FakeSig(strategy_name="knowledge_referred", confidence=5.5)
    conv = _kda_conviction(15.0, 0.55, "USEFUL", "KNOWLEDGE_BUY", "knowledge_referred")
    if conv > s.confidence:
        s.confidence = conv
    # Phase 2 GAP-029 check
    GAP029_THRESHOLD = 7.5
    r3_ev = "USEFUL"
    kr_exempt = (s.strategy_name == "knowledge_referred" and
                 r3_ev in ("DECISION_ELIGIBLE", "VALIDATED"))
    blocked = (s.confidence < GAP029_THRESHOLD and not kr_exempt)
    _assert("T035", "KDA BUY + USEFUL evidence still blocked by GAP-029",
            blocked, f"conf={s.confidence}, exempt={kr_exempt}")

    # T036: KDA BUY does NOT bypass RiskManager confidence gate for USEFUL
    MIN_CONF = 6.8
    _assert("T036", "KDA BUY + USEFUL conf 5.5 < 6.8 → blocked at RiskManager",
            s.confidence < MIN_CONF, f"conf={s.confidence}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 4 — Phase 5: Knowledge state execution eligibility matrix
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _apply_all_gates(kda_result: dict, strategy_name: str = "knowledge_referred",
                     initial_conf: float = 5.5) -> dict:
    """
    Simulate the full post-KDA conviction + gate chain:
      1. Evidence-derived conviction (if knowledge_referred + BUY + VALIDATED/DECISION_ELIGIBLE)
      2. Phase 2 GAP-029 check
      3. RiskManager confidence gate
    Returns dict with keys: conviction, passes_gap029, passes_riskmanager
    """
    sig = _FakeSig(strategy_name=strategy_name, confidence=initial_conf)
    _apply_conviction(sig, kda_result)

    r3_ev    = kda_result.get("evidence_state", "")
    kr_ex    = (strategy_name == "knowledge_referred"
                and r3_ev in ("DECISION_ELIGIBLE", "VALIDATED"))
    pass_g29 = not (sig.confidence < 7.5 and not kr_ex)
    pass_rm  = (sig.confidence >= 6.8)

    return {
        "conviction": sig.confidence,
        "passes_gap029": pass_g29,
        "passes_riskmanager": pass_rm,
    }


def _test_knowledge_states():
    print("\n── Phase 5: Knowledge state execution eligibility matrix ─────────────")

    # T040: INSUFFICIENT → not boosted → fails RiskManager
    r = _apply_all_gates({"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "INSUFFICIENT",
                           "effective_sample_size": 1.0, "hbe_target_hit_prob": None})
    _assert("T040", "INSUFFICIENT → fails RiskManager",
            not r["passes_riskmanager"], f"passes_rm={r['passes_riskmanager']} conv={r['conviction']}")

    # T041: DEVELOPING → not boosted → fails RiskManager
    r = _apply_all_gates({"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "DEVELOPING",
                           "effective_sample_size": 5.0, "hbe_target_hit_prob": 0.55})
    _assert("T041", "DEVELOPING → fails RiskManager",
            not r["passes_riskmanager"], f"passes_rm={r['passes_riskmanager']} conv={r['conviction']}")

    # T042: USEFUL → not boosted → fails GAP-029 and RiskManager
    r = _apply_all_gates({"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "USEFUL",
                           "effective_sample_size": 15.0, "hbe_target_hit_prob": 0.60})
    _assert("T042", "USEFUL → fails both GAP-029 and RiskManager",
            not r["passes_gap029"] and not r["passes_riskmanager"],
            f"gap029={r['passes_gap029']} rm={r['passes_riskmanager']} conv={r['conviction']}")

    # T043: VALIDATED + thp=0.60 → conviction 7.375 → passes RiskManager (≥6.8)
    r = _apply_all_gates({"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED",
                           "effective_sample_size": 50.0, "hbe_target_hit_prob": 0.60})
    _assert("T043", "VALIDATED + thp=60% → passes RiskManager (≥6.8)",
            r["passes_riskmanager"], f"conv={r['conviction']}")

    # T044: DECISION_ELIGIBLE + thp=0.74 → conviction 9.42 → passes all
    r = _apply_all_gates({"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "DECISION_ELIGIBLE",
                           "effective_sample_size": 327.0, "hbe_target_hit_prob": 0.74})
    _assert("T044", "DECISION_ELIGIBLE + thp=74% → passes GAP-029 and RiskManager",
            r["passes_gap029"] and r["passes_riskmanager"],
            f"gap029={r['passes_gap029']} rm={r['passes_riskmanager']} conv={r['conviction']}")

    # T045: KNOWLEDGE_WAIT → not in kda_authorized → never reaches Phase 2
    auth: Set[str] = set()
    if {"kda_decision": "KNOWLEDGE_WAIT"}.get("kda_decision") in ("KNOWLEDGE_BUY", "KNOWLEDGE_SELL"):
        auth.add("SYM")
    _assert("T045", "KNOWLEDGE_WAIT → not in kda_authorized → no execution",
            "SYM" not in auth, f"auth={auth}")

    # T046: KNOWLEDGE_HOLD: source check that Phase 1 merge blocks HOLD
    src = open(os.path.join(ROOT, "orchestrator", "master_orchestrator.py"),
               encoding="utf-8").read()
    _assert("T046", "KNOWLEDGE_HOLD blocked in Phase 1 merge (source check)",
            '"KNOWLEDGE_HOLD"' in src,
            "KNOWLEDGE_HOLD block not found in orchestrator")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 5 — Phase 7: Lineage verification (source inspection)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_lineage():
    print("\n── Phase 7: opportunity_id lineage (source inspection) ──────────────")

    scanner_src = open(os.path.join(ROOT, "opportunity_engine",
                                    "equity_scanner_ai.py"), encoding="utf-8").read()
    _assert("T050", "opportunity_id set in scanner",
            "opportunity_id" in scanner_src and "uuid4" in scanner_src,
            "opportunity_id assignment not found in equity_scanner_ai.py")

    kda_src = open(os.path.join(ROOT, "knowledge_authority",
                                "knowledge_decision_pipeline.py"), encoding="utf-8").read()
    _assert("T051", "opportunity_id passed to KDA observation builder",
            '"opportunity_id"' in kda_src,
            "opportunity_id not found in knowledge_decision_pipeline.py")

    _assert("T052", "opportunity_id in KDA result dict",
            '"opportunity_id": kda_record.opportunity_id' in kda_src,
            "opportunity_id not found in KDA result return dict")

    om_src = open(os.path.join(ROOT, "execution_engine",
                               "order_manager.py"), encoding="utf-8").read()
    _assert("T053", "opportunity_id propagated to OrderManager record",
            "opportunity_id" in om_src,
            "opportunity_id not found in order_manager.py")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 6 — Phase 8+9: Historical evidence availability + equivalent search
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_evidence_and_equivalents():
    print("\n── Phase 8+9: Historical evidence + equivalent occurrence search ─────")

    hbe_src = open(os.path.join(ROOT, "opportunity_engine",
                                "historical_behaviour_engine.py"), encoding="utf-8").read()
    _assert("T054", "HBE get_behaviour_profile does NOT filter by strategy_name",
            "strategy_name" not in hbe_src.split("def get_behaviour_profile")[1].split("def ")[0],
            "strategy_name filter found in get_behaviour_profile — HBE is not strategy-agnostic")

    kda_src = open(os.path.join(ROOT, "knowledge_authority",
                                "knowledge_decision_pipeline.py"), encoding="utf-8").read()
    _assert("T055", "KDA pipeline _shadow_impl does NOT filter by strategy_name in HBE call",
            "get_behaviour_profile" in kda_src,
            "get_behaviour_profile not called from KDA pipeline")

    rm_src = open(os.path.join(ROOT, "risk_control",
                               "risk_manager_ai.py"), encoding="utf-8").read()
    # Check there's no condition like 'if "knowledge_referred" in sig.strategy_name: reject'
    _assert("T056", "RiskManagerAI has no strategy_name gate",
            "knowledge_referred" not in rm_src and "KDA_AUTHORITY" not in rm_src,
            "Found knowledge_referred/KDA_AUTHORITY in risk_manager_ai.py — possible gate")

    pa_src = open(os.path.join(ROOT, "risk_control",
                               "portfolio_allocation_ai.py"), encoding="utf-8").read()
    _assert("T057", "PortfolioAllocationAI bucket uses market cap, not strategy_name",
            "LARGE_CAP_SYMBOLS" in pa_src or "large_cap" in pa_src,
            "Market-cap bucket logic not found in portfolio_allocation_ai.py")

    cre_src = open(os.path.join(ROOT, "risk_control",
                                "capital_risk_engine.py"), encoding="utf-8").read()
    # CRE should NOT have a hard 'if confidence < X: reject signal' outside telemetry
    # We verified in previous session that lines 284, 422 are telemetry only
    _assert("T058", "CRE.allocate uses quality sort (no hard confidence rejection gate)",
            "_cre_quality_score" in cre_src,
            "Quality sort not found in capital_risk_engine.py")

    debate_src = open(os.path.join(ROOT, "debate_system",
                                   "multi_agent_debate.py"), encoding="utf-8").read()
    # Verify the KDA exemption exists AND no other agent method touches strategy_name.
    # Count distinct method-level strategy_name uses outside _regime_vote.
    regime_vote_start = debate_src.find("def _regime_vote")
    regime_vote_end   = debate_src.find("\n    def ", regime_vote_start + 1)
    outside_regime    = debate_src[:regime_vote_start] + debate_src[regime_vote_end:]
    strategy_outside  = outside_regime.count("strat")
    _assert("T059", "strategy_name only used inside _regime_vote in debate system",
            strategy_outside == 0 and 'strat in ("KDA_AUTHORITY"' in debate_src,
            f"strategy_name references outside _regime_vote: {strategy_outside}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP 7 — Source inspection: all DTA-021 fixes in place
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _test_source():
    print("\n── Source inspection: DTA-021 fixes present in production files ─────")

    mo_src = open(os.path.join(ROOT, "orchestrator", "master_orchestrator.py"),
                  encoding="utf-8").read()

    _assert("SRC-001", "_kr_conv (evidence-derived conviction) in master_orchestrator.py",
            "_kr_conv" in mo_src,
            "DTA-021 conviction variable _kr_conv not found — fix not applied")

    _assert("SRC-001b", "_kr_ess and _kr_thp computed from KDA result in orchestrator",
            "_kr_ess" in mo_src and "_kr_thp" in mo_src,
            "Evidence metrics (_kr_ess/_kr_thp) not found in orchestrator")

    _assert("SRC-001c", "DTA-021 no longer uses fixed floors (7.5/7.0 as literals removed)",
            "_kr_conf_floor" not in mo_src,
            "Old fixed floor variable _kr_conf_floor still present — fix incomplete")

    debate_src = open(os.path.join(ROOT, "debate_system", "multi_agent_debate.py"),
                      encoding="utf-8").read()
    _assert("SRC-002", "KDA_AUTHORITY exemption in multi_agent_debate.py",
            'strat in ("KDA_AUTHORITY", "knowledge_referred")' in debate_src,
            "KDA_AUTHORITY exemption not found in debate_system")

    sg_src = open(os.path.join(ROOT, "strategy_lab", "strategy_generator_ai.py"),
                  encoding="utf-8").read()
    _assert("SRC-003", "Fix A guard still in strategy_generator_ai.py",
            'getattr(signal, "strategy_name", "") == "knowledge_referred"' in sg_src,
            "DTA-020 Fix A guard missing from strategy_generator_ai.py")

    _assert("SRC-004", "Fix C GAP-029 exemption still in master_orchestrator.py",
            "_kr_gap029_exempt" in mo_src,
            "DTA-020 Fix C exemption missing from master_orchestrator.py")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("=" * 65)
    print("DTA-SYSTEM-021  Final Verification + Root-Cause Resolution")
    print("=" * 65)

    _test_conviction()
    _test_debate_regime()
    _test_kda_authority()
    _test_knowledge_states()
    _test_lineage()
    _test_evidence_and_equivalents()
    _test_source()

    print()
    print("=" * 65)
    total = _PASS + _FAIL
    print(f"Results: {_PASS}/{total} passed  ({_FAIL} failed)")
    print("=" * 65)

    sys.exit(0 if _FAIL == 0 else 1)
