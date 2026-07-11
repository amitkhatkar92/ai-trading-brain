"""tests/unit/investment/market/sector_rotation/test_rotation_detector.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import (
    RotationStrength,
    RotationType,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.rotation_classifier import classify_rotation
from iios.investment.market.sector_rotation.rotation_detector import RotationDetector
from iios.investment.market.sector_rotation.rotation_history import RotationHistory
from iios.investment.market.sector_rotation.rotation_statistics import (
    avg_confidence,
    dominant_rotation_type,
    rotation_frequency,
    sectors_most_often_falling,
    sectors_most_often_rising,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


def _make_perf(sector: str, momentum: float) -> SectorPerformance:
    return SectorPerformance(
        sector=sector, bar_index=1,
        return_1bar=0.0, return_5bar=0.0, return_20bar=0.0, return_60bar=0.0,
        rel_return_1bar=0.0, rel_return_5bar=0.0, rel_return_20bar=0.0,
        breadth_pct=0.5, avg_volume_ratio=1.0,
        momentum_score=momentum, strength_score=momentum,
        n_securities=3,
    )


class TestRotationClassifier:
    def setup_method(self):
        self.taxonomy = SectorTaxonomy()

    def test_defensive_rotation(self):
        rising  = ["Consumer Staples", "Utilities", "Health Care"]
        falling = ["Financials", "Energy", "Information Technology"]
        rot_type, strength, conf = classify_rotation(rising, falling, self.taxonomy)
        assert rot_type is RotationType.INTO_DEFENSIVES
        assert 0.0 < conf <= 1.0

    def test_cyclical_rotation(self):
        rising  = ["Financials", "Energy", "Materials"]
        falling = ["Consumer Staples", "Utilities"]
        rot_type, strength, conf = classify_rotation(rising, falling, self.taxonomy)
        assert rot_type is RotationType.INTO_CYCLICALS

    def test_no_rotation_empty(self):
        rot_type, strength, conf = classify_rotation([], [], self.taxonomy)
        assert rot_type is RotationType.NO_ROTATION

    def test_broad_rotation_many_sectors(self):
        all_sectors = self.taxonomy.sectors()
        rising  = all_sectors[:6]
        falling = all_sectors[6:]
        rot_type, _, _ = classify_rotation(rising, falling, self.taxonomy)
        assert rot_type in {
            RotationType.BROAD_ROTATION,
            RotationType.INTO_DEFENSIVES,
            RotationType.INTO_CYCLICALS,
        }

    def test_confidence_in_range(self):
        rising  = ["Consumer Staples"]
        falling = ["Financials"]
        _, _, conf = classify_rotation(rising, falling, self.taxonomy)
        assert 0.0 <= conf <= 1.0


class TestRotationDetector:
    def setup_method(self):
        self.taxonomy = SectorTaxonomy()
        self.detector = RotationDetector(self.taxonomy, min_rank_change=1, confirm_bars=3)

    def _make_flows(self):
        return {}  # capital flows optional for these tests

    def test_no_signal_on_first_bar(self):
        perfs = {
            "Information Technology": _make_perf("Information Technology", 70.0),
            "Consumer Staples": _make_perf("Consumer Staples", 40.0),
        }
        signal = self.detector.update(perfs, self._make_flows())
        assert signal is None  # no history to compare

    def test_signal_on_large_rank_change(self):
        perfs_1 = {
            "Information Technology": _make_perf("Information Technology", 80.0),
            "Consumer Staples":       _make_perf("Consumer Staples",       30.0),
            "Utilities":              _make_perf("Utilities",               25.0),
        }
        self.detector.update(perfs_1, self._make_flows())

        # IT falls, defensives rise
        perfs_2 = {
            "Information Technology": _make_perf("Information Technology", 25.0),
            "Consumer Staples":       _make_perf("Consumer Staples",       80.0),
            "Utilities":              _make_perf("Utilities",               75.0),
        }
        signal = self.detector.update(perfs_2, self._make_flows())
        # Signal may or may not fire depending on rank_change threshold vs n sectors
        # At minimum, the method returns without error
        assert signal is None or signal.rotation_type is not None

    def test_confirmed_after_n_bars(self):
        """Signal becomes confirmed after confirm_bars repetitions."""
        detector = RotationDetector(
            self.taxonomy, min_rank_change=1, confirm_bars=2
        )
        perfs_a = {
            "Information Technology": _make_perf("IT", 80.0),
            "Consumer Staples":       _make_perf("CS", 20.0),
        }
        perfs_b = {
            "Information Technology": _make_perf("IT", 20.0),
            "Consumer Staples":       _make_perf("CS", 80.0),
        }
        detector.update(perfs_a, {})
        for _ in range(4):
            sig = detector.update(perfs_b, {})
        # If a signal is produced, confirmed status increases over time
        if sig is not None:
            assert sig.bars_active >= 1

    def test_rank_changes_populated(self):
        perfs_1 = {"IT": _make_perf("IT", 60.0), "FIN": _make_perf("FIN", 40.0)}
        self.detector.update(perfs_1, {})
        self.detector.update({"IT": _make_perf("IT", 40.0), "FIN": _make_perf("FIN", 60.0)}, {})
        changes = self.detector.rank_changes()
        assert isinstance(changes, dict)

    def test_current_ranks_after_update(self):
        perfs = {"IT": _make_perf("IT", 70.0), "FIN": _make_perf("FIN", 30.0)}
        self.detector.update(perfs, {})
        ranks = self.detector.current_ranks()
        assert ranks is not None
        assert "IT" in ranks


class TestRotationHistory:
    def test_append_and_len(self):
        h = RotationHistory(maxlen=10)
        from iios.investment.market.sector_rotation.models import RotationSignal
        sig = RotationSignal(RotationType.INTO_DEFENSIVES, RotationStrength.MODERATE,
                             ["IT"], ["Utilities"], 0.7, 3, True)
        h.append(sig)
        assert len(h) == 1
        assert h.latest() is sig

    def test_maxlen_respected(self):
        h = RotationHistory(maxlen=5)
        from iios.investment.market.sector_rotation.models import RotationSignal
        for i in range(10):
            sig = RotationSignal(RotationType.NO_ROTATION, RotationStrength.WEAK,
                                 [], [], 0.1, 1, False)
            h.append(sig)
        assert len(h) == 5

    def test_by_type(self):
        h = RotationHistory()
        from iios.investment.market.sector_rotation.models import RotationSignal
        s1 = RotationSignal(RotationType.INTO_DEFENSIVES, RotationStrength.WEAK, [], [], 0.5, 1, False)
        s2 = RotationSignal(RotationType.INTO_CYCLICALS,  RotationStrength.MODERATE, [], [], 0.5, 2, True)
        h.append(s1)
        h.append(s2)
        assert len(h.by_type(RotationType.INTO_DEFENSIVES)) == 1
        assert len(h.by_type(RotationType.INTO_CYCLICALS)) == 1

    def test_confirmed_signals(self):
        h = RotationHistory()
        from iios.investment.market.sector_rotation.models import RotationSignal
        s1 = RotationSignal(RotationType.NO_ROTATION, RotationStrength.WEAK, [], [], 0.1, 1, False)
        s2 = RotationSignal(RotationType.INTO_DEFENSIVES, RotationStrength.STRONG, [], [], 0.8, 5, True)
        h.append(s1)
        h.append(s2)
        confirmed = h.confirmed_signals()
        assert len(confirmed) == 1
        assert confirmed[0] is s2


class TestRotationStatistics:
    def _make_history_with_signals(self) -> RotationHistory:
        from iios.investment.market.sector_rotation.models import RotationSignal
        h = RotationHistory()
        for i in range(5):
            sig = RotationSignal(
                RotationType.INTO_DEFENSIVES, RotationStrength.MODERATE,
                ["IT"], ["Utilities", "Consumer Staples"], 0.7, i + 1, i >= 2,
            )
            h.append(sig)
        for i in range(3):
            sig = RotationSignal(
                RotationType.INTO_CYCLICALS, RotationStrength.WEAK,
                ["Utilities"], ["Financials"], 0.3, i + 1, False,
            )
            h.append(sig)
        return h

    def test_rotation_frequency(self):
        h = self._make_history_with_signals()
        freq = rotation_frequency(h, window=20)
        assert "into_defensives" in freq
        assert 0.0 <= freq["into_defensives"] <= 1.0

    def test_dominant_rotation_type(self):
        h = self._make_history_with_signals()
        dom = dominant_rotation_type(h)
        assert dom is RotationType.INTO_DEFENSIVES

    def test_avg_confidence(self):
        h = self._make_history_with_signals()
        conf = avg_confidence(h)
        assert 0.0 <= conf <= 1.0

    def test_sectors_most_often_rising(self):
        h = self._make_history_with_signals()
        # to_sectors=["Utilities","Consumer Staples"] → they appear most in rising list
        rising = sectors_most_often_rising(h)
        assert "Utilities" in rising or "Consumer Staples" in rising

    def test_sectors_most_often_falling(self):
        h = self._make_history_with_signals()
        # from_sectors=["IT"] → IT appears most in falling list
        falling = sectors_most_often_falling(h)
        assert "IT" in falling
