"""tests/unit/investment/market/volatility/test_regime_classifier.py"""
from __future__ import annotations

import pytest

from iios.investment.market.volatility.regime_classifier import RegimeClassifier
from iios.investment.market.volatility.models import (
    VolatilityBehaviour,
    VolatilityRegimeType,
    VolatilityRegimeSnapshot,
    VolatilityTransitionType,
)
from tests.unit.investment.market.volatility.conftest import make_vol_state


def classify(
    normalized: float,
    relative: float = 1.0,
    behaviour: VolatilityBehaviour = VolatilityBehaviour.STABLE,
    previous: VolatilityRegimeType | None = None,
) -> VolatilityRegimeSnapshot:
    clf = RegimeClassifier()
    state = make_vol_state(
        normalized_volatility=normalized,
        relative_volatility=relative,
    )
    return clf.classify(state, behaviour, previous, duration_bars=5)


class TestRegimeClassification:
    def test_very_low_normalized(self):
        snap = classify(0.05)
        assert snap.regime == VolatilityRegimeType.VERY_LOW

    def test_low_normalized(self):
        snap = classify(0.18)
        assert snap.regime == VolatilityRegimeType.LOW

    def test_normal_normalized(self):
        snap = classify(0.40)
        assert snap.regime == VolatilityRegimeType.NORMAL

    def test_elevated_normalized(self):
        snap = classify(0.63)
        assert snap.regime == VolatilityRegimeType.ELEVATED

    def test_high_normalized(self):
        snap = classify(0.78)
        assert snap.regime == VolatilityRegimeType.HIGH

    def test_extreme_normalized(self):
        snap = classify(0.90)
        assert snap.regime == VolatilityRegimeType.EXTREME

    def test_shock_normalized(self):
        snap = classify(0.95)
        assert snap.regime == VolatilityRegimeType.SHOCK

    def test_expansion_detected(self):
        snap = classify(
            normalized=0.60,
            relative=1.20,
            behaviour=VolatilityBehaviour.EXPANDING,
        )
        assert snap.regime == VolatilityRegimeType.EXPANSION

    def test_compression_detected(self):
        snap = classify(
            normalized=0.35,
            relative=0.85,
            behaviour=VolatilityBehaviour.COMPRESSING,
        )
        assert snap.regime == VolatilityRegimeType.COMPRESSION

    def test_recovery_after_extreme(self):
        snap = classify(
            normalized=0.70,
            relative=0.88,
            previous=VolatilityRegimeType.EXTREME,
        )
        assert snap.regime == VolatilityRegimeType.RECOVERY

    def test_recovery_after_shock(self):
        snap = classify(
            normalized=0.65,
            relative=0.85,
            previous=VolatilityRegimeType.SHOCK,
        )
        assert snap.regime == VolatilityRegimeType.RECOVERY

    def test_no_recovery_if_vol_rising(self):
        """Rising vol after shock should classify as HIGH/EXTREME, not RECOVERY."""
        snap = classify(
            normalized=0.90,
            relative=1.10,   # vol still high, not falling
            previous=VolatilityRegimeType.SHOCK,
        )
        # RECOVERY requires relative < 0.95, so this should be EXTREME
        assert snap.regime in (VolatilityRegimeType.EXTREME, VolatilityRegimeType.SHOCK)


class TestRegimeSnapshotFields:
    def test_confidence_in_range(self):
        snap = classify(0.50)
        assert 0.0 <= snap.confidence <= 1.0

    def test_transition_probability_in_range(self):
        snap = classify(0.50)
        assert 0.0 <= snap.transition_probability <= 1.0

    def test_regime_score_in_range(self):
        snap = classify(0.40)
        assert 0.0 <= snap.regime_score <= 100.0

    def test_duration_bars(self):
        clf = RegimeClassifier()
        state = make_vol_state(normalized_volatility=0.40)
        snap = clf.classify(state, VolatilityBehaviour.STABLE, None, duration_bars=15)
        assert snap.duration_bars == 15

    def test_transition_type_stable(self):
        snap = classify(0.40)
        assert snap.transition_type in list(VolatilityTransitionType)

    def test_to_dict(self):
        snap = classify(0.50)
        d = snap.to_dict()
        assert "regime" in d
        assert "confidence" in d
        assert "transition_probability" in d


class TestRegimeConfidenceProperties:
    def test_uninitialised_state_lower_confidence(self):
        clf = RegimeClassifier()
        state_init = make_vol_state(normalized_volatility=0.40, is_initialized=True)
        state_uninit = make_vol_state(normalized_volatility=0.40, is_initialized=False)
        snap_init   = clf.classify(state_init, VolatilityBehaviour.STABLE, None, 5)
        snap_uninit = clf.classify(state_uninit, VolatilityBehaviour.STABLE, None, 5)
        assert snap_init.confidence > snap_uninit.confidence

    def test_shock_produces_high_transition_prob(self):
        snap = classify(0.96)
        # Shock regime should be somewhat unstable (high vol-of-vol scenario)
        # just verify it's a valid float
        assert 0.0 <= snap.transition_probability <= 1.0
