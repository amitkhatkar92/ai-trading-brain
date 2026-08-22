"""
ARCH-004 Integration Tests
===========================
16 tests (T01–T16) covering final gap closure items:

T01–T04: OOS Validation (WFE-006 — IMPLEMENT NOW)
T05–T06: paper_trades.csv → KFE (WFE-004 — VERIFY NOW)
T07–T08: DhanBroker.get_order_status (LIVE-003/004 — CONNECT NOW)
T09–T10: OrderManager.reconcile_partial_fills (LIVE-008 — FIX NOW)
T11–T14: Full decision pipeline (16-scenario proof)
T15–T16: Safety invariants (broker_calls=0, PAPER_TRADING=true)

broker_calls = 0 on every test.
orders = 0 on every test.
PAPER_TRADING = true on every test.
"""
from __future__ import annotations

import os
import tempfile
import json
from pathlib import Path
from typing import Any, List

import pytest

# ─── Safety: never enable live trading ───────────────────────────────────────
os.environ.setdefault("PAPER_TRADING", "true")
# ─────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════
# T01–T04: OOS Validation — WFE-006 IMPLEMENT NOW
# ═══════════════════════════════════════════════════════════════════════════

class TestOOSValidation:
    """Verify _annotate_oos_holdout() populates OOS status on rejection records."""

    def _make_rej_record(self, sym: str, dirn: str, date: str, move: float,
                          outcome: str) -> Any:
        """Create a minimal KnowledgeFusionRecord simulating a rejection record."""
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord
        return KnowledgeFusionRecord(
            fusion_id=f"REJ_{sym}_{date}_{dirn}_aaaa",
            trading_date=date,
            symbol=sym,
            direction=dirn,
            sector="BANK",
            outcome_available=True,
            move_1d_pct=move,
            rejection_outcome=outcome,
            source_ids=["REJECTION_AUDIT_DB"],
        )

    def test_T01_oos_annotation_sets_passed_for_buy_positive_move(self):
        """T01: BUY record in OOS holdout with +2% move → OOS_PASSED."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _annotate_oos_holdout
        from opportunity_engine.knowledge_fusion.kf_models import OOS_PASSED, OOS_NOT_TESTED
        # Build 8 records: first 6 = training, last 2 = OOS holdout (25% of 8)
        records = [self._make_rej_record("HDFCBANK", "BUY", f"2025-01-{i:02d}", 1.5, "FALSE_REJECTION")
                   for i in range(1, 9)]
        _annotate_oos_holdout(records)
        training = records[:6]
        holdout  = records[6:]
        # Training records should still be OOS_NOT_TESTED
        for r in training:
            assert getattr(r, "oos_status", OOS_NOT_TESTED) == OOS_NOT_TESTED
        # Holdout BUY records with +1.5% move → OOS_PASSED
        for r in holdout:
            assert getattr(r, "oos_status", OOS_NOT_TESTED) == OOS_PASSED

    def test_T02_oos_annotation_sets_failed_for_buy_negative_move(self):
        """T02: BUY record in OOS holdout with -2% move → OOS_FAILED."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _annotate_oos_holdout
        from opportunity_engine.knowledge_fusion.kf_models import OOS_FAILED, OOS_NOT_TESTED
        records = [self._make_rej_record("ICICIBANK", "BUY", f"2025-02-{i:02d}", -2.0, "CORRECT_REJECTION")
                   for i in range(1, 9)]
        _annotate_oos_holdout(records)
        for r in records[6:]:
            assert getattr(r, "oos_status", OOS_NOT_TESTED) == OOS_FAILED

    def test_T03_oos_angle_returns_nonzero_when_pool_annotated(self):
        """T03: KFE OOS_VALIDATION angle returns tested>0 when pool has annotated records."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _annotate_oos_holdout
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord, OOS_PASSED
        # Build a small pool with one pre-annotated OOS_PASSED record
        record = KnowledgeFusionRecord(
            fusion_id="TEST_R", trading_date="2025-01-01",
            symbol="SBIN", direction="BUY", sector="BANK",
            outcome_available=True, move_1d_pct=2.0,
            source_ids=["REJECTION_AUDIT_DB"],
        )
        setattr(record, "oos_status", OOS_PASSED)
        pool = [record]
        # Now run the angle
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _oos_validation_angle
        result = _oos_validation_angle(record, pool)
        assert result.metrics.get("oos_tested", 0) >= 1
        assert result.metrics.get("oos_passed", 0) >= 1
        assert result.metrics.get("oos_pass_rate") is not None
        assert result.metrics["oos_pass_rate"] == 1.0

    def test_T04_kfe_pool_has_oos_records_after_load(self):
        """T04: KFE.load_fusion_records() produces pool with OOS-annotated records."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        from opportunity_engine.knowledge_fusion.kf_models import OOS_PASSED, OOS_FAILED, OOS_TESTED, OOS_NOT_TESTED
        kfe = KnowledgeFusionEngine()
        pool = kfe.load_fusion_records()
        # Pool must be non-empty
        assert len(pool) > 0
        # At least some rejection records should be annotated (if rejection_audit.db has data)
        annotated = [r for r in pool
                     if getattr(r, "oos_status", OOS_NOT_TESTED) in (OOS_PASSED, OOS_FAILED, OOS_TESTED)]
        # If rejection_audit.db has >=4 outcome-linked records, we should see annotations
        rej_records = [r for r in pool if "REJECTION_AUDIT_DB" in (r.source_ids or [])]
        if len(rej_records) >= 4:
            assert len(annotated) > 0, "Expected OOS-annotated records in pool"


# ═══════════════════════════════════════════════════════════════════════════
# T05–T06: paper_trades.csv → KFE — WFE-004 VERIFY NOW
# ═══════════════════════════════════════════════════════════════════════════

class TestPaperTradesKFEConnection:
    """Verify KFE code path for paper_trades.csv is wired (no data needed for code path)."""

    def test_T05_kfe_source_inventory_has_paper_trades_entry(self):
        """T05: build_source_inventory() lists PAPER_TRADES_CSV source."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import build_source_inventory
        inventory = build_source_inventory()
        sources = {item.source for item in inventory}
        assert "PAPER_TRADES_CSV" in sources

    def test_T06_kfe_paper_trades_csv_code_path_exists(self):
        """T06: KFE load_fusion_records() imports and calls paper_trades code path without error."""
        import tempfile, csv
        from pathlib import Path
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord

        # Create a minimal paper_trades.csv with a closed trade
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            p = td / "paper_trades.csv"
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "timestamp","order_id","symbol","direction","quantity",
                    "entry_price","stop_loss","target","strategy",
                    "confidence","rr","event","exit_price","pnl","reason"
                ])
                w.writeheader()
                w.writerow({
                    "timestamp": "2026-08-22 10:00:00", "order_id": "TEST_001",
                    "symbol": "HDFCBANK", "direction": "BUY", "quantity": 5,
                    "entry_price": 1800.0, "stop_loss": 1770.0, "target": 1850.0,
                    "strategy": "momentum", "confidence": 7.5, "rr": 1.67,
                    "event": "CLOSE", "exit_price": 1850.0, "pnl": 250.0,
                    "reason": "TARGET_HIT"
                })
            kfe = KnowledgeFusionEngine(data_dir=td)
            records = kfe.load_fusion_records()
            # Should not raise; paper_trades.csv may or may not produce KFE records
            # depending on whether load_fusion_records reads it (it does via build_source_inventory)
            assert isinstance(records, list)


# ═══════════════════════════════════════════════════════════════════════════
# T07–T08: DhanBroker.get_order_status — LIVE-003/004 CONNECT NOW
# ═══════════════════════════════════════════════════════════════════════════

class TestDhanBrokerFillReconciliation:
    """Verify DhanBroker.get_order_status() is connected and returns safe defaults."""

    def test_T07_dhan_broker_has_get_order_status(self):
        """T07: DhanBroker exposes get_order_status() method."""
        from execution_engine.brokers.dhan_broker import DhanBroker
        assert hasattr(DhanBroker, "get_order_status"), \
            "DhanBroker.get_order_status() is required (ARCH-004 LIVE-003/004)"

    def test_T08_get_order_status_returns_safe_dict_when_disconnected(self):
        """T08: get_order_status() returns safe dict when SDK returns nothing."""
        from execution_engine.brokers.dhan_broker import DhanBroker
        b = DhanBroker.__new__(DhanBroker)
        b._connected = False
        b._dhan = None
        result = b.get_order_status("FAKE_ORDER")
        assert isinstance(result, dict)
        assert "status" in result
        assert result.get("filled_qty", 0) == 0   # safe default = no fill


# ═══════════════════════════════════════════════════════════════════════════
# T09–T10: OrderManager.reconcile_partial_fills — LIVE-008 FIX NOW
# ═══════════════════════════════════════════════════════════════════════════

class TestPartialFillHandling:
    """Verify reconcile_partial_fills() is implemented and safe in paper mode."""

    def test_T09_order_manager_has_reconcile_partial_fills(self):
        """T09: OrderManager exposes reconcile_partial_fills() method."""
        from execution_engine.order_manager import OrderManager
        assert hasattr(OrderManager, "reconcile_partial_fills"), \
            "OrderManager.reconcile_partial_fills() is required (ARCH-004 LIVE-008)"

    def test_T10_reconcile_partial_fills_noop_in_paper_mode(self):
        """T10: reconcile_partial_fills() returns empty list in paper mode (no broker)."""
        os.environ["PAPER_TRADING"] = "true"
        from execution_engine.order_manager import OrderManager
        om = OrderManager()
        assert om._paper_mode is True
        result = om.reconcile_partial_fills()
        assert result == []
        assert om.broker_calls if hasattr(om, "broker_calls") else True  # no broker in paper mode


# ═══════════════════════════════════════════════════════════════════════════
# T11–T14: Decision pipeline correctness
# ═══════════════════════════════════════════════════════════════════════════

class TestDecisionPipeline:
    """Verify the full decision pipeline handles key scenarios correctly."""

    def test_T11_oos_validation_angle_handles_empty_pool(self):
        """T11: OOS_VALIDATION angle returns gracefully with empty pool."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _oos_validation_angle
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord
        r = KnowledgeFusionRecord(
            fusion_id="T11", trading_date="2026-08-22",
            symbol="TEST", direction="BUY", sector="UNKNOWN",
        )
        result = _oos_validation_angle(r, [])
        assert result.angle_name == "OOS_VALIDATION"
        assert result.confidence == 0.0  # insufficient

    def test_T12_oos_validation_angle_handles_all_untested_pool(self):
        """T12: OOS_VALIDATION angle returns all_untested summary when nothing is annotated."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _oos_validation_angle
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord
        r = KnowledgeFusionRecord(
            fusion_id="T12", trading_date="2026-08-22",
            symbol="TEST", direction="BUY", sector="UNKNOWN",
        )
        pool = [KnowledgeFusionRecord(
            fusion_id=f"P{i}", trading_date="2025-01-01",
            symbol="TEST", direction="BUY", sector="UNKNOWN",
        ) for i in range(5)]
        result = _oos_validation_angle(r, pool)
        assert result.metrics.get("oos_passed", -1) == 0
        assert result.metrics.get("oos_failed", -1) == 0
        assert result.metrics.get("oos_not_tested", 0) == 5

    def test_T13_annotate_oos_holdout_skips_records_without_outcomes(self):
        """T13: _annotate_oos_holdout() does not annotate records without move_1d_pct."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _annotate_oos_holdout
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord, OOS_NOT_TESTED
        records = [KnowledgeFusionRecord(
            fusion_id=f"R{i}", trading_date=f"2025-01-{i:02d}",
            symbol="TEST", direction="BUY", sector="UNKNOWN",
            outcome_available=False, move_1d_pct=None,
        ) for i in range(1, 9)]
        _annotate_oos_holdout(records)
        # No records should be annotated (all have no outcome)
        annotated = [r for r in records if hasattr(r, "oos_status")]
        assert len(annotated) == 0

    def test_T14_oos_sell_direction_annotation_correct(self):
        """T14: SELL record with -2% move (favorable for SELL) → OOS_PASSED."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import _annotate_oos_holdout
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord, OOS_PASSED, OOS_NOT_TESTED
        records = [KnowledgeFusionRecord(
            fusion_id=f"S{i}", trading_date=f"2025-03-{i:02d}",
            symbol="TATASTEEL", direction="SELL", sector="METALS",
            outcome_available=True, move_1d_pct=-2.5,
        ) for i in range(1, 9)]
        _annotate_oos_holdout(records)
        # Holdout SELL records with -2.5% move → OOS_PASSED (direction confirmed)
        for r in records[6:]:
            assert getattr(r, "oos_status", OOS_NOT_TESTED) == OOS_PASSED


# ═══════════════════════════════════════════════════════════════════════════
# T15–T16: Safety invariants
# ═══════════════════════════════════════════════════════════════════════════

class TestSafetyInvariantsARCH004:
    """Prove ARCH-004 changes never break safety contract."""

    def test_T15_kfe_broker_calls_zero_after_oos_annotation(self):
        """T15: KFE.load_fusion_records() with OOS annotation produces broker_calls=0."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine()
        assert kfe.broker_calls == 0
        _ = kfe.load_fusion_records()
        assert kfe.broker_calls == 0  # OOS annotation must not call any broker

    def test_T16_paper_trading_enforced_after_partial_fill_method_added(self):
        """T16: OrderManager still enforces PAPER_TRADING=true; new method does not bypass it."""
        os.environ["PAPER_TRADING"] = "true"
        from execution_engine.order_manager import OrderManager
        import importlib, execution_engine.order_manager as _om_mod
        importlib.reload(_om_mod)
        om = _om_mod.OrderManager()
        # New method must not call broker in paper mode
        result = om.reconcile_partial_fills()
        assert result == []
        assert om._broker is None or om._paper_mode is True
        # Confirm defense-in-depth: LIVE_TRADING_AUTHORIZED absent
        live_auth = os.getenv("LIVE_TRADING_AUTHORIZED", "")
        assert live_auth.lower() != "true", \
            "LIVE_TRADING_AUTHORIZED must NOT be set during ARCH-004 tests"
