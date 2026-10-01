"""
tests/test_dta_confidence_provenance_001.py
==============================================
DTA-CONFIDENCE-PROVENANCE-001

TradeSignal.confidence can be silently overwritten in place by KDA's
conviction score (DTA-KDA-AUTHORITY-001, orchestrator/master_orchestrator.py)
-- meaning the SAME field changes meaning mid-pipeline from "scanner
technical pattern score" to "KDA evidence-based conviction" with nothing
but a log line marking the switch.

This adds `TradeSignal.confidence_source` ("SCANNER" | "KDA_CONVICTION_
OVERRIDE") so that mutation is permanent and traceable on the signal
itself, independent of logs. Purely additive/observational: no decision,
risk, or execution gate reads this field -- it never changes any trade
outcome, only makes an existing, already-live behavior visible.
"""
from __future__ import annotations

from models.trade_signal import SignalDirection, TradeSignal
from risk_control.capital_risk_engine import CapitalRiskEngine


def _sig(**kwargs) -> TradeSignal:
    defaults = dict(symbol="RELIANCE", direction=SignalDirection.BUY, confidence=5.0)
    defaults.update(kwargs)
    return TradeSignal(**defaults)


class TestConfidenceSourceField:

    def test_T01_default_is_scanner(self):
        sig = _sig()
        assert sig.confidence_source == "SCANNER"

    def test_T02_unaffected_by_ordinary_field_construction(self):
        sig = _sig(confidence=8.2, scanner_score=8.2, kda_conviction=None)
        assert sig.confidence_source == "SCANNER"

    def test_T03_explicit_override_flag_settable(self):
        sig = _sig(confidence=5.3)
        sig.confidence = 8.35
        sig.confidence_source = "KDA_CONVICTION_OVERRIDE"
        assert sig.confidence == 8.35
        assert sig.confidence_source == "KDA_CONVICTION_OVERRIDE"
        # scanner_score (if set) remains the untouched original, independent of this flag
        sig.scanner_score = 5.3
        assert sig.scanner_score == 5.3


class TestOrchestratorOverrideSetsProvenance:

    def test_T04_master_orchestrator_sets_source_at_override_site(self):
        """
        Source-inspection regression guard: the exact override block in
        master_orchestrator.py (DTA-KDA-AUTHORITY-001 / DTA-KDA-CONV-002)
        must set confidence_source immediately after mutating confidence.
        """
        import inspect
        import orchestrator.master_orchestrator as mod
        src = inspect.getsource(mod)
        assert '_kda_sig.confidence = _kr_conv' in src
        idx = src.index('_kda_sig.confidence = _kr_conv')
        # the provenance assignment must appear shortly after the mutation
        window = src[idx:idx + 600]
        assert '_kda_sig.confidence_source = "KDA_CONVICTION_OVERRIDE"' in window


class TestCapitalRiskEngineSurfacesProvenance:

    def test_T05_opportunity_profile_metadata_includes_confidence_source(self):
        sig = _sig(confidence=8.35, confidence_source="KDA_CONVICTION_OVERRIDE")
        meta = CapitalRiskEngine._opportunity_profile_metadata(sig)
        assert meta["confidence_source"] == "KDA_CONVICTION_OVERRIDE"

    def test_T06_opportunity_profile_metadata_defaults_to_scanner(self):
        sig = _sig(confidence=5.0)
        meta = CapitalRiskEngine._opportunity_profile_metadata(sig)
        assert meta["confidence_source"] == "SCANNER"

    def test_T07_metadata_fails_open_for_signal_missing_attribute(self):
        class Bare:
            pass
        bare = Bare()
        meta = CapitalRiskEngine._opportunity_profile_metadata(bare)  # type: ignore[arg-type]
        assert meta["confidence_source"] == "SCANNER"


class TestSafetyContract:

    def test_T08_confidence_source_never_read_by_risk_manager_gate(self):
        """
        Regression guard: confidence_source must stay observational-only --
        no live decision/risk gate may branch on it.
        """
        import inspect
        for modpath, modname in [
            ("risk_control.risk_manager_ai", "risk_manager_ai"),
            ("decision_ai.decision_engine", "decision_engine"),
            ("strategy_lab.strategy_generator_ai", "strategy_generator_ai"),
        ]:
            mod = __import__(modpath, fromlist=[modname])
            src = inspect.getsource(mod)
            assert "confidence_source" not in src, (
                f"{modpath} must never branch on confidence_source (observability-only field)"
            )
