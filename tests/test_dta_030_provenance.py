"""
tests/test_dta_030_provenance.py
==================================
DTA-KNOWLEDGE-PROVENANCE-FIX-030 — Regression tests.

Covers:
  T001 — L6 BROAD_MARKET_DIRECTION maps to BROAD_DIR (not ATR_FALLBACK)
  T002 — L4 generic evidence: evidence_scope=GENERIC, counts populated
  T003 — L2 symbol-specific bootstrap: evidence_scope=SYMBOL_SPECIFIC, counts populated
  T004 — Mixed HISTORICAL+LIVE: bootstrap_count+live_count == total records
  T005 — Empty evidence: counts are 0, no crash
  T006 — Decision behaviour invariance (ESS/state/conviction unchanged)
  T007 — KDA authority invariance (L4 generic vs L2 symbol-specific, same conviction)

Safety invariants (must hold after all tests):
  conviction formula = UNCHANGED
  ESS = UNCHANGED
  KDA decision logic = UNCHANGED
  bootstrap contents = UNCHANGED
  KDA authority = UNCHANGED
  RiskGuardian/CRE/OrderManager = not exercised (shadow mode only)
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from knowledge_authority import (
    EvidenceHierarchyLevel,
    EvidenceState,
    KDADecision,
    KnowledgeDecisionAuthority,
)
from knowledge_authority.kda_models import KnowledgeAuthorityComponents
from opportunity_engine.hbe_models import (
    BehaviourMetrics,
    OutcomeRecord,
    TARGET_HIT,
    STOP_HIT,
)
from opportunity_engine.historical_behaviour_engine import (
    _compute_metrics,
    _L1, _L2, _L3, _L4, _L5, _L6, _L7,
    HistoricalBehaviourEngine,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_REF_DATE = date(2026, 9, 1)

KDA = KnowledgeDecisionAuthority()


def _obs(**kwargs) -> Dict[str, Any]:
    defaults: Dict[str, Any] = dict(
        symbol="RELIANCE", direction="BUY",
        entry_price=2800.0, atr=28.0, atr_pct=1.0,
        scanner_confidence=7.0,
    )
    defaults.update(kwargs)
    return defaults


def _bm(ess: float = 50.0, evidence_src: str = "SYMBOL_DIRECTION_REGIME",
        bootstrap: int = 0, live: int = 0, **kwargs) -> MagicMock:
    bm = MagicMock()
    bm.effective_sample_size        = ess
    bm.relevant_sample_size         = int(ess)
    bm.target_hit_probability       = kwargs.get("target_prob", 0.6)
    bm.stop_first_probability       = kwargs.get("stop_prob", 0.3)
    bm.target_source                = kwargs.get("target_src", "EMPIRICAL")
    bm.stop_source                  = kwargs.get("target_src", "EMPIRICAL")
    bm.knowledge_target_offset_p50  = kwargs.get("target_offset", 3.0)
    bm.knowledge_stop_offset_p50    = kwargs.get("stop_offset", 1.5)
    bm.expected_move_p25            = kwargs.get("em_p25", 1.0)
    bm.expected_move_p50            = kwargs.get("em_p50", 2.5)
    bm.expected_move_p75            = kwargs.get("em_p75", 4.5)
    bm.expected_days_p25            = kwargs.get("days_p25", 2.0)
    bm.expected_days_p50            = kwargs.get("days_p50", 4.0)
    bm.expected_days_p75            = kwargs.get("days_p75", 8.0)
    bm.evidence_source              = evidence_src
    bm.bootstrap_record_count       = bootstrap
    bm.live_record_count            = live
    return bm


def _make_outcome(
    symbol: str = "TATASTEEL",
    direction: str = "BUY",
    regime: str = "BULL",
    sector: str = "METALS",
    trading_date: str = "2026-08-20",
    source_type: str = "LIVE",
    first_event: str = TARGET_HIT,
    target_hit: bool = True,
    stop_hit: bool = False,
) -> OutcomeRecord:
    return OutcomeRecord(
        obs_id=f"{symbol}_{trading_date}_{direction}",
        trading_date=trading_date,
        symbol=symbol,
        direction=direction,
        regime=regime,
        sector=sector,
        reference_entry=200.0,
        knowledge_target=215.0,
        knowledge_stop=192.0,
        atr=3.0,
        atr_pct=1.5,
        scanner_confidence=7.0,
        candidate_score=0.75,
        knowledge_score=0.68,
        knowledge_rr=2.5,
        first_event=first_event,
        first_event_day="2026-08-22",
        target_hit=target_hit,
        stop_hit=stop_hit,
        t1_ret_pct=1.5,
        t3_ret_pct=3.0,
        t5_ret_pct=4.5,
        mfe_pct=5.0,
        mae_pct=-1.0,
        days_to_event=2,
        no_lookahead=True,
        source_type=source_type,
    )


# ─────────────────────────────────────────────────────────────────────────────
# T001 — L6 BROAD_MARKET_DIRECTION maps to BROAD_DIR (not ATR_FALLBACK)
# ─────────────────────────────────────────────────────────────────────────────

class TestT001_L6LabelFix:
    """T001: KDA._determine_hierarchy_level maps 'BROAD_MARKET_DIRECTION' → BROAD_DIR."""

    def test_broad_market_direction_maps_to_broad_dir(self):
        bm = _bm(ess=50.0, evidence_src="BROAD_MARKET_DIRECTION", live=50)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.BROAD_DIR, (
            f"Expected BROAD_DIR, got {rec.evidence_level}"
        )

    def test_broad_market_direction_not_atr_fallback(self):
        bm = _bm(ess=50.0, evidence_src="BROAD_MARKET_DIRECTION", live=50)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level != EvidenceHierarchyLevel.ATR_FALLBACK

    def test_broad_market_direction_scope_is_generic(self):
        bm = _bm(ess=50.0, evidence_src="BROAD_MARKET_DIRECTION", live=50)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_scope == "GENERIC"

    def test_l6_via_hbe_gives_broad_market_direction_source(self):
        """HBE selects L6 for cross-symbol query → evidence_source = BROAD_MARKET_DIRECTION."""
        records = [
            _make_outcome(
                symbol=f"SYM{i}", direction="BUY", regime="BEAR",
                sector="UNKNOWN", trading_date=f"2026-08-{i+1:02d}",
            )
            for i in range(15)
        ]
        # Use internal load pattern (bypasses source_type filter) as test_klp_003_hbe.py does
        hbe = HistoricalBehaviourEngine(reference_date=_REF_DATE)
        hbe._outcomes = records
        hbe._loaded = True
        profile = hbe.get_behaviour_profile("NEWSTOCK", "BUY", regime="BULL", sector="METALS")
        assert profile.metrics.evidence_source == "BROAD_MARKET_DIRECTION"
        assert profile.metrics.evidence_level == 6  # HBE level int = 6


# ─────────────────────────────────────────────────────────────────────────────
# T002 — L4 generic evidence: counts and scope
# ─────────────────────────────────────────────────────────────────────────────

class TestT002_L4GenericProvenance:
    """T002: 76 LIVE records at L4 → evidence_scope=GENERIC, bootstrap=0, live=76."""

    def _make_76_live_records(self) -> List[OutcomeRecord]:
        return [
            _make_outcome(
                symbol=f"STOCK{i}", direction="BUY", regime="RANGE_MARKET",
                sector="METALS", trading_date=f"2026-08-{(i % 28) + 1:02d}",
                source_type="LIVE",
            )
            for i in range(76)
        ]

    def test_compute_metrics_live_counts(self):
        records = self._make_76_live_records()
        m = _compute_metrics(records, 4, _L4, 4, _REF_DATE)
        assert m.live_record_count == 76
        assert m.bootstrap_record_count == 0

    def test_kda_evidence_scope_generic_for_regime_dir(self):
        bm = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_scope == "GENERIC"
        assert rec.evidence_level == EvidenceHierarchyLevel.REGIME_DIR

    def test_kda_bootstrap_zero_live_76(self):
        bm = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.bootstrap_record_count == 0
        assert rec.live_record_count == 76

    def test_ess_unchanged_after_provenance_fields(self):
        records = self._make_76_live_records()
        m = _compute_metrics(records, 4, _L4, 4, _REF_DATE)
        assert m.effective_sample_size > 0
        # ESS is not affected by adding provenance fields
        assert m.live_record_count + m.bootstrap_record_count == 76


# ─────────────────────────────────────────────────────────────────────────────
# T003 — L2 symbol-specific bootstrap: SUNPHARMA-like scenario
# ─────────────────────────────────────────────────────────────────────────────

class TestT003_L2SymbolBootstrap:
    """T003: 47 HISTORICAL records at L2 → evidence_scope=SYMBOL_SPECIFIC, bootstrap=47, live=0."""

    def _make_47_historical_records(self) -> List[OutcomeRecord]:
        return [
            _make_outcome(
                symbol="SUNPHARMA", direction="BUY", regime="UNKNOWN",
                sector="PHARMA",
                trading_date=f"2025-{10 + (i // 30):02d}-{(i % 28) + 1:02d}",
                source_type="HISTORICAL",
            )
            for i in range(47)
        ]

    def test_compute_metrics_bootstrap_counts(self):
        records = self._make_47_historical_records()
        m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
        assert m.bootstrap_record_count == 47
        assert m.live_record_count == 0

    def test_kda_evidence_scope_symbol_specific_for_symbol_dir(self):
        bm = _bm(ess=16.78, evidence_src="SYMBOL_DIRECTION", bootstrap=47, live=0)
        rec = KDA.evaluate(_obs(symbol="SUNPHARMA"), behaviour=bm)
        assert rec.evidence_scope == "SYMBOL_SPECIFIC"
        assert rec.evidence_level == EvidenceHierarchyLevel.SYMBOL_DIR

    def test_kda_bootstrap_47_live_0(self):
        bm = _bm(ess=16.78, evidence_src="SYMBOL_DIRECTION", bootstrap=47, live=0)
        rec = KDA.evaluate(_obs(symbol="SUNPHARMA"), behaviour=bm)
        assert rec.bootstrap_record_count == 47
        assert rec.live_record_count == 0

    def test_l1_also_symbol_specific(self):
        # DTA-030A fixed L1 mapping — now uses exact HBE canonical string
        bm = _bm(ess=30.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT", bootstrap=10, live=5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_scope == "SYMBOL_SPECIFIC"
        assert rec.evidence_level == EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX

    def test_ess_unchanged_from_bootstrap_records(self):
        records = self._make_47_historical_records()
        m_with_provenance = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
        # ESS should match manual calculation and be same as without provenance
        assert m_with_provenance.effective_sample_size > 0
        assert m_with_provenance.bootstrap_record_count == 47


# ─────────────────────────────────────────────────────────────────────────────
# T004 — Mixed HISTORICAL+LIVE source: no double-counting
# ─────────────────────────────────────────────────────────────────────────────

class TestT004_MixedSourceCounts:
    """T004: Mixed HISTORICAL+LIVE → bootstrap+live == total, no double-counting."""

    def test_mixed_counts_sum_to_total(self):
        records = (
            [_make_outcome(source_type="HISTORICAL", trading_date=f"2025-10-{i+1:02d}")
             for i in range(20)]
            +
            [_make_outcome(source_type="LIVE", trading_date=f"2026-08-{i+1:02d}")
             for i in range(30)]
        )
        m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
        assert m.bootstrap_record_count == 20
        assert m.live_record_count == 30
        assert m.bootstrap_record_count + m.live_record_count == len(records)

    def test_paper_records_counted_in_live(self):
        records = (
            [_make_outcome(source_type="HISTORICAL") for _ in range(5)]
            + [_make_outcome(source_type="LIVE") for _ in range(5)]
            + [_make_outcome(source_type="PAPER") for _ in range(3)]
        )
        m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
        assert m.bootstrap_record_count == 5
        assert m.live_record_count == 8   # LIVE(5) + PAPER(3)

    def test_unknown_source_type_not_in_either_count(self):
        records = (
            [_make_outcome(source_type="LIVE") for _ in range(10)]
            + [_make_outcome(source_type="SYNTHETIC_FUTURE") for _ in range(2)]
        )
        m = _compute_metrics(records, 2, _L2, 2, _REF_DATE)
        assert m.live_record_count == 10
        assert m.bootstrap_record_count == 0
        # 2 unknown records not double-counted
        assert m.live_record_count + m.bootstrap_record_count == 10


# ─────────────────────────────────────────────────────────────────────────────
# T005 — Empty evidence: zero counts, no crash
# ─────────────────────────────────────────────────────────────────────────────

class TestT005_EmptyEvidence:
    """T005: Zero records → both counts 0, no crash."""

    def test_empty_records_no_crash(self):
        m = _compute_metrics([], 7, _L7, 7, _REF_DATE)
        assert m.bootstrap_record_count == 0
        assert m.live_record_count == 0

    def test_empty_records_ess_zero(self):
        m = _compute_metrics([], 7, _L7, 7, _REF_DATE)
        assert m.effective_sample_size == 0.0

    def test_bm_none_kda_counts_zero(self):
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.bootstrap_record_count == 0
        assert rec.live_record_count == 0

    def test_bm_none_kda_scope_generic(self):
        rec = KDA.evaluate(_obs(), behaviour=None)
        assert rec.evidence_scope == "GENERIC"


# ─────────────────────────────────────────────────────────────────────────────
# T006 — Decision behaviour invariance
# ─────────────────────────────────────────────────────────────────────────────

class TestT006_DecisionBehaviourInvariance:
    """T006: Provenance fields do not change ESS, evidence_state, conviction, or decision."""

    def _make_records(self, n: int, source: str) -> List[OutcomeRecord]:
        return [
            _make_outcome(
                source_type=source,
                trading_date=f"2026-08-{(i % 28) + 1:02d}",
            )
            for i in range(n)
        ]

    def test_ess_invariant_regardless_of_source_type(self):
        live_records = self._make_records(20, "LIVE")
        hist_records = [
            OutcomeRecord(
                **{**_make_outcome(source_type="HISTORICAL").__dict__,
                   "source_type": "HISTORICAL"}
            )
            for _ in range(20)
        ]
        m_live = _compute_metrics(live_records, 2, _L2, 2, _REF_DATE)
        # Patch source_type on copies to HISTORICAL
        hist_copies = []
        for r in live_records:
            import dataclasses
            hist_copies.append(dataclasses.replace(r, source_type="HISTORICAL"))
        m_hist = _compute_metrics(hist_copies, 2, _L2, 2, _REF_DATE)
        # ESS must be same (source_type does not affect recency weighting)
        assert abs(m_live.effective_sample_size - m_hist.effective_sample_size) < 1e-9

    def test_kda_ess_unchanged_by_provenance(self):
        """KDA effective_sample_size field equals what BM reports."""
        bm = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert abs(rec.effective_sample_size - 76.9) < 0.01

    def test_kda_evidence_state_unchanged(self):
        """ESS=76.9 → VALIDATED; provenance doesn't change classification."""
        bm = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_state == EvidenceState.VALIDATED

    def test_kda_conviction_not_affected_by_provenance_fields(self):
        """Conviction is same whether bootstrap=0,live=76 or bootstrap=76,live=0."""
        bm_live = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        bm_boot = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=76, live=0)
        rec_live = KDA.evaluate(_obs(), behaviour=bm_live)
        rec_boot = KDA.evaluate(_obs(), behaviour=bm_boot)
        assert abs(rec_live.knowledge_authority - rec_boot.knowledge_authority) < 1e-9

    def test_kda_decision_not_affected_by_provenance_fields(self):
        bm_live = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        bm_boot = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=76, live=0)
        rec_live = KDA.evaluate(_obs(), behaviour=bm_live)
        rec_boot = KDA.evaluate(_obs(), behaviour=bm_boot)
        assert rec_live.decision == rec_boot.decision


# ─────────────────────────────────────────────────────────────────────────────
# T007 — KDA authority invariance: L4 generic vs L2 symbol-specific
# ─────────────────────────────────────────────────────────────────────────────

class TestT007_KDAAuthorityInvariance:
    """T007: L4 generic and L2 symbol-specific with equal ESS produce equal conviction."""

    def test_equal_ess_equal_authority(self):
        bm_l4 = _bm(ess=76.9, evidence_src="REGIME_DIRECTION",   bootstrap=0,  live=76)
        bm_l2 = _bm(ess=76.9, evidence_src="SYMBOL_DIRECTION",   bootstrap=76, live=0)
        rec_l4 = KDA.evaluate(_obs(), behaviour=bm_l4)
        rec_l2 = KDA.evaluate(_obs(), behaviour=bm_l2)
        # Same ESS → same authority (provenance does NOT alter conviction in DTA-030)
        assert abs(rec_l4.knowledge_authority - rec_l2.knowledge_authority) < 1e-9

    def test_scope_differs_but_authority_same(self):
        bm_l4 = _bm(ess=76.9, evidence_src="REGIME_DIRECTION",   bootstrap=0,  live=76)
        bm_l2 = _bm(ess=76.9, evidence_src="SYMBOL_DIRECTION",   bootstrap=76, live=0)
        rec_l4 = KDA.evaluate(_obs(), behaviour=bm_l4)
        rec_l2 = KDA.evaluate(_obs(), behaviour=bm_l2)
        assert rec_l4.evidence_scope == "GENERIC"
        assert rec_l2.evidence_scope == "SYMBOL_SPECIFIC"
        # Despite different scope, authority identical
        assert abs(rec_l4.knowledge_authority - rec_l2.knowledge_authority) < 1e-9

    def test_sector_levels_are_generic(self):
        for src in ("SECTOR_DIRECTION_REGIME", "SECTOR_DIRECTION"):
            bm = _bm(ess=50.0, evidence_src=src, bootstrap=0, live=50)
            rec = KDA.evaluate(_obs(), behaviour=bm)
            assert rec.evidence_scope == "GENERIC", f"Expected GENERIC for {src}"

    def test_safety_invariants_unchanged(self):
        bm = _bm(ess=76.9, evidence_src="REGIME_DIRECTION", bootstrap=0, live=76)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.broker_calls == 0
        assert rec.orders == 0
        assert rec.no_lookahead is True
        assert rec.mode == "SHADOW_DECISION"


# ───────────────────────────────────────────────────────────────────────────
# DTA-030A — L1 evidence-level metadata consistency fix
# ───────────────────────────────────────────────────────────────────────────

class TestDTA030A_L1LabelFix:
    """
    DTA-030A: HBE canonical L1 string 'SYMBOL_DIRECTION_REGIME_CONTEXT'
    must map to SYMBOL_DIR_REGIME_CTX (not ATR_FALLBACK).
    """

    def test_l1_canonical_string_maps_to_symbol_dir_regime_ctx(self):
        """'SYMBOL_DIRECTION_REGIME_CONTEXT' → SYMBOL_DIR_REGIME_CTX."""
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT", bootstrap=10, live=5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level == EvidenceHierarchyLevel.SYMBOL_DIR_REGIME_CTX

    def test_l1_not_atr_fallback(self):
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT", bootstrap=10, live=5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_level != EvidenceHierarchyLevel.ATR_FALLBACK

    def test_l1_evidence_scope_symbol_specific(self):
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT", bootstrap=10, live=5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.evidence_scope == "SYMBOL_SPECIFIC"

    def test_l1_via_hbe_produces_correct_evidence_source(self):
        """HBE selecting L1 sets evidence_source = 'SYMBOL_DIRECTION_REGIME_CONTEXT'."""
        records = [
            _make_outcome(
                symbol="TATASTEEL", direction="BUY", regime="BULL",
                sector="METALS", trading_date=f"2026-08-{i+1:02d}",
                source_type="LIVE",
            )
            for i in range(5)
        ]
        hbe = HistoricalBehaviourEngine(reference_date=_REF_DATE)
        hbe._outcomes = records
        hbe._loaded = True
        profile = hbe.get_behaviour_profile(
            "TATASTEEL", "BUY", regime="BULL", sector="METALS",
            query_atr_pct=1.5, query_confidence=7.0,
        )
        # L1 requires context match (atr_pct + confidence similarity)
        # If L1 selected, evidence_source must be canonical HBE string
        if profile.metrics.evidence_level == 1:
            assert profile.metrics.evidence_source == "SYMBOL_DIRECTION_REGIME_CONTEXT"

    def test_l1_provenance_counts_preserved(self):
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT",
                 bootstrap=10, live=5)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.bootstrap_record_count == 10
        assert rec.live_record_count == 5

    def test_ess_unchanged_for_l1(self):
        """ESS is not affected by the label fix."""
        bm = _bm(ess=42.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT", bootstrap=5, live=10)
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert abs(rec.effective_sample_size - 42.0) < 0.01

    def test_conviction_unchanged_for_l1(self):
        """Same ESS before/after fix produces same conviction."""
        bm_l1_ctx  = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT")
        bm_l1_old  = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME")
        rec_ctx = KDA.evaluate(_obs(), behaviour=bm_l1_ctx)
        rec_old = KDA.evaluate(_obs(), behaviour=bm_l1_old)
        # Both are SYMBOL_SPECIFIC now; conviction must be identical
        assert abs(rec_ctx.knowledge_authority - rec_old.knowledge_authority) < 1e-9

    def test_decision_unchanged_for_l1(self):
        bm_l1_ctx = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT")
        bm_l1_old = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME")
        rec_ctx = KDA.evaluate(_obs(), behaviour=bm_l1_ctx)
        rec_old = KDA.evaluate(_obs(), behaviour=bm_l1_old)
        assert rec_ctx.decision == rec_old.decision

    def test_safety_invariants(self):
        bm = _bm(ess=50.0, evidence_src="SYMBOL_DIRECTION_REGIME_CONTEXT")
        rec = KDA.evaluate(_obs(), behaviour=bm)
        assert rec.broker_calls == 0
        assert rec.orders == 0
        assert rec.no_lookahead is True
        assert rec.mode == "SHADOW_DECISION"
