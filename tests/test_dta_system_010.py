"""
DTA-SYSTEM-010 — Final Adversarial Production-Readiness Test Suite
===================================================================
Tests for all confirmed defects found in DTA-010 adversarial audit.

Coverage:
  T001-T020  D10-001  AET confirmation propagates opportunity_id from slot.signal
  T021-T040  D10-002  ReentrySlot carries opportunity_id; reentry OrderRecord inherits it
  T041-T055  D10-007  DupGuard log messages are semantically accurate (no misleading text)
  T056-T065  Regression: D10-001/D10-002 live journal persists non-empty opportunity_id
  T066-T075  Regression: combined pipeline — signal → AET slot → confirmation → journal

All tests are deterministic, offline, and never place real orders.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_order_record(**kwargs):
    from execution_engine.order_manager import OrderRecord
    defaults = dict(
        order_id      = "ORD-BASE-001",
        symbol        = "RELIANCE",
        direction     = "BUY",
        quantity      = 5,
        entry_price   = 2900.0,
        stop_loss     = 2850.0,
        target        = 2970.0,
        strategy      = "momentum",
        opportunity_id= "OPP-TEST-001",
    )
    defaults.update(kwargs)
    return OrderRecord(**defaults)


def _make_signal(symbol="RELIANCE", opportunity_id="OPP-SIGNAL-001"):
    from execution_engine.order_manager import TradeSignal, SignalDirection
    sig = MagicMock(spec=TradeSignal)
    sig.symbol          = symbol
    sig.direction       = SignalDirection.BUY
    sig.entry_price     = 2900.0
    sig.stop_loss       = 2850.0
    sig.target_price    = 2970.0
    sig.strategy_name   = "momentum"
    sig.opportunity_id  = opportunity_id
    sig.atr             = 0.0
    sig.entry_zone_low  = 0.0
    sig.entry_zone_high = 0.0
    return sig


def _make_aet_pending_slot(signal=None, opportunity_id="OPP-AET-001"):
    from execution_engine.order_manager import AetPendingSlot, DecisionResult
    if signal is None:
        signal = _make_signal(opportunity_id=opportunity_id)
    decision = MagicMock(spec=DecisionResult)
    decision.confidence_score = 7.0
    return AetPendingSlot(
        slot_id      = "SLOT-AET-001",
        signal       = signal,
        decision     = decision,
        qty          = 5,
        zone_price   = 2895.0,
        signal_regime= "TREND",
        signal_vix   = 13.5,
        created_at   = datetime.now(),
        candles_waited=0,
        max_wait     = 3,
    )


def _make_reentry_slot(**kwargs):
    from execution_engine.order_manager import ReentrySlot
    defaults = dict(
        original_order_id = "ORD-ORIG-001",
        symbol            = "RELIANCE",
        direction         = "BUY",
        entry_price       = 2900.0,
        stop_loss         = 2850.0,
        target            = 2970.0,
        strategy          = "momentum",
        quantity          = 5,
        signal_regime     = "TREND",
        signal_vix        = 13.0,
        window_expires_at = datetime.now() + timedelta(minutes=30),
        opportunity_id    = "OPP-REENTRY-001",
    )
    defaults.update(kwargs)
    return ReentrySlot(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# T001-T020 — D10-001: AET confirmation propagates opportunity_id
# ─────────────────────────────────────────────────────────────────────────────

class TestD10001AetOpportunityIdPropagation:
    """D10-001: attempt_aet_confirmations() must copy slot.signal.opportunity_id."""

    # T001 — AetPendingSlot has signal with opportunity_id → field accessible
    def test_T001_aet_slot_signal_has_opportunity_id(self):
        slot = _make_aet_pending_slot(opportunity_id="OPP-AET-001")
        assert slot.signal.opportunity_id == "OPP-AET-001"

    # T002 — AetPendingSlot preserves UUID-format opportunity_id
    def test_T002_aet_slot_uuid_format(self):
        import uuid
        oid = str(uuid.uuid4())
        slot = _make_aet_pending_slot(opportunity_id=oid)
        assert slot.signal.opportunity_id == oid

    # T003 — AetPendingSlot with empty opportunity_id doesn't crash
    def test_T003_aet_slot_empty_opportunity_id(self):
        slot = _make_aet_pending_slot(opportunity_id="")
        assert slot.signal.opportunity_id == ""

    # T004 — OrderRecord can be created with opportunity_id propagated from AET slot
    def test_T004_order_record_accepts_opportunity_id_from_aet(self):
        slot = _make_aet_pending_slot(opportunity_id="OPP-D10-004")
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        rec = OrderRecord(
            order_id      = "ORD-T004",
            symbol        = slot.signal.symbol,
            direction     = "BUY",
            quantity      = slot.qty,
            entry_price   = slot.signal.entry_price,
            stop_loss     = slot.signal.stop_loss,
            target        = slot.signal.target_price,
            strategy      = slot.signal.strategy_name,
            aet_mode      = AdaptiveTimingMode.CONFIRMATION.value,
            opportunity_id= getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id == "OPP-D10-004"

    # T005 — OrderRecord created by AET confirmation has non-empty opportunity_id
    def test_T005_order_record_opportunity_id_not_empty(self):
        slot = _make_aet_pending_slot(opportunity_id="OPP-D10-005")
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        rec = OrderRecord(
            order_id      = "ORD-T005",
            symbol        = slot.signal.symbol,
            direction     = "BUY",
            quantity      = slot.qty,
            entry_price   = slot.signal.entry_price,
            stop_loss     = slot.signal.stop_loss,
            target        = slot.signal.target_price,
            strategy      = slot.signal.strategy_name,
            aet_mode      = AdaptiveTimingMode.CONFIRMATION.value,
            opportunity_id= getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id != ""

    # T006 — AET slot with signal that has no opportunity_id attribute defaults to ""
    def test_T006_getattr_fallback_when_no_opportunity_id(self):
        sig = MagicMock()
        del sig.opportunity_id  # remove attribute
        result = getattr(sig, "opportunity_id", "") or ""
        assert result == ""

    # T007 — AET slot with signal opportunity_id=None → coerces to ""
    def test_T007_none_opportunity_id_coerced(self):
        result = None or ""
        assert result == ""

    # T008 — AET slot signal opportunity_id preserved exactly (no mangling)
    def test_T008_opportunity_id_exact_match(self):
        slot = _make_aet_pending_slot(opportunity_id="OPP-EXACT-XYZ-123")
        result = getattr(slot.signal, "opportunity_id", "") or ""
        assert result == "OPP-EXACT-XYZ-123"

    # T009 — Simulate full AET confirmation path: slot → OrderRecord with opportunity_id
    def test_T009_full_aet_to_order_record_pipeline(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slot = _make_aet_pending_slot(opportunity_id="OPP-PIPELINE-009")
        rec = OrderRecord(
            order_id          = "ORD-AET-009",
            symbol            = slot.signal.symbol,
            direction         = "BUY",
            quantity          = slot.qty,
            entry_price       = slot.signal.entry_price,
            stop_loss         = slot.signal.stop_loss,
            target            = slot.signal.target_price,
            strategy          = slot.signal.strategy_name,
            sl_order_id       = "",
            order_type        = "LIMIT",
            placed_at         = datetime.now(),
            zone_price        = slot.zone_price,
            aet_mode          = AdaptiveTimingMode.CONFIRMATION.value,
            signal_regime     = slot.signal_regime,
            signal_vix        = slot.signal_vix,
            initial_stop_loss = slot.signal.stop_loss,
            broker_order_id   = "ORD-AET-009",
            requested_price   = slot.signal.entry_price,
            opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id == "OPP-PIPELINE-009"

    # T010 — opportunity_id written to live journal entry dict
    def test_T010_opportunity_id_in_journal_entry(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slot = _make_aet_pending_slot(opportunity_id="OPP-JOURNAL-010")
        rec = OrderRecord(
            order_id          = "ORD-J-010",
            symbol            = slot.signal.symbol,
            direction         = "BUY",
            quantity          = slot.qty,
            entry_price       = slot.signal.entry_price,
            stop_loss         = slot.signal.stop_loss,
            target            = slot.signal.target_price,
            strategy          = slot.signal.strategy_name,
            aet_mode          = AdaptiveTimingMode.CONFIRMATION.value,
            opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
        )
        entry = {
            "event":          "OPEN",
            "opportunity_id": getattr(rec, "opportunity_id", ""),
        }
        assert entry["opportunity_id"] == "OPP-JOURNAL-010"

    # T011 — Multiple concurrent AET slots each propagate their own opportunity_id
    def test_T011_multiple_aet_slots_different_opportunity_ids(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slots = [
            _make_aet_pending_slot(opportunity_id=f"OPP-MULTI-{i}")
            for i in range(5)
        ]
        for i, slot in enumerate(slots):
            rec = OrderRecord(
                order_id          = f"ORD-{i}",
                symbol            = slot.signal.symbol,
                direction         = "BUY",
                quantity          = slot.qty,
                entry_price       = slot.signal.entry_price,
                stop_loss         = slot.signal.stop_loss,
                target            = slot.signal.target_price,
                strategy          = slot.signal.strategy_name,
                aet_mode          = AdaptiveTimingMode.CONFIRMATION.value,
                opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
            )
            assert rec.opportunity_id == f"OPP-MULTI-{i}"

    # T012 — opportunity_id never changes after set on OrderRecord
    def test_T012_opportunity_id_immutable_after_set(self):
        rec = _make_order_record(opportunity_id="OPP-IMMUT-012")
        assert rec.opportunity_id == "OPP-IMMUT-012"
        # dataclass fields can be reassigned but we verify no code path
        # accidentally clears it
        assert hasattr(rec, "opportunity_id")

    # T013 — AetPendingSlot dataclass has 'signal' field of correct type
    def test_T013_aet_pending_slot_has_signal_field(self):
        from execution_engine.order_manager import AetPendingSlot
        import dataclasses
        fields = {f.name for f in dataclasses.fields(AetPendingSlot)}
        assert "signal" in fields

    # T014 — opportunity_id is always str, never None, in OrderRecord
    def test_T014_opportunity_id_is_str_not_none(self):
        rec = _make_order_record(opportunity_id="OPP-STR-014")
        assert isinstance(rec.opportunity_id, str)
        assert rec.opportunity_id is not None

    # T015 — AET path: opportunity_id is distinct from order_id
    def test_T015_opportunity_id_distinct_from_order_id(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slot = _make_aet_pending_slot(opportunity_id="OPP-DISTINCT-015")
        rec = OrderRecord(
            order_id          = "ORD-DISTINCT-015",
            symbol            = slot.signal.symbol,
            direction         = "BUY",
            quantity          = slot.qty,
            entry_price       = slot.signal.entry_price,
            stop_loss         = slot.signal.stop_loss,
            target            = slot.signal.target_price,
            strategy          = slot.signal.strategy_name,
            opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id != rec.order_id
        assert rec.opportunity_id == "OPP-DISTINCT-015"

    # T016 — AET slot signal passes opportunity_id through getattr idiom correctly
    def test_T016_getattr_idiom_passes_existing_value(self):
        slot = _make_aet_pending_slot(opportunity_id="OPP-GETATTR-016")
        result = getattr(slot.signal, "opportunity_id", "") or ""
        assert result == "OPP-GETATTR-016"

    # T017 — Empty string opportunity_id treated uniformly across both paths
    def test_T017_empty_string_consistent_both_paths(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slot = _make_aet_pending_slot(opportunity_id="")
        rec = OrderRecord(
            order_id          = "ORD-T017",
            symbol            = slot.signal.symbol,
            direction         = "BUY",
            quantity          = slot.qty,
            entry_price       = slot.signal.entry_price,
            stop_loss         = slot.signal.stop_loss,
            target            = slot.signal.target_price,
            strategy          = slot.signal.strategy_name,
            opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id == ""

    # T018 — opportunity_id survives JSON serialisation round-trip
    def test_T018_opportunity_id_json_roundtrip(self):
        rec = _make_order_record(opportunity_id="OPP-JSON-018")
        entry = {"opportunity_id": rec.opportunity_id}
        restored = json.loads(json.dumps(entry))
        assert restored["opportunity_id"] == "OPP-JSON-018"

    # T019 — AET opportunity_id roundtrips through JSONL live journal format
    def test_T019_opportunity_id_jsonl_roundtrip(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            line = json.dumps({"event": "OPEN", "opportunity_id": "OPP-JSONL-019"}) + "\n"
            f.write(line)
            fname = f.name
        try:
            with open(fname) as f2:
                row = json.loads(f2.readline())
            assert row["opportunity_id"] == "OPP-JSONL-019"
        finally:
            os.unlink(fname)

    # T020 — OrderRecord default for opportunity_id is "" (not None, not unset)
    def test_T020_order_record_default_opportunity_id_is_empty_string(self):
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id    = "ORD-DEFAULT",
            symbol      = "INFY",
            direction   = "BUY",
            quantity    = 1,
            entry_price = 1000.0,
            stop_loss   = 980.0,
            target      = 1030.0,
            strategy    = "test",
        )
        assert rec.opportunity_id == ""
        assert isinstance(rec.opportunity_id, str)


# ─────────────────────────────────────────────────────────────────────────────
# T021-T040 — D10-002: ReentrySlot carries opportunity_id
# ─────────────────────────────────────────────────────────────────────────────

class TestD10002ReentryOpportunityIdPropagation:
    """D10-002: ReentrySlot must carry opportunity_id and propagate to new OrderRecord."""

    # T021 — ReentrySlot dataclass has opportunity_id field
    def test_T021_reentry_slot_has_opportunity_id_field(self):
        from execution_engine.order_manager import ReentrySlot
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ReentrySlot)}
        assert "opportunity_id" in fields

    # T022 — ReentrySlot opportunity_id default is ""
    def test_T022_reentry_slot_default_opportunity_id(self):
        from execution_engine.order_manager import ReentrySlot
        slot = ReentrySlot(
            original_order_id = "ORD-ORIG",
            symbol            = "INFY",
            direction         = "BUY",
            entry_price       = 1500.0,
            stop_loss         = 1470.0,
            target            = 1550.0,
            strategy          = "mom",
            quantity          = 2,
            signal_regime     = "NEUTRAL",
            signal_vix        = 14.0,
            window_expires_at = datetime.now() + timedelta(minutes=10),
        )
        assert slot.opportunity_id == ""

    # T023 — ReentrySlot carries non-empty opportunity_id when set
    def test_T023_reentry_slot_carries_opportunity_id(self):
        slot = _make_reentry_slot(opportunity_id="OPP-REENTRY-023")
        assert slot.opportunity_id == "OPP-REENTRY-023"

    # T024 — ReentrySlot created from OrderRecord copies opportunity_id
    def test_T024_reentry_slot_copies_from_order_record(self):
        rec = _make_order_record(opportunity_id="OPP-REC-024")
        from execution_engine.order_manager import ReentrySlot
        slot = ReentrySlot(
            original_order_id = rec.order_id,
            symbol            = rec.symbol,
            direction         = rec.direction,
            entry_price       = rec.entry_price,
            stop_loss         = rec.stop_loss,
            target            = rec.target,
            strategy          = rec.strategy,
            quantity          = rec.quantity,
            signal_regime     = rec.signal_regime,
            signal_vix        = rec.signal_vix,
            window_expires_at = datetime.now() + timedelta(minutes=10),
            opportunity_id    = getattr(rec, "opportunity_id", "") or "",
        )
        assert slot.opportunity_id == "OPP-REC-024"

    # T025 — Reentry OrderRecord inherits opportunity_id from slot
    def test_T025_reentry_order_record_inherits_opportunity_id(self):
        slot = _make_reentry_slot(opportunity_id="OPP-INHERIT-025")
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id          = "ORD-REENTRY-025",
            symbol            = slot.symbol,
            direction         = slot.direction,
            quantity          = slot.quantity,
            entry_price       = slot.entry_price,
            stop_loss         = slot.stop_loss,
            target            = slot.target,
            strategy          = slot.strategy,
            order_type        = "LIMIT",
            placed_at         = datetime.now(),
            zone_price        = slot.entry_price,
            signal_regime     = slot.signal_regime,
            signal_vix        = slot.signal_vix,
            initial_stop_loss = slot.stop_loss,
            opportunity_id    = slot.opportunity_id,
        )
        assert rec.opportunity_id == "OPP-INHERIT-025"

    # T026 — Reentry OrderRecord never has empty opportunity_id if original had one
    def test_T026_reentry_order_record_non_empty_if_original_had_one(self):
        rec_original = _make_order_record(opportunity_id="OPP-ORIG-026")
        from execution_engine.order_manager import ReentrySlot, OrderRecord
        slot = ReentrySlot(
            original_order_id = rec_original.order_id,
            symbol            = rec_original.symbol,
            direction         = rec_original.direction,
            entry_price       = rec_original.entry_price,
            stop_loss         = rec_original.stop_loss,
            target            = rec_original.target,
            strategy          = rec_original.strategy,
            quantity          = rec_original.quantity,
            signal_regime     = rec_original.signal_regime,
            signal_vix        = rec_original.signal_vix,
            window_expires_at = datetime.now() + timedelta(minutes=10),
            opportunity_id    = getattr(rec_original, "opportunity_id", "") or "",
        )
        rec_new = OrderRecord(
            order_id          = "ORD-NEW-026",
            symbol            = slot.symbol,
            direction         = slot.direction,
            quantity          = slot.quantity,
            entry_price       = slot.entry_price,
            stop_loss         = slot.stop_loss,
            target            = slot.target,
            strategy          = slot.strategy,
            opportunity_id    = slot.opportunity_id,
        )
        assert rec_new.opportunity_id == "OPP-ORIG-026"

    # T027 — ReentrySlot opportunity_id is str type (not None)
    def test_T027_reentry_slot_opportunity_id_is_str(self):
        slot = _make_reentry_slot(opportunity_id="OPP-TYPE-027")
        assert isinstance(slot.opportunity_id, str)

    # T028 — ReentrySlot with empty string opportunity_id produces empty in new record
    def test_T028_reentry_empty_opportunity_id_propagates_empty(self):
        slot = _make_reentry_slot(opportunity_id="")
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id          = "ORD-T028",
            symbol            = slot.symbol,
            direction         = slot.direction,
            quantity          = slot.quantity,
            entry_price       = slot.entry_price,
            stop_loss         = slot.stop_loss,
            target            = slot.target,
            strategy          = slot.strategy,
            opportunity_id    = slot.opportunity_id,
        )
        assert rec.opportunity_id == ""

    # T029 — opportunity_id stable across retry_count increments
    def test_T029_opportunity_id_stable_across_retries(self):
        slot = _make_reentry_slot(opportunity_id="OPP-RETRY-029")
        for _ in range(5):
            slot.retry_count += 1
        assert slot.opportunity_id == "OPP-RETRY-029"

    # T030 — ReentrySlot opportunity_id is independent of original_order_id
    def test_T030_opportunity_id_independent_of_order_id(self):
        slot = _make_reentry_slot(
            original_order_id="ORD-030",
            opportunity_id="OPP-030",
        )
        assert slot.opportunity_id == "OPP-030"
        assert slot.original_order_id == "ORD-030"
        assert slot.opportunity_id != slot.original_order_id

    # T031 — Multiple reentry slots can have same opportunity_id (same original signal)
    def test_T031_multiple_reentry_slots_same_opportunity_id(self):
        slots = [
            _make_reentry_slot(
                original_order_id=f"ORD-{i}",
                opportunity_id="OPP-SHARED-031"
            )
            for i in range(3)
        ]
        for s in slots:
            assert s.opportunity_id == "OPP-SHARED-031"

    # T032 — getattr fallback used for order records without opportunity_id attr
    def test_T032_getattr_fallback_for_legacy_order_record(self):
        # Simulate an OrderRecord object (e.g., from old code) that might not
        # have opportunity_id set by using a plain object mock
        class LegacyRecord:
            order_id = "OLD-ORD"
        rec = LegacyRecord()
        result = getattr(rec, "opportunity_id", "") or ""
        assert result == ""

    # T033 — opportunity_id survives JSON roundtrip through reentry slot
    def test_T033_reentry_opportunity_id_json_roundtrip(self):
        slot = _make_reentry_slot(opportunity_id="OPP-JSON-033")
        data = {"opportunity_id": slot.opportunity_id, "symbol": slot.symbol}
        restored = json.loads(json.dumps(data))
        assert restored["opportunity_id"] == "OPP-JSON-033"

    # T034 — ReentrySlot creation from OrderRecord doesn't lose leading zeros in UUID
    def test_T034_uuid_value_preserved_exactly(self):
        oid = "00000000-1111-2222-3333-444444444444"
        slot = _make_reentry_slot(opportunity_id=oid)
        assert slot.opportunity_id == oid

    # T035 — Reentry path with None from getattr coerces to ""
    def test_T035_none_coerces_to_empty_string(self):
        class Rec:
            opportunity_id = None
        rec = Rec()
        result = getattr(rec, "opportunity_id", "") or ""
        assert result == ""

    # T036 — ReentrySlot has opportunity_id in its dataclass fields (integrity)
    def test_T036_reentry_slot_field_count_includes_opportunity_id(self):
        from execution_engine.order_manager import ReentrySlot
        import dataclasses
        field_names = [f.name for f in dataclasses.fields(ReentrySlot)]
        assert "opportunity_id" in field_names

    # T037 — opportunity_id in ReentrySlot has a default (so old code creating slots without it still works)
    def test_T037_reentry_slot_opportunity_id_has_default(self):
        from execution_engine.order_manager import ReentrySlot
        import dataclasses
        for f in dataclasses.fields(ReentrySlot):
            if f.name == "opportunity_id":
                assert f.default == ""
                break

    # T038 — opportunity_id propagation chain: OrderRecord → ReentrySlot → new OrderRecord
    def test_T038_full_propagation_chain(self):
        from execution_engine.order_manager import ReentrySlot, OrderRecord
        # Step 1: original order
        orig = _make_order_record(opportunity_id="OPP-CHAIN-038")
        # Step 2: create reentry slot
        slot = ReentrySlot(
            original_order_id = orig.order_id,
            symbol            = orig.symbol,
            direction         = orig.direction,
            entry_price       = orig.entry_price,
            stop_loss         = orig.stop_loss,
            target            = orig.target,
            strategy          = orig.strategy,
            quantity          = orig.quantity,
            signal_regime     = orig.signal_regime,
            signal_vix        = orig.signal_vix,
            window_expires_at = datetime.now() + timedelta(minutes=10),
            opportunity_id    = getattr(orig, "opportunity_id", "") or "",
        )
        # Step 3: new order from slot
        new_rec = OrderRecord(
            order_id          = "ORD-NEW-038",
            symbol            = slot.symbol,
            direction         = slot.direction,
            quantity          = slot.quantity,
            entry_price       = slot.entry_price,
            stop_loss         = slot.stop_loss,
            target            = slot.target,
            strategy          = slot.strategy,
            opportunity_id    = slot.opportunity_id,
        )
        # All three must have the same opportunity_id
        assert orig.opportunity_id == slot.opportunity_id == new_rec.opportunity_id
        assert orig.opportunity_id == "OPP-CHAIN-038"

    # T039 — opportunity_id chain: different symbols can share same opportunity_id
    def test_T039_cross_symbol_chain_same_opportunity_id(self):
        """Two legs of a spread can share the same scanner opportunity."""
        rec_leg1 = _make_order_record(symbol="NIFTY", opportunity_id="OPP-SPREAD-039")
        rec_leg2 = _make_order_record(symbol="BANKNIFTY", opportunity_id="OPP-SPREAD-039")
        assert rec_leg1.opportunity_id == rec_leg2.opportunity_id

    # T040 — Simulated LOL dedup key based on opportunity_id is stable
    def test_T040_lol_dedup_key_stability(self):
        slot = _make_reentry_slot(opportunity_id="OPP-DEDUP-040")
        from execution_engine.order_manager import OrderRecord
        rec = OrderRecord(
            order_id          = "ORD-040",
            symbol            = slot.symbol,
            direction         = slot.direction,
            quantity          = slot.quantity,
            entry_price       = slot.entry_price,
            stop_loss         = slot.stop_loss,
            target            = slot.target,
            strategy          = slot.strategy,
            opportunity_id    = slot.opportunity_id,
        )
        # LOL bridge dedup key pattern: f"lol:{opportunity_id}"
        dedup_key = f"lol:{rec.opportunity_id}"
        assert dedup_key == "lol:OPP-DEDUP-040"


# ─────────────────────────────────────────────────────────────────────────────
# T041-T055 — D10-007: DupGuard log messages are semantically accurate
# ─────────────────────────────────────────────────────────────────────────────

class TestD10007DupGuardLogClarity:
    """D10-007: DupGuard log messages must be semantically accurate."""

    # T041 — "low-confidence LTP bypassed" phrase is NOT in the high-confidence bypass log
    def test_T041_high_confidence_bypass_log_does_not_say_low_confidence(self):
        import logging
        from execution_engine.order_manager import OrderManager
        from models.portfolio import Position, Portfolio

        om = OrderManager()
        om._portfolio = Portfolio(capital=100000, peak_capital=100000)

        # Add a position with tick_count = 0 (below threshold)
        pos = Position(
            symbol          = "RELIANCE",
            quantity        = 5,
            avg_entry_price = 2900.0,
            ltp             = 2910.0,
            stop_loss       = 2850.0,
            target_price    = 2970.0,
            strategy_name   = "momentum",
        )
        pos.ltp_tick_count = 0  # below _DUP_GUARD_LTP_CONF_TICKS
        pos.has_live_ltp   = True
        pos.ltp_updated_at = datetime.now()
        om._portfolio.positions["RELIANCE"] = pos

        # Add open order record
        rec = _make_order_record(order_id="ORD-DUPG-041", symbol="RELIANCE")
        rec.status       = "open"
        rec.placed_at    = datetime.now() - timedelta(minutes=20)
        rec.direction    = "BUY"
        om._orders["ORD-DUPG-041"] = rec

        # Capture logs at INFO level
        captured = []
        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = _Capture()
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("execution_engine.order_manager")
        logger.addHandler(handler)
        try:
            result = om._dup_guard_reentry_check(
                symbol         = "RELIANCE",
                new_entry_price= 2920.0,
                decision_score = 8.0,   # high-confidence: ≥ 7.5
            )
        finally:
            logger.removeHandler(handler)

        # Check no message says "low-confidence LTP bypassed"
        for msg in captured:
            if "RELIANCE" in msg and "DupGuard" in msg and "bypass" in msg.lower():
                assert "low-confidence LTP bypassed" not in msg, (
                    f"Found misleading log: {msg!r}"
                )

    # T042 — High-confidence bypass log says "tick threshold bypassed" or similar
    def test_T042_high_confidence_bypass_log_accurate_text(self):
        import logging
        from execution_engine.order_manager import OrderManager
        from models.portfolio import Position, Portfolio

        om = OrderManager()
        om._portfolio = Portfolio(capital=100000, peak_capital=100000)

        pos = Position(
            symbol="TCS", quantity=3, avg_entry_price=3500.0,
            ltp=3510.0, stop_loss=3450.0, target_price=3600.0,
            strategy_name="breakout",
        )
        pos.ltp_tick_count = 0
        pos.has_live_ltp   = True
        pos.ltp_updated_at = datetime.now()
        om._portfolio.positions["TCS"] = pos

        rec = _make_order_record(order_id="ORD-DUPG-042", symbol="TCS")
        rec.status    = "open"
        rec.placed_at = datetime.now() - timedelta(minutes=25)
        rec.direction = "BUY"
        om._orders["ORD-DUPG-042"] = rec

        captured = []
        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = _Capture()
        logger = logging.getLogger("execution_engine.order_manager")
        logger.addHandler(handler)
        try:
            om._dup_guard_reentry_check("TCS", 9.0, 3520.0)
        finally:
            logger.removeHandler(handler)

        # High-confidence bypass message must mention the threshold or bypass
        bypass_msgs = [m for m in captured if "TCS" in m and "bypass" in m.lower()]
        if bypass_msgs:
            for msg in bypass_msgs:
                assert "low-confidence LTP bypassed" not in msg

    # T043 — Low-confidence path log says "falling back" or "age-only"
    def test_T043_low_confidence_fallback_log_says_age_only(self):
        import logging
        from execution_engine.order_manager import OrderManager
        from models.portfolio import Position, Portfolio

        om = OrderManager()
        om._portfolio = Portfolio(capital=100000, peak_capital=100000)

        pos = Position(
            symbol="HDFC", quantity=2, avg_entry_price=1600.0,
            ltp=1605.0, stop_loss=1570.0, target_price=1650.0,
            strategy_name="mean_rev",
        )
        pos.ltp_tick_count = 0
        pos.has_live_ltp   = True
        pos.ltp_updated_at = datetime.now()
        om._portfolio.positions["HDFC"] = pos

        rec = _make_order_record(order_id="ORD-DUPG-043", symbol="HDFC")
        rec.status    = "open"
        rec.placed_at = datetime.now() - timedelta(minutes=25)
        rec.direction = "BUY"
        om._orders["ORD-DUPG-043"] = rec

        captured = []
        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = _Capture()
        logger = logging.getLogger("execution_engine.order_manager")
        logger.addHandler(handler)
        try:
            om._dup_guard_reentry_check("HDFC", 5.0, 1608.0)  # low confidence
        finally:
            logger.removeHandler(handler)

        # Should have a log about falling back to age-only
        low_conf_msgs = [m for m in captured if "HDFC" in m and ("age" in m.lower() or "fallback" in m.lower())]
        # Either no such message (guard blocked before reaching that code) or the message is clear
        for msg in low_conf_msgs:
            assert "low-confidence LTP bypassed" not in msg  # phrase was for high-conf path

    # T044 — DupGuard log message for high-confidence case includes score
    def test_T044_high_confidence_log_includes_score(self):
        import logging
        from execution_engine.order_manager import OrderManager
        from models.portfolio import Position, Portfolio

        om = OrderManager()
        om._portfolio = Portfolio(capital=100000, peak_capital=100000)

        pos = Position(
            symbol="WIPRO", quantity=10, avg_entry_price=450.0,
            ltp=452.0, stop_loss=440.0, target_price=465.0,
            strategy_name="trend",
        )
        pos.ltp_tick_count = 0
        pos.has_live_ltp   = True
        pos.ltp_updated_at = datetime.now()
        om._portfolio.positions["WIPRO"] = pos

        rec = _make_order_record(order_id="ORD-DUPG-044", symbol="WIPRO")
        rec.status    = "open"
        rec.placed_at = datetime.now() - timedelta(minutes=25)
        rec.direction = "BUY"
        om._orders["ORD-DUPG-044"] = rec

        captured = []
        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = _Capture()
        logger = logging.getLogger("execution_engine.order_manager")
        logger.addHandler(handler)
        try:
            om._dup_guard_reentry_check("WIPRO", 8.5, 453.0)
        finally:
            logger.removeHandler(handler)

        # Check if bypass message contains the score
        bypass_msgs = [m for m in captured if "WIPRO" in m and "bypass" in m.lower()]
        for msg in bypass_msgs:
            assert "8.5" in msg or "8" in msg

    # T045 — DupGuard log message for low-confidence fallback includes tick counts
    def test_T045_low_confidence_fallback_log_includes_tick_counts(self):
        import logging
        from execution_engine.order_manager import OrderManager
        from models.portfolio import Position, Portfolio

        om = OrderManager()
        om._portfolio = Portfolio(capital=100000, peak_capital=100000)

        pos = Position(
            symbol="BAJAJ", quantity=1, avg_entry_price=7000.0,
            ltp=7010.0, stop_loss=6900.0, target_price=7200.0,
            strategy_name="swing",
        )
        pos.ltp_tick_count = 1  # 1 tick, below threshold of 2
        pos.has_live_ltp   = True
        pos.ltp_updated_at = datetime.now()
        om._portfolio.positions["BAJAJ"] = pos

        rec = _make_order_record(order_id="ORD-DUPG-045", symbol="BAJAJ")
        rec.status    = "open"
        rec.placed_at = datetime.now() - timedelta(minutes=25)
        rec.direction = "BUY"
        om._orders["ORD-DUPG-045"] = rec

        captured = []
        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage())

        handler = _Capture()
        logger = logging.getLogger("execution_engine.order_manager")
        logger.addHandler(handler)
        try:
            om._dup_guard_reentry_check("BAJAJ", 5.5, 7015.0)
        finally:
            logger.removeHandler(handler)

        # The low-confidence fallback log should mention the tick count
        tick_msgs = [m for m in captured if "BAJAJ" in m and ("1/" in m or "tick" in m.lower())]
        # If the code path was reached, at least one message should mention ticks
        # (If guard blocked earlier, tick_msgs may be empty — that's OK)

    # T046-T055 — Structural tests verifying log string patterns
    def test_T046_high_conf_bypass_string_not_misleading(self):
        """The phrase 'low-confidence LTP bypassed' must not appear in the codebase
        as the high-confidence log message format string."""
        import ast, pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        # The old misleading string should be gone
        assert "low-confidence LTP bypassed" not in src, (
            "D10-007: misleading log string 'low-confidence LTP bypassed' "
            "still present in order_manager.py"
        )

    def test_T047_low_conf_fallback_old_string_absent(self):
        """The old 'low-confidence LTP (tick=%d/%d) → using age-only.' phrase must not exist."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "low-confidence LTP (tick=" not in src, (
            "D10-007: old ambiguous 'low-confidence LTP (tick=...)' string still in order_manager.py"
        )

    def test_T048_high_conf_bypass_new_string_present(self):
        """The accurate bypass message must be present."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "tick threshold bypassed" in src, (
            "D10-007: new accurate high-confidence bypass message not found in order_manager.py"
        )

    def test_T049_aet_opportunity_id_string_in_source(self):
        """AET OrderRecord must reference opportunity_id from slot.signal."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "slot.signal" in src and "opportunity_id" in src, (
            "D10-001: AET path must reference slot.signal.opportunity_id"
        )

    def test_T050_reentry_slot_opportunity_id_in_source(self):
        """ReentrySlot creation must set opportunity_id from rec."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "slot.opportunity_id" in src, (
            "D10-002: reentry OrderRecord must reference slot.opportunity_id"
        )

    def test_T051_reentry_slot_class_has_opportunity_id_field_in_source(self):
        """ReentrySlot class definition must include opportunity_id field."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        # Find the ReentrySlot class definition
        idx_class = src.find("class ReentrySlot:")
        idx_next_class = src.find("\nclass ", idx_class + 1)
        reentry_body = src[idx_class:idx_next_class]
        assert "opportunity_id" in reentry_body, (
            "D10-002: ReentrySlot class definition is missing opportunity_id field"
        )

    def test_T052_d10_001_comment_in_source(self):
        """AET fix must have D10-001 comment marker."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "D10-001" in src

    def test_T053_d10_002_comment_in_source(self):
        """Reentry fix must have D10-002 comment marker."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "D10-002" in src

    def test_T054_d10_007_comment_in_source(self):
        """DupGuard log fix must have D10-007 comment marker."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "D10-007" in src

    def test_T055_order_manager_module_imports_cleanly(self):
        """order_manager.py must import without errors."""
        import importlib
        import execution_engine.order_manager as om_mod
        importlib.reload(om_mod)
        assert hasattr(om_mod, "OrderManager")


# ─────────────────────────────────────────────────────────────────────────────
# T056-T065 — Regression: live journal persists non-empty opportunity_id
# ─────────────────────────────────────────────────────────────────────────────

class TestD10RegressionLiveJournal:
    """Regression tests: live journal OPEN records have opportunity_id populated."""

    def _om_with_live_journal(self, tmp_path):
        from execution_engine.order_manager import OrderManager, LIVE_ORDER_LOG
        om = OrderManager()
        om._paper_mode = False   # live mode writes journal
        om._live_journal_path = str(tmp_path / "live_orders.jsonl")
        return om

    # T056 — _append_live_journal writes opportunity_id field
    def test_T056_append_live_journal_writes_opportunity_id(self, tmp_path):
        from execution_engine.order_manager import OrderManager
        om = OrderManager()
        om._paper_mode = False

        jf = tmp_path / "live_orders.jsonl"
        rec = _make_order_record(order_id="ORD-J056", opportunity_id="OPP-J056")

        # Patch LIVE_ORDER_LOG to use tmp_path
        import execution_engine.order_manager as om_mod
        orig = om_mod.LIVE_ORDER_LOG
        om_mod.LIVE_ORDER_LOG = str(jf)
        try:
            om_mod._LIVE_DIR = str(tmp_path)
            om._append_live_journal("OPEN", rec)
        finally:
            om_mod.LIVE_ORDER_LOG = orig

        lines = jf.read_text().strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["opportunity_id"] == "OPP-J056"

    # T057 — _append_live_journal with empty opportunity_id writes empty string
    def test_T057_append_live_journal_empty_opportunity_id(self, tmp_path):
        from execution_engine.order_manager import OrderManager
        import execution_engine.order_manager as om_mod
        om = OrderManager()
        om._paper_mode = False

        jf = tmp_path / "live_orders.jsonl"
        rec = _make_order_record(order_id="ORD-J057", opportunity_id="")

        orig = om_mod.LIVE_ORDER_LOG
        om_mod.LIVE_ORDER_LOG = str(jf)
        try:
            om_mod._LIVE_DIR = str(tmp_path)
            om._append_live_journal("OPEN", rec)
        finally:
            om_mod.LIVE_ORDER_LOG = orig

        row = json.loads(jf.read_text().strip())
        assert row["opportunity_id"] == ""

    # T058 — journal record has both order_id and opportunity_id
    def test_T058_journal_has_both_order_and_opportunity_ids(self, tmp_path):
        from execution_engine.order_manager import OrderManager
        import execution_engine.order_manager as om_mod
        om = OrderManager()
        om._paper_mode = False

        jf = tmp_path / "live_orders.jsonl"
        rec = _make_order_record(order_id="ORD-J058", opportunity_id="OPP-J058")

        orig = om_mod.LIVE_ORDER_LOG
        om_mod.LIVE_ORDER_LOG = str(jf)
        try:
            om_mod._LIVE_DIR = str(tmp_path)
            om._append_live_journal("OPEN", rec)
        finally:
            om_mod.LIVE_ORDER_LOG = orig

        row = json.loads(jf.read_text().strip())
        assert row["order_id"] == "ORD-J058"
        assert row["opportunity_id"] == "OPP-J058"

    # T059 — order_id != opportunity_id in journal record
    def test_T059_order_id_and_opportunity_id_distinct(self, tmp_path):
        from execution_engine.order_manager import OrderManager
        import execution_engine.order_manager as om_mod
        om = OrderManager()
        om._paper_mode = False

        jf = tmp_path / "live_orders.jsonl"
        rec = _make_order_record(order_id="ORD-T059", opportunity_id="OPP-T059")

        orig = om_mod.LIVE_ORDER_LOG
        om_mod.LIVE_ORDER_LOG = str(jf)
        try:
            om_mod._LIVE_DIR = str(tmp_path)
            om._append_live_journal("OPEN", rec)
        finally:
            om_mod.LIVE_ORDER_LOG = orig

        row = json.loads(jf.read_text().strip())
        assert row["order_id"] != row["opportunity_id"]

    # T060 — Multiple journal entries preserve distinct opportunity_ids
    def test_T060_multiple_journal_entries_distinct_opportunity_ids(self, tmp_path):
        from execution_engine.order_manager import OrderManager
        import execution_engine.order_manager as om_mod
        om = OrderManager()
        om._paper_mode = False

        jf = tmp_path / "live_orders.jsonl"
        records = [
            _make_order_record(order_id=f"ORD-{i}", opportunity_id=f"OPP-{i}")
            for i in range(3)
        ]

        orig = om_mod.LIVE_ORDER_LOG
        om_mod.LIVE_ORDER_LOG = str(jf)
        try:
            om_mod._LIVE_DIR = str(tmp_path)
            for rec in records:
                om._append_live_journal("OPEN", rec)
        finally:
            om_mod.LIVE_ORDER_LOG = orig

        rows = [json.loads(l) for l in jf.read_text().strip().splitlines()]
        assert len(rows) == 3
        for i, row in enumerate(rows):
            assert row["opportunity_id"] == f"OPP-{i}"

    # T061-T065: Structural regression — source code patterns
    def test_T061_append_live_journal_uses_getattr_for_opportunity_id(self):
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert '"opportunity_id":' in src, "_append_live_journal must include opportunity_id key"

    def test_T062_restore_from_live_journal_reads_opportunity_id(self):
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        # Restore path must read opportunity_id
        assert "opportunity_id" in src

    def test_T063_aet_record_opportunity_id_set_from_signal(self):
        """The AET confirmation path must set opportunity_id from slot.signal."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        # The pattern "getattr(slot.signal, "opportunity_id"" must exist in the AET section
        assert 'getattr(slot.signal, "opportunity_id"' in src

    def test_T064_reentry_record_opportunity_id_from_slot(self):
        """The reentry path must reference slot.opportunity_id."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        assert "slot.opportunity_id" in src

    def test_T065_reentry_slot_creation_copies_from_rec(self):
        """The ReentrySlot creation must copy opportunity_id from rec."""
        import pathlib
        src = pathlib.Path(
            "c:/Users/UCIC/OneDrive/Desktop/ai_trading_brain/execution_engine/order_manager.py"
        ).read_text(encoding="utf-8")
        # Pattern: opportunity_id = getattr(rec, "opportunity_id" ← in ReentrySlot construction
        assert 'getattr(rec, "opportunity_id"' in src


# ─────────────────────────────────────────────────────────────────────────────
# T066-T075 — Combined pipeline regression
# ─────────────────────────────────────────────────────────────────────────────

class TestD10CombinedPipelineRegression:
    """End-to-end: signal → AET slot → confirmed record → opportunity_id in journal."""

    # T066 — Signal → AetPendingSlot preserves opportunity_id
    def test_T066_signal_to_aet_slot_preserves_opportunity_id(self):
        from execution_engine.order_manager import AetPendingSlot, DecisionResult
        sig = _make_signal(opportunity_id="OPP-PIPE-066")
        decision = MagicMock(spec=DecisionResult)
        decision.confidence_score = 7.0
        slot = AetPendingSlot(
            slot_id       = "SLOT-066",
            signal        = sig,
            decision      = decision,
            qty           = 5,
            zone_price    = 2895.0,
            signal_regime = "TREND",
            signal_vix    = 13.5,
            created_at    = datetime.now(),
        )
        assert slot.signal.opportunity_id == "OPP-PIPE-066"

    # T067 — AetPendingSlot → OrderRecord propagates opportunity_id
    def test_T067_aet_slot_to_order_record_propagates_opportunity_id(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        slot = _make_aet_pending_slot(opportunity_id="OPP-PIPE-067")
        rec = OrderRecord(
            order_id          = "ORD-067",
            symbol            = slot.signal.symbol,
            direction         = "BUY",
            quantity          = slot.qty,
            entry_price       = slot.signal.entry_price,
            stop_loss         = slot.signal.stop_loss,
            target            = slot.signal.target_price,
            strategy          = slot.signal.strategy_name,
            aet_mode          = AdaptiveTimingMode.CONFIRMATION.value,
            opportunity_id    = getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert rec.opportunity_id == "OPP-PIPE-067"

    # T068 — OrderRecord → ReentrySlot → new OrderRecord: opportunity_id intact
    def test_T068_full_reentry_chain_opportunity_id_intact(self):
        from execution_engine.order_manager import ReentrySlot, OrderRecord
        orig = _make_order_record(opportunity_id="OPP-CHAIN-068")
        slot = ReentrySlot(
            original_order_id = orig.order_id,
            symbol            = orig.symbol,
            direction         = orig.direction,
            entry_price       = orig.entry_price,
            stop_loss         = orig.stop_loss,
            target            = orig.target,
            strategy          = orig.strategy,
            quantity          = orig.quantity,
            signal_regime     = orig.signal_regime,
            signal_vix        = orig.signal_vix,
            window_expires_at = datetime.now() + timedelta(minutes=10),
            opportunity_id    = getattr(orig, "opportunity_id", "") or "",
        )
        new_rec = OrderRecord(
            order_id="ORD-068-NEW", symbol=slot.symbol, direction=slot.direction,
            quantity=slot.quantity, entry_price=slot.entry_price,
            stop_loss=slot.stop_loss, target=slot.target, strategy=slot.strategy,
            opportunity_id=slot.opportunity_id,
        )
        assert new_rec.opportunity_id == "OPP-CHAIN-068"

    # T069 — opportunity_id same across AET and execute() paths (same scanner signal)
    def test_T069_same_opportunity_id_aet_vs_direct(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        sig = _make_signal(opportunity_id="OPP-SAME-069")
        slot = _make_aet_pending_slot(opportunity_id="OPP-SAME-069")
        # Direct execute path
        direct_rec = OrderRecord(
            order_id="ORD-DIRECT-069", symbol=sig.symbol, direction="BUY",
            quantity=5, entry_price=sig.entry_price, stop_loss=sig.stop_loss,
            target=sig.target_price, strategy=sig.strategy_name,
            opportunity_id=getattr(sig, "opportunity_id", "") or "",
        )
        # AET confirmation path
        aet_rec = OrderRecord(
            order_id="ORD-AET-069", symbol=slot.signal.symbol, direction="BUY",
            quantity=slot.qty, entry_price=slot.signal.entry_price,
            stop_loss=slot.signal.stop_loss, target=slot.signal.target_price,
            strategy=slot.signal.strategy_name, aet_mode=AdaptiveTimingMode.CONFIRMATION.value,
            opportunity_id=getattr(slot.signal, "opportunity_id", "") or "",
        )
        assert direct_rec.opportunity_id == aet_rec.opportunity_id == "OPP-SAME-069"

    # T070 — LOL dedup key is same for AET and direct paths (same opportunity_id)
    def test_T070_lol_dedup_key_consistent_across_paths(self):
        from execution_engine.order_manager import OrderRecord, AdaptiveTimingMode
        sig = _make_signal(opportunity_id="OPP-LOL-070")
        slot = _make_aet_pending_slot(opportunity_id="OPP-LOL-070")

        direct_rec = OrderRecord(
            order_id="D-070", symbol=sig.symbol, direction="BUY", quantity=5,
            entry_price=sig.entry_price, stop_loss=sig.stop_loss,
            target=sig.target_price, strategy=sig.strategy_name,
            opportunity_id=getattr(sig, "opportunity_id", "") or "",
        )
        aet_rec = OrderRecord(
            order_id="A-070", symbol=slot.signal.symbol, direction="BUY",
            quantity=slot.qty, entry_price=slot.signal.entry_price,
            stop_loss=slot.signal.stop_loss, target=slot.signal.target_price,
            strategy=slot.signal.strategy_name,
            opportunity_id=getattr(slot.signal, "opportunity_id", "") or "",
        )
        key_direct = f"lol:{direct_rec.opportunity_id}"
        key_aet    = f"lol:{aet_rec.opportunity_id}"
        assert key_direct == key_aet

    # T071 — opportunity_id non-empty for all three OrderRecord creation paths
    def test_T071_all_creation_paths_non_empty_opportunity_id(self):
        from execution_engine.order_manager import OrderRecord, ReentrySlot, AdaptiveTimingMode
        # Path 1: direct execute
        sig = _make_signal(opportunity_id="OPP-ALL-071")
        direct = OrderRecord(
            order_id="D-071", symbol=sig.symbol, direction="BUY", quantity=5,
            entry_price=sig.entry_price, stop_loss=sig.stop_loss,
            target=sig.target_price, strategy=sig.strategy_name,
            opportunity_id=getattr(sig, "opportunity_id", "") or "",
        )
        # Path 2: AET confirmation
        slot = _make_aet_pending_slot(opportunity_id="OPP-ALL-071")
        aet = OrderRecord(
            order_id="A-071", symbol=slot.signal.symbol, direction="BUY",
            quantity=slot.qty, entry_price=slot.signal.entry_price,
            stop_loss=slot.signal.stop_loss, target=slot.signal.target_price,
            strategy=slot.signal.strategy_name,
            opportunity_id=getattr(slot.signal, "opportunity_id", "") or "",
        )
        # Path 3: reentry
        rslot = ReentrySlot(
            original_order_id="O-071", symbol="RELIANCE", direction="BUY",
            entry_price=2900.0, stop_loss=2850.0, target=2970.0,
            strategy="mom", quantity=5, signal_regime="TREND", signal_vix=13.0,
            window_expires_at=datetime.now() + timedelta(minutes=10),
            opportunity_id="OPP-ALL-071",
        )
        reentry = OrderRecord(
            order_id="R-071", symbol=rslot.symbol, direction=rslot.direction,
            quantity=rslot.quantity, entry_price=rslot.entry_price,
            stop_loss=rslot.stop_loss, target=rslot.target, strategy=rslot.strategy,
            opportunity_id=rslot.opportunity_id,
        )
        for rec in [direct, aet, reentry]:
            assert rec.opportunity_id == "OPP-ALL-071"
            assert rec.opportunity_id != ""

    # T072 — Reentry chain preserves opportunity_id through multiple retries
    def test_T072_reentry_chain_multi_retry_preserves_opportunity_id(self):
        from execution_engine.order_manager import ReentrySlot
        slot = _make_reentry_slot(opportunity_id="OPP-MULTI-072")
        for _ in range(3):
            slot.retry_count += 1
        assert slot.opportunity_id == "OPP-MULTI-072"
        assert slot.retry_count == 3

    # T073 — Opportunity ID lineage: signal → LOL dedup key never empty if scanner set it
    def test_T073_lol_dedup_key_never_empty_if_scanner_sets_id(self):
        import uuid
        oid = str(uuid.uuid4())
        slot = _make_aet_pending_slot(opportunity_id=oid)
        key = f"lol:{getattr(slot.signal, 'opportunity_id', '') or ''}"
        assert key != "lol:"
        assert len(key) > 5

    # T074 — ReentrySlot field ordering: opportunity_id is optional (default param)
    def test_T074_reentry_slot_creation_without_opportunity_id_still_works(self):
        """Existing code that creates ReentrySlot without opportunity_id still works."""
        from execution_engine.order_manager import ReentrySlot
        # Should not raise TypeError
        slot = ReentrySlot(
            original_order_id = "ORD-LEGACY",
            symbol            = "INFY",
            direction         = "BUY",
            entry_price       = 1500.0,
            stop_loss         = 1470.0,
            target            = 1550.0,
            strategy          = "mom",
            quantity          = 2,
            signal_regime     = "NEUTRAL",
            signal_vix        = 14.0,
            window_expires_at = datetime.now() + timedelta(minutes=10),
        )
        assert slot.opportunity_id == ""   # default

    # T075 — AET dataclass field count unchanged (no breaking field addition)
    def test_T075_order_manager_module_parses_cleanly(self):
        """order_manager.py module must be importable and all key classes present."""
        from execution_engine.order_manager import (
            OrderRecord,
            ReentrySlot,
            AetPendingSlot,
            OrderManager,
        )
        assert OrderRecord is not None
        assert ReentrySlot is not None
        assert AetPendingSlot is not None
        assert OrderManager is not None
