"""tests/unit/investment/market/sector_rotation/test_sector_confidence.py"""
from __future__ import annotations

import pytest

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    RotationSignal,
    RotationStrength,
    RotationType,
    SectorConfidenceScore,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorRankEntry,
    SectorStage,
)
from iios.investment.market.sector_rotation.sector_confidence import compute_confidence
from iios.investment.market.sector_rotation.sector_score import compute_composite_score
from iios.investment.market.sector_rotation.models import RelativeStrengthScore


def _rs(composite: float) -> RelativeStrengthScore:
    return RelativeStrengthScore(
        symbol="X", vs_benchmark=0.0, vs_group=0.0,
        composite=composite, rank=1, percentile=1.0,
    )


def _flow(net: float) -> CapitalFlowProfile:
    return CapitalFlowProfile(
        sector="X", bar_index=1,
        flow_type=FlowType.ACCUMULATION if net > 0 else FlowType.DISTRIBUTION,
        flow_intensity=abs(net), volume_ratio=1.0,
        accumulation_score=50.0 + net * 50.0,
        distribution_score=50.0 - net * 50.0,
        net_flow_signal=net,
    )


def _lifecycle(stage: SectorStage) -> SectorLifecycleProfile:
    return SectorLifecycleProfile(
        sector="X", stage=stage, stage_duration_bars=5,
        previous_stage=None, stage_confidence=0.8,
        transition_probability=0.2,
    )


def _perf(momentum: float) -> SectorPerformance:
    return SectorPerformance(
        sector="X", bar_index=1,
        return_1bar=0.01, return_5bar=0.05, return_20bar=0.10, return_60bar=0.30,
        rel_return_1bar=0.005, rel_return_5bar=0.025, rel_return_20bar=0.05,
        breadth_pct=0.7, avg_volume_ratio=1.3,
        momentum_score=momentum, strength_score=momentum, n_securities=5,
    )


def _ranking(sector: str, composite: float, rank: int) -> SectorRankEntry:
    return SectorRankEntry(
        rank=rank, sector=sector, composite_score=composite,
        relative_strength=50.0, momentum=55.0, flow_signal=0.2,
        lifecycle_stage=SectorStage.LEADING, rank_change=0,
    )


class TestComputeCompositeScore:
    def test_strong_sector(self):
        score = compute_composite_score(
            perf=_perf(75.0),
            rs=_rs(80.0),
            flow=_flow(0.6),
            lifecycle=_lifecycle(SectorStage.LEADING),
        )
        assert score > 60.0

    def test_weak_sector(self):
        score = compute_composite_score(
            perf=_perf(30.0),
            rs=_rs(20.0),
            flow=_flow(-0.6),
            lifecycle=_lifecycle(SectorStage.LAGGING),
        )
        assert score < 50.0

    def test_range(self):
        for mom in (20.0, 50.0, 80.0):
            for rs_v in (20.0, 50.0, 80.0):
                for flow_v in (-0.8, 0.0, 0.8):
                    for stage in (SectorStage.LEADING, SectorStage.LAGGING):
                        score = compute_composite_score(
                            _perf(mom), _rs(rs_v), _flow(flow_v), _lifecycle(stage)
                        )
                        assert 0.0 <= score <= 100.0


class TestComputeConfidence:
    def _make_rankings(self, scores):
        return [_ranking(f"S{i}", s, i + 1) for i, s in enumerate(scores)]

    def test_output_type(self):
        rankings = self._make_rankings([80.0, 60.0, 40.0])
        perfs    = {f"S{i}": _perf(55.0) for i in range(3)}
        flows    = {f"S{i}": _flow(0.2)  for i in range(3)}
        profiles = {f"S{i}": _lifecycle(SectorStage.MATURE) for i in range(3)}
        conf = compute_confidence(
            sector_rankings=rankings,
            sector_perfs=perfs,
            lifecycle_profiles=profiles,
            capital_flows=flows,
            rotation_signals=[],
            n_bars_warm=20,
        )
        assert isinstance(conf, SectorConfidenceScore)

    def test_all_fields_in_range(self):
        rankings = self._make_rankings([80.0, 70.0, 50.0])
        perfs    = {f"S{i}": _perf(60.0) for i in range(3)}
        flows    = {f"S{i}": _flow(0.3)  for i in range(3)}
        profiles = {f"S{i}": _lifecycle(SectorStage.LEADING) for i in range(3)}
        sig = RotationSignal(
            RotationType.INTO_DEFENSIVES, RotationStrength.STRONG,
            ["S2"], ["S0"], 0.8, 5, True,
        )
        conf = compute_confidence(
            sector_rankings=rankings,
            sector_perfs=perfs,
            lifecycle_profiles=profiles,
            capital_flows=flows,
            rotation_signals=[sig],
            n_bars_warm=20,
        )
        assert 0.0 <= conf.leadership_confidence <= 1.0
        assert 0.0 <= conf.rotation_confidence   <= 1.0
        assert 0.0 <= conf.strength_score        <= 100.0
        assert 0.0 <= conf.flow_confidence       <= 1.0
        assert 0.0 <= conf.overall_score         <= 100.0

    def test_warmup_damping(self):
        rankings = self._make_rankings([80.0, 60.0])
        perfs    = {"S0": _perf(70.0), "S1": _perf(50.0)}
        flows    = {"S0": _flow(0.5),  "S1": _flow(0.1)}
        profiles = {"S0": _lifecycle(SectorStage.LEADING), "S1": _lifecycle(SectorStage.MATURE)}

        conf_cold = compute_confidence(
            sector_rankings=rankings, sector_perfs=perfs,
            lifecycle_profiles=profiles, capital_flows=flows,
            rotation_signals=[], n_bars_warm=1,
        )
        conf_warm = compute_confidence(
            sector_rankings=rankings, sector_perfs=perfs,
            lifecycle_profiles=profiles, capital_flows=flows,
            rotation_signals=[], n_bars_warm=50,
        )
        assert conf_warm.overall_score >= conf_cold.overall_score

    def test_empty_inputs(self):
        conf = compute_confidence(
            sector_rankings=[],
            sector_perfs={},
            lifecycle_profiles={},
            capital_flows={},
            rotation_signals=[],
            n_bars_warm=5,
        )
        assert isinstance(conf, SectorConfidenceScore)
        # With no sectors, leadership and rotation confidence are 0;
        # only the default strength contributes a small residual.
        assert conf.leadership_confidence == 0.0
        assert conf.rotation_confidence   == 0.0
        assert conf.overall_score >= 0.0
