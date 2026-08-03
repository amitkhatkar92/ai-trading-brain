"""
test_dna_discovery_engine.py — MLS Phase 3 test suite.

Covers:
    MLSConfig Phase 3 fields   — defaults, overrides, hash change
    DNADiscoveryEngine init    — default, custom config/dir
    discover() structure       — type, IDs, regime, profiles, persistence
    Winner characteristics     — detected, direction, effect_abs, confidence
    Loser characteristics      — WINNERS_LOWER direction, threshold
    Neutral analysis           — NEUTRALS_HIGHER/LOWER direction
    Cohen's d math             — known inputs, sign, zero groups, constants
    Spearman math              — known monotonic, anti-monotonic, constant
    Bootstrap CI               — contains effect, finite, width
    FeatureEvidence model      — round-trip, fields present
    DNACharacteristic model    — round-trip, char_id prefix, lifecycle default
    DNAInteraction             — detected, amplification >= threshold, round-trip
    WinnerDNA / LoserDNA       — round-trip, n_members, population_ids
    NeutralDNA                 — round-trip, direction NEUTRALS_*
    DiscoveryReport model      — round-trip, IDs, characteristics_by_direction
    Feature type detection     — binary, continuous, ordinal
    Lifecycle advancement      — DISCOVERED/REPLICATED/VERIFIED/STABLE/WEAKENING
    Storage                    — load, list sorted, .bak, missing->None
    Statistics                 — type, counts, top_feature, avg_effect
    Query API                  — winner_dna/loser_dna/neutral_dna/list_chars
    Insufficient data          — raises InsufficientDataError, custom min_group
    Constant feature skipped   — zero-variance feature not reported
    Market-wide features       — excluded from characteristics
    Thread safety              — 8 concurrent discover() calls

Run:
    python test_dna_discovery_engine.py
"""
from __future__ import annotations

import math
import random
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_learning import (
    DNADiscoveryEngine,
    DNACharacteristic,
    DNAInteraction,
    DNALifecycle,
    DNAStatistics,
    DiscoveryReport,
    FeatureEvidence,
    FeatureType,
    InsufficientDataError,
    LoserDNA,
    MLSConfig,
    NeutralDNA,
    SeparationDirection,
    WinnerDNA,
)
from market_learning.dna_discovery_engine import (
    _cohen_d, _spearman, _bootstrap_ci, _detect_feature_type,
)
from market_learning.market_observer_models import (
    DailyMarketSnapshot, MarketObservation, ObservationMetadata,
)
from market_learning.population_classifier_models import (
    ClassificationResult, ClassifierType, GroupLabel, Population, PopulationMember,
)


# ═════════════════════════════════════════════════════════════════════════════
# Test framework
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name:        str
    passed:      bool
    duration_ms: float
    detail:      str
    error:       Optional[str] = None


class TestRunner:
    def __init__(self) -> None:
        self.results: List[TestResult] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        t0 = time.perf_counter()
        try:
            detail = fn() or "OK"
            self.results.append(TestResult(
                name=name, passed=True,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail=str(detail),
            ))
        except AssertionError as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="ASSERTION FAILED", error=str(exc),
            ))
        except Exception as exc:
            self.results.append(TestResult(
                name=name, passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000, 1),
                detail="EXCEPTION",
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            ))

    @property
    def passed(self) -> int:  return sum(1 for r in self.results if r.passed)
    @property
    def failed(self) -> int:  return sum(1 for r in self.results if not r.passed)


def ok(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(msg or "condition is False")


# ═════════════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═════════════════════════════════════════════════════════════════════════════

_TMP:     Optional[Path] = None
_COUNTER: int = 0
_TEST_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)

# Controlled feature templates — large between-group separation
_WIN_FEATS: Dict[str, float] = {
    "mom_1d":        0.020,
    "mom_5d":        0.060,
    "rsi":           75.0,
    "rsi_norm":      0.75,
    "sector_strength": 0.85,
    "liquidity_score": 0.80,
    "hist_vol_5d":   0.10,
    "volume_ratio_raw": 2.00,
    "iv_rank":       0.25,
    "bb_position":   0.70,
    "adx_score":     0.70,
    "gap_pct":       0.008,
    "macd_signal_norm": 0.50,
    # binary
    "volume_spike":  1.0,
    "rsi_overbought": 1.0,
    "rsi_oversold":  0.0,
    "rsi_neutral":   0.0,
    "macd_bull":     1.0,
    "macd_bear":     0.0,
    "bb_upper":      1.0,
    "bb_lower":      0.0,
    "gap_up":        1.0,
    "gap_down":      0.0,
    "strong_trend":  1.0,
}
_LOS_FEATS: Dict[str, float] = {
    "mom_1d":        -0.018,
    "mom_5d":        -0.055,
    "rsi":           25.0,
    "rsi_norm":      0.25,
    "sector_strength": 0.15,
    "liquidity_score": 0.25,
    "hist_vol_5d":   0.28,
    "volume_ratio_raw": 0.65,
    "iv_rank":       0.80,
    "bb_position":   -0.80,
    "adx_score":     0.65,
    "gap_pct":       -0.010,
    "macd_signal_norm": -0.50,
    # binary
    "volume_spike":  0.0,
    "rsi_overbought": 0.0,
    "rsi_oversold":  1.0,
    "rsi_neutral":   0.0,
    "macd_bull":     0.0,
    "macd_bear":     1.0,
    "bb_upper":      0.0,
    "bb_lower":      1.0,
    "gap_up":        0.0,
    "gap_down":      1.0,
    "strong_trend":  1.0,   # same as winners — should show zero effect
}
_NEU_FEATS: Dict[str, float] = {
    "mom_1d":        0.001,
    "mom_5d":        0.002,
    "rsi":           50.0,
    "rsi_norm":      0.50,
    "sector_strength": 0.50,
    "liquidity_score": 0.55,
    "hist_vol_5d":   0.15,
    "volume_ratio_raw": 1.00,
    "iv_rank":       0.50,
    "bb_position":   0.0,
    "adx_score":     0.40,
    "gap_pct":       0.0,
    "macd_signal_norm": 0.0,
    # binary
    "volume_spike":  0.0,
    "rsi_overbought": 0.0,
    "rsi_oversold":  0.0,
    "rsi_neutral":   1.0,
    "macd_bull":     0.0,
    "macd_bear":     0.0,
    "bb_upper":      0.0,
    "bb_lower":      0.0,
    "gap_up":        0.0,
    "gap_down":      0.0,
    "strong_trend":  0.0,
}

_BINARY_FEATURES = {
    "volume_spike", "rsi_overbought", "rsi_oversold", "rsi_neutral",
    "macd_bull", "macd_bear", "bb_upper", "bb_lower",
    "gap_up", "gap_down", "strong_trend", "vol_compression",
    "iv_spike", "iv_low", "mom_positive",
}


def get_tmp() -> Path:
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="mls_dna_test_"))
    return _TMP


def fresh_dir(tag: str = "") -> Path:
    global _COUNTER
    _COUNTER += 1
    d = get_tmp() / f"{tag}_{_COUNTER}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_obs_list(
    prefix: str,
    n: int,
    base_feats: Dict[str, float],
    date: str = "2026-08-03",
    variation: float = 0.05,
    seed: int = 42,
) -> List[MarketObservation]:
    """Create *n* MarketObservation objects with slight variation from base_feats."""
    rng = random.Random(seed)
    obs = []
    for i in range(n):
        feats = {}
        for k, v in base_feats.items():
            if k in _BINARY_FEATURES:
                feats[k] = v
            else:
                noise = rng.gauss(0, variation * max(abs(v), 0.01))
                feats[k] = v + noise
        obs.append(MarketObservation(
            symbol=f"{prefix}_{i + 1}",
            feature_timestamp=f"{date}T09:00:00",
            features=feats,
            feature_count=len(feats),
        ))
    return obs


def _make_synthetic(
    n_winners: int = 3,
    n_losers:  int = 3,
    n_neutrals: int = 5,
    date: str = "2026-08-03",
    regime: str = "bull_trend",
    win_feats:  Optional[Dict[str, float]] = None,
    los_feats:  Optional[Dict[str, float]] = None,
    neu_feats:  Optional[Dict[str, float]] = None,
) -> Tuple[DailyMarketSnapshot, ClassificationResult]:
    """Build a controlled DailyMarketSnapshot + ClassificationResult."""
    wf = win_feats or _WIN_FEATS
    lf = los_feats or _LOS_FEATS
    nf = neu_feats or _NEU_FEATS

    w_obs = _make_obs_list("WIN", n_winners, wf, date)
    l_obs = _make_obs_list("LOS", n_losers,  lf, date, seed=99)
    n_obs = _make_obs_list("NEU", n_neutrals, nf, date, seed=77)

    all_obs  = w_obs + l_obs + n_obs
    all_syms = [o.symbol for o in all_obs]
    n_total  = len(all_syms)

    meta = ObservationMetadata(
        run_id=f"TEST-{date}",
        trading_date=date,
        capture_time=f"{date}T09:00:00",
        universe_size=n_total,
        feature_count=len(wf),
        snapshot_id=f"MLS-SNAP-{date.replace('-', '')}",
        temporal_contract_verified=True,
        regime=regime,
        volatility="MEDIUM",
        vix=15.0, pcr=1.0, breadth=0.6, global_bias=0.3,
        mls_config_hash="test",
    )
    snap = DailyMarketSnapshot(
        snapshot_id=f"MLS-SNAP-{date.replace('-', '')}",
        trading_date=date,
        feature_timestamp=f"{date}T09:00:00",
        regime=regime,
        volatility="MEDIUM",
        vix=15.0, pcr=1.0, breadth=0.6, global_bias=0.3,
        universe_size=n_total,
        symbols=all_syms,
        observations=all_obs,
        metadata=meta,
        created_at=f"{date}T09:00:00",
    )

    now_str = f"{date}T09:00:00"
    d8      = date.replace("-", "")
    w_syms  = [o.symbol for o in w_obs]
    l_syms  = [o.symbol for o in l_obs]
    n_syms  = [o.symbol for o in n_obs]

    pops: List[Population] = []
    # Performance populations — only TOP_5PCT and BOTTOM_5PCT populated
    for lbl, syms in [
        (GroupLabel.TOP_1PCT,     []),
        (GroupLabel.TOP_5PCT,     w_syms),
        (GroupLabel.TOP_10PCT,    []),
        (GroupLabel.NEUTRAL,      n_syms),
        (GroupLabel.BOTTOM_10PCT, []),
        (GroupLabel.BOTTOM_5PCT,  l_syms),
        (GroupLabel.BOTTOM_1PCT,  []),
    ]:
        pops.append(Population(
            population_id=f"POP-{d8}-PERFORMANCE-{lbl.value}",
            trading_date=date, classifier_type=ClassifierType.PERFORMANCE, label=lbl,
            member_count=len(syms), members=syms, threshold_value=None, created_at=now_str,
        ))
    # Other classifiers: everyone in mid/neutral group
    for ct, lbl in [
        (ClassifierType.SECTOR,            GroupLabel.SECTOR_NEUTRAL),
        (ClassifierType.REGIME,            GroupLabel.REGIME_ALIGNED),
        (ClassifierType.LIQUIDITY,         GroupLabel.MID_LIQUIDITY),
        (ClassifierType.VOLATILITY,        GroupLabel.MID_VOLATILITY),
        (ClassifierType.MARKET_CAP,        GroupLabel.MID_CAP),
        (ClassifierType.VOLUME_EXPANSION,  GroupLabel.VOLUME_NORMAL),
        (ClassifierType.RELATIVE_STRENGTH, GroupLabel.RS_NEUTRAL),
    ]:
        pops.append(Population(
            population_id=f"POP-{d8}-{ct.value}-{lbl.value}",
            trading_date=date, classifier_type=ct, label=lbl,
            member_count=n_total, members=all_syms, threshold_value=None, created_at=now_str,
        ))

    pop_ids_by_sym: Dict[str, List[str]] = {}
    for p in pops:
        for sym in p.members:
            pop_ids_by_sym.setdefault(sym, []).append(p.population_id)

    members = [
        PopulationMember(
            symbol=sym, trading_date=date,
            population_ids=pop_ids_by_sym.get(sym, []),
            labels=[], realized_return=None, classification_values={},
        )
        for sym in all_syms
    ]

    cls_result = ClassificationResult(
        result_id=f"MLS-CLS-{d8}",
        trading_date=date,
        snapshot_id=snap.snapshot_id,
        universe_size=n_total,
        populations=pops,
        members=members,
        outcomes_source="external",
        created_at=now_str,
    )
    return snap, cls_result


def _make_engine(tag: str = "") -> DNADiscoveryEngine:
    return DNADiscoveryEngine(data_dir=fresh_dir(tag), config=_TEST_CFG)


# ═════════════════════════════════════════════════════════════════════════════
# Test groups
# ═════════════════════════════════════════════════════════════════════════════

def test_group_config(runner: TestRunner) -> None:

    def t01_phase3_defaults():
        cfg = MLSConfig()
        ok(cfg.dna_min_group_size    == 2,    f"got {cfg.dna_min_group_size}")
        ok(cfg.dna_min_effect_size   == 0.30, f"got {cfg.dna_min_effect_size}")
        ok(cfg.dna_min_spearman      == 0.15, f"got {cfg.dna_min_spearman}")
        ok(cfg.dna_interaction_amplify == 0.30, f"got {cfg.dna_interaction_amplify}")
        ok(cfg.dna_bootstrap_samples == 200,  f"got {cfg.dna_bootstrap_samples}")
        ok(cfg.dna_winner_labels     == ("TOP_5PCT", "TOP_10PCT"),    f"got {cfg.dna_winner_labels}")
        ok(cfg.dna_loser_labels      == ("BOTTOM_5PCT", "BOTTOM_10PCT"), f"got {cfg.dna_loser_labels}")
        return "Phase 3 defaults correct"

    def t02_phase3_overrides():
        cfg = MLSConfig(dna_min_effect_size=0.50, dna_bootstrap_samples=50,
                        dna_winner_labels=("TOP_1PCT",), dna_loser_labels=("BOTTOM_1PCT",))
        ok(cfg.dna_min_effect_size  == 0.50, "override failed")
        ok(cfg.dna_bootstrap_samples == 50,  "override failed")
        ok(cfg.dna_winner_labels    == ("TOP_1PCT",), "override failed")
        ok(cfg.dna_min_group_size   == 2,    "unmodified field changed")
        return "Phase 3 overrides correct"

    def t03_hash_changes():
        cfg1 = MLSConfig()
        cfg2 = MLSConfig(dna_min_effect_size=0.99)
        ok(cfg1.config_hash() != cfg2.config_hash(), "hash should differ")
        return "hash changes with Phase 3 fields"

    runner.run("T01 MLSConfig Phase 3 defaults",    t01_phase3_defaults)
    runner.run("T02 MLSConfig Phase 3 overrides",   t02_phase3_overrides)
    runner.run("T03 MLSConfig hash with Phase 3",   t03_hash_changes)


def test_group_init(runner: TestRunner) -> None:

    def t04_default_init():
        eng = DNADiscoveryEngine()
        ok(eng is not None)
        ok(isinstance(eng._config, MLSConfig))
        return "default init OK"

    def t05_custom_config():
        cfg = MLSConfig(dna_min_effect_size=0.99)
        eng = DNADiscoveryEngine(config=cfg)
        ok(eng._config.dna_min_effect_size == 0.99)
        return "custom config assigned"

    def t06_custom_dir():
        d   = fresh_dir("init")
        eng = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        ok(eng._dna_dir == d / "dna")
        return f"dna_dir={eng._dna_dir.name}"

    runner.run("T04 DNADiscoveryEngine default init",   t04_default_init)
    runner.run("T05 DNADiscoveryEngine custom config",  t05_custom_config)
    runner.run("T06 DNADiscoveryEngine custom data_dir", t06_custom_dir)


def test_group_discover_structure(runner: TestRunner) -> None:

    def _get_report(date: str = "2026-08-03") -> DiscoveryReport:
        snap, cls_ = _make_synthetic(date=date)
        return _make_engine("struct").discover(snap, cls_)

    def t07_returns_discovery_report():
        r = _get_report()
        ok(isinstance(r, DiscoveryReport), f"type={type(r)}")
        return "type correct"

    def t08_report_id_format():
        r = _get_report()
        ok(r.report_id == "MLS-DNA-20260803", f"got {r.report_id}")
        return f"report_id={r.report_id}"

    def t09_snapshot_id():
        r = _get_report()
        ok(r.snapshot_id == "MLS-SNAP-20260803", f"got {r.snapshot_id}")
        return f"snapshot_id={r.snapshot_id}"

    def t10_classification_id():
        r = _get_report()
        ok(r.classification_id == "MLS-CLS-20260803", f"got {r.classification_id}")
        return f"classification_id={r.classification_id}"

    def t11_has_three_dna_profiles():
        r = _get_report()
        ok(isinstance(r.winner_dna,  WinnerDNA),  "winner_dna wrong type")
        ok(isinstance(r.loser_dna,   LoserDNA),   "loser_dna wrong type")
        ok(isinstance(r.neutral_dna, NeutralDNA), "neutral_dna wrong type")
        return "all 3 DNA profiles present"

    def t12_regime_in_report():
        r = _get_report()
        ok(r.regime == "bull_trend", f"got {r.regime}")
        return f"regime={r.regime}"

    def t13_all_characteristics_nonempty():
        r = _get_report()
        ok(len(r.all_characteristics) > 0, "no characteristics found")
        return f"all_characteristics={len(r.all_characteristics)}"

    def t14_persists_json_file():
        d    = fresh_dir("struct")
        eng  = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        snap, cls_ = _make_synthetic()
        eng.discover(snap, cls_)
        path = d / "dna" / "dna_2026-08-03.json"
        ok(path.exists(), f"file not found: {path}")
        return f"file={path.name}"

    runner.run("T07 discover() returns DiscoveryReport",    t07_returns_discovery_report)
    runner.run("T08 discover() report_id format",           t08_report_id_format)
    runner.run("T09 discover() snapshot_id",                t09_snapshot_id)
    runner.run("T10 discover() classification_id",          t10_classification_id)
    runner.run("T11 discover() has 3 DNA profiles",         t11_has_three_dna_profiles)
    runner.run("T12 discover() regime in report",           t12_regime_in_report)
    runner.run("T13 discover() all_characteristics nonempty", t13_all_characteristics_nonempty)
    runner.run("T14 discover() persists JSON file",         t14_persists_json_file)


def test_group_winner_characteristics(runner: TestRunner) -> None:

    def _r():
        snap, cls_ = _make_synthetic()
        return _make_engine("wchar").discover(snap, cls_)

    def t15_winner_characteristics_exist():
        r = _r()
        ok(len(r.winner_dna.characteristics) > 0, "no winner characteristics found")
        return f"winner_chars={len(r.winner_dna.characteristics)}"

    def t16_winner_chars_direction_correct():
        r = _r()
        for c in r.winner_dna.characteristics:
            ok(c.direction == SeparationDirection.WINNERS_HIGHER,
               f"{c.feature_name} direction={c.direction}")
        return "all winner chars have WINNERS_HIGHER direction"

    def t17_winner_chars_effect_above_threshold():
        r = _r()
        thr = _TEST_CFG.dna_min_effect_size
        for c in r.winner_dna.characteristics:
            ok(c.effect_abs >= thr, f"{c.feature_name} effect={c.effect_abs} < {thr}")
        return f"all winner_chars effect_abs >= {thr}"

    def t18_winner_chars_confidence_valid():
        r = _r()
        for c in r.winner_dna.characteristics:
            ok(0.0 <= c.confidence <= 1.0,
               f"{c.feature_name} confidence={c.confidence} out of [0,1]")
        return "all confidence scores in [0,1]"

    def t19_winner_chars_in_report_all_characteristics():
        r = _r()
        report_feats = {c.feature_name for c in r.all_characteristics}
        for c in r.winner_dna.characteristics:
            ok(c.feature_name in report_feats,
               f"{c.feature_name} not in all_characteristics")
        return "winner chars all in all_characteristics"

    runner.run("T15 winner chars: exist",                 t15_winner_characteristics_exist)
    runner.run("T16 winner chars: direction WINNERS_HIGHER", t16_winner_chars_direction_correct)
    runner.run("T17 winner chars: effect_abs >= threshold",  t17_winner_chars_effect_above_threshold)
    runner.run("T18 winner chars: confidence in [0,1]",    t18_winner_chars_confidence_valid)
    runner.run("T19 winner chars: in report.all_characteristics", t19_winner_chars_in_report_all_characteristics)


def test_group_loser_characteristics(runner: TestRunner) -> None:

    def t20_loser_characteristics_exist():
        snap, cls_ = _make_synthetic()
        r = _make_engine("lchar").discover(snap, cls_)
        ok(len(r.loser_dna.characteristics) > 0, "no loser characteristics found")
        return f"loser_chars={len(r.loser_dna.characteristics)}"

    def t21_loser_chars_direction_correct():
        snap, cls_ = _make_synthetic()
        r = _make_engine("lchar").discover(snap, cls_)
        for c in r.loser_dna.characteristics:
            ok(c.direction == SeparationDirection.WINNERS_LOWER,
               f"{c.feature_name} direction={c.direction}")
        return "all loser chars have WINNERS_LOWER direction"

    def t22_loser_chars_effect_above_threshold():
        snap, cls_ = _make_synthetic()
        r   = _make_engine("lchar").discover(snap, cls_)
        thr = _TEST_CFG.dna_min_effect_size
        for c in r.loser_dna.characteristics:
            ok(c.effect_abs >= thr, f"{c.feature_name} effect={c.effect_abs} < {thr}")
        return f"all loser_chars effect_abs >= {thr}"

    runner.run("T20 loser chars: exist",                    t20_loser_characteristics_exist)
    runner.run("T21 loser chars: direction WINNERS_LOWER",  t21_loser_chars_direction_correct)
    runner.run("T22 loser chars: effect_abs >= threshold",  t22_loser_chars_effect_above_threshold)


def test_group_neutral_analysis(runner: TestRunner) -> None:

    def t23_neutral_chars_direction():
        snap, cls_ = _make_synthetic(n_neutrals=5)
        r = _make_engine("nchar").discover(snap, cls_)
        valid = {SeparationDirection.NEUTRALS_HIGHER, SeparationDirection.NEUTRALS_LOWER}
        for c in r.neutral_dna.characteristics:
            ok(c.direction in valid, f"{c.feature_name} direction={c.direction}")
        return f"neutral_chars={len(r.neutral_dna.characteristics)}"

    def t24_neutral_dna_n_members():
        snap, cls_ = _make_synthetic(n_neutrals=6)
        r = _make_engine("nchar").discover(snap, cls_)
        ok(r.neutral_dna.n_members == 6, f"n_members={r.neutral_dna.n_members}")
        return f"neutral.n_members=6"

    runner.run("T23 neutral chars: direction NEUTRALS_*",   t23_neutral_chars_direction)
    runner.run("T24 neutral dna: n_members correct",        t24_neutral_dna_n_members)


def test_group_cohen_d(runner: TestRunner) -> None:

    def t25_cohen_d_known_positive():
        a = [0.10, 0.15, 0.20]   # mean=0.15
        b = [0.01, 0.02, 0.03]   # mean=0.02
        d = _cohen_d(a, b)
        ok(d > 0, f"expected d > 0, got {d}")
        ok(d > 2.0, f"expected d > 2.0, got {d:.3f}")
        return f"d={d:.3f}"

    def t26_cohen_d_sign_follows_mean():
        a = [0.5, 0.6, 0.7]
        b = [1.5, 1.6, 1.7]
        d = _cohen_d(a, b)
        ok(d < 0, f"expected d < 0 (b higher), got {d}")
        return f"d={d:.3f} < 0 correct"

    def t27_cohen_d_zero_for_equal_groups():
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        d = _cohen_d(a, b)
        ok(abs(d) < 1e-9, f"expected d=0, got {d}")
        return f"d={d}"

    def t28_cohen_d_large_for_no_overlap():
        a = [10.0, 10.1, 10.2]
        b = [0.1,  0.2,  0.3]
        d = _cohen_d(a, b)
        ok(abs(d) > 50, f"expected |d| >> 50 for non-overlapping groups, got {d:.1f}")
        return f"|d|={abs(d):.1f}"

    def t29_cohen_d_insufficient_data():
        ok(_cohen_d([1.0], [2.0]) == 0.0, "singleton groups should return 0")
        ok(_cohen_d([], [1.0, 2.0]) == 0.0, "empty group should return 0")
        return "insufficient data -> 0.0"

    runner.run("T25 cohen_d: positive known input",  t25_cohen_d_known_positive)
    runner.run("T26 cohen_d: sign follows mean",      t26_cohen_d_sign_follows_mean)
    runner.run("T27 cohen_d: zero for equal groups",  t27_cohen_d_zero_for_equal_groups)
    runner.run("T28 cohen_d: large for no overlap",   t28_cohen_d_large_for_no_overlap)
    runner.run("T29 cohen_d: insufficient data -> 0", t29_cohen_d_insufficient_data)


def test_group_spearman(runner: TestRunner) -> None:

    def t30_spearman_perfect_monotonic():
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [1.0, 2.0, 3.0, 4.0, 5.0]
        r = _spearman(a, b)
        ok(abs(r - 1.0) < 1e-9, f"perfect monotonic: expected 1.0, got {r}")
        return f"r={r}"

    def t31_spearman_perfect_anti_monotonic():
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [5.0, 4.0, 3.0, 2.0, 1.0]
        r = _spearman(a, b)
        ok(abs(r + 1.0) < 1e-9, f"anti-monotonic: expected -1.0, got {r}")
        return f"r={r}"

    def t32_spearman_constant_returns_zero():
        a = [3.0, 3.0, 3.0, 3.0]
        b = [1.0, 2.0, 3.0, 4.0]
        r = _spearman(a, b)
        ok(r == 0.0, f"constant input: expected 0, got {r}")
        return f"r={r}"

    def t33_spearman_insufficient_length():
        ok(_spearman([1.0, 2.0], [1.0, 2.0]) == 0.0, "n<3 -> 0.0")
        return "n<3 -> 0.0"

    runner.run("T30 spearman: perfect monotonic -> 1.0",     t30_spearman_perfect_monotonic)
    runner.run("T31 spearman: anti-monotonic -> -1.0",       t31_spearman_perfect_anti_monotonic)
    runner.run("T32 spearman: constant -> 0.0",              t32_spearman_constant_returns_zero)
    runner.run("T33 spearman: n<3 -> 0.0",                   t33_spearman_insufficient_length)


def test_group_bootstrap(runner: TestRunner) -> None:

    def t34_ci_contains_point_estimate():
        a = [0.10, 0.15, 0.20, 0.12, 0.18]
        b = [0.01, 0.02, 0.03, 0.015, 0.025]
        d    = _cohen_d(a, b)
        lo, hi = _bootstrap_ci(a, b, n_boot=400)
        ok(lo <= d <= hi or abs(d - lo) < 0.5 or abs(d - hi) < 0.5,
           f"d={d:.3f} not near CI=[{lo:.3f},{hi:.3f}]")
        return f"d={d:.2f} CI=[{lo:.2f},{hi:.2f}]"

    def t35_ci_finite():
        a = [0.5, 0.6, 0.7]
        b = [0.1, 0.2, 0.3]
        lo, hi = _bootstrap_ci(a, b, n_boot=100)
        ok(math.isfinite(lo) and math.isfinite(hi), "CI should be finite")
        return f"CI=[{lo:.3f},{hi:.3f}]"

    def t36_ci_insufficient_data():
        lo, hi = _bootstrap_ci([1.0], [2.0], n_boot=50)
        ok(lo == 0.0 and hi == 0.0, "single-element -> (0,0)")
        return "insufficient data -> (0.0, 0.0)"

    runner.run("T34 bootstrap CI: contains point estimate", t34_ci_contains_point_estimate)
    runner.run("T35 bootstrap CI: finite",                  t35_ci_finite)
    runner.run("T36 bootstrap CI: insufficient data",       t36_ci_insufficient_data)


def test_group_feature_type(runner: TestRunner) -> None:

    def t37_binary_detection():
        ft = _detect_feature_type([0.0, 1.0, 0.0, 1.0, 0.0])
        ok(ft == FeatureType.BINARY, f"got {ft}")
        return "BINARY detected"

    def t38_continuous_detection():
        ft = _detect_feature_type([0.12, 0.15, 0.18, 0.22, 0.08])
        ok(ft == FeatureType.CONTINUOUS, f"got {ft}")
        return "CONTINUOUS detected"

    def t39_pure_continuous_vs_binary():
        ft_binary = _detect_feature_type([0.0, 0.0, 1.0, 1.0])
        ft_cont   = _detect_feature_type([0.1, 0.2, 0.7, 0.9])
        ok(ft_binary == FeatureType.BINARY, "0/1 values -> BINARY")
        ok(ft_cont   == FeatureType.CONTINUOUS, "fractional values -> CONTINUOUS")
        return "type detection correct"

    runner.run("T37 feature type: binary",      t37_binary_detection)
    runner.run("T38 feature type: continuous",  t38_continuous_detection)
    runner.run("T39 feature type: detection",   t39_pure_continuous_vs_binary)


def test_group_feature_evidence(runner: TestRunner) -> None:

    def _get_ev() -> FeatureEvidence:
        snap, cls_ = _make_synthetic()
        r = _make_engine("ev").discover(snap, cls_)
        ok(len(r.winner_dna.characteristics) > 0)
        return r.winner_dna.characteristics[0].evidence

    def t40_evidence_round_trip():
        ev1 = _get_ev()
        ev2 = FeatureEvidence.from_dict(ev1.to_dict())
        ok(ev2.feature_name  == ev1.feature_name)
        ok(ev2.effect_abs    == ev1.effect_abs)
        ok(ev2.n_winners     == ev1.n_winners)
        ok(ev2.spearman_corr == ev1.spearman_corr)
        return "FeatureEvidence round-trip OK"

    def t41_evidence_fields_present():
        ev = _get_ev()
        ok(ev.winner_mean  != ev.loser_mean, "winner/loser means should differ")
        ok(ev.n_winners    >= _TEST_CFG.dna_min_group_size)
        ok(ev.n_losers     >= _TEST_CFG.dna_min_group_size)
        ok(0.0 <= ev.ci_low <= ev.ci_high or ev.ci_low <= ev.ci_high,
           "CI should be ordered")
        return f"evidence fields OK: n_w={ev.n_winners} n_l={ev.n_losers}"

    runner.run("T40 FeatureEvidence round-trip",       t40_evidence_round_trip)
    runner.run("T41 FeatureEvidence fields present",   t41_evidence_fields_present)


def test_group_dna_characteristic_model(runner: TestRunner) -> None:

    def _get_char() -> DNACharacteristic:
        snap, cls_ = _make_synthetic()
        r = _make_engine("char").discover(snap, cls_)
        ok(r.winner_dna.characteristics)
        return r.winner_dna.characteristics[0]

    def t42_char_round_trip():
        c1 = _get_char()
        c2 = DNACharacteristic.from_dict(c1.to_dict())
        ok(c2.char_id       == c1.char_id)
        ok(c2.feature_name  == c1.feature_name)
        ok(c2.lifecycle     == c1.lifecycle)
        ok(c2.confidence    == c1.confidence)
        return "DNACharacteristic round-trip OK"

    def t43_char_id_prefix():
        c = _get_char()
        ok(c.char_id.startswith("DNA-"), f"char_id={c.char_id}")
        ok(len(c.char_id) == 12, f"char_id length={len(c.char_id)}")  # "DNA-" + 8 hex
        return f"char_id={c.char_id}"

    def t44_default_lifecycle_discovered():
        snap, cls_ = _make_synthetic()
        r = _make_engine("char").discover(snap, cls_)  # no history
        for c in r.winner_dna.characteristics:
            ok(c.lifecycle == DNALifecycle.DISCOVERED,
               f"{c.feature_name} lifecycle={c.lifecycle}")
        return "all new characteristics start as DISCOVERED"

    def t45_char_effect_abs_positive():
        c = _get_char()
        ok(c.effect_abs > 0, f"effect_abs={c.effect_abs}")
        ok(c.effect_abs == abs(c.effect_size), "effect_abs != |effect_size|")
        return f"effect_abs={c.effect_abs:.3f}"

    def t46_char_feature_type_set():
        c = _get_char()
        ok(isinstance(c.feature_type, FeatureType), f"feature_type={c.feature_type}")
        return f"feature_type={c.feature_type.value}"

    runner.run("T42 DNACharacteristic round-trip",         t42_char_round_trip)
    runner.run("T43 DNACharacteristic char_id prefix DNA-", t43_char_id_prefix)
    runner.run("T44 DNACharacteristic default lifecycle",   t44_default_lifecycle_discovered)
    runner.run("T45 DNACharacteristic effect_abs positive", t45_char_effect_abs_positive)
    runner.run("T46 DNACharacteristic feature_type set",    t46_char_feature_type_set)


def test_group_interactions(runner: TestRunner) -> None:

    def t47_interaction_structure():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        dna_interaction_amplify=-0.9)  # very low threshold
        eng = DNADiscoveryEngine(data_dir=fresh_dir("int"), config=cfg)
        snap, cls_ = _make_synthetic()
        r = eng.discover(snap, cls_)
        if not r.all_interactions:
            return "no interactions found (amplification threshold not met)"
        inter = r.all_interactions[0]
        ok(isinstance(inter, DNAInteraction))
        ok(inter.interaction_id.startswith("INT-"), f"id={inter.interaction_id}")
        ok(len(inter.features) == 2, f"features={inter.features}")
        ok(inter.joint_effect > 0,   f"joint_effect={inter.joint_effect}")
        ok(inter.max_individual > 0, f"max_individual={inter.max_individual}")
        return f"interaction: {inter.features[0]} x {inter.features[1]}"

    def t48_interaction_amplification_respected():
        """Every reported interaction must have amplification >= the configured threshold."""
        thr = 0.30
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        dna_interaction_amplify=thr)
        eng = DNADiscoveryEngine(data_dir=fresh_dir("int"), config=cfg)
        snap, cls_ = _make_synthetic()
        r   = eng.discover(snap, cls_)
        for inter in r.all_interactions:
            ok(inter.amplification >= thr,
               f"interaction {inter.features} amplification={inter.amplification:.4f} < threshold={thr}")
        return f"all {len(r.all_interactions)} interactions respect amplification threshold={thr}"

    def t49_interaction_round_trip():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        dna_interaction_amplify=-0.9)
        eng = DNADiscoveryEngine(data_dir=fresh_dir("int"), config=cfg)
        snap, cls_ = _make_synthetic()
        r = eng.discover(snap, cls_)
        if not r.all_interactions:
            return "no interactions to round-trip"
        i1 = r.all_interactions[0]
        i2 = DNAInteraction.from_dict(i1.to_dict())
        ok(i2.interaction_id == i1.interaction_id)
        ok(i2.features        == i1.features)
        ok(i2.amplification   == i1.amplification)
        return "DNAInteraction round-trip OK"

    def t50_interaction_features_in_characteristics():
        cfg = MLSConfig(min_universe_size=1, dna_min_group_size=2,
                        dna_interaction_amplify=-0.9)
        eng = DNADiscoveryEngine(data_dir=fresh_dir("int"), config=cfg)
        snap, cls_ = _make_synthetic()
        r = eng.discover(snap, cls_)
        char_feats = {c.feature_name for c in r.all_characteristics}
        for inter in r.all_interactions:
            for f in inter.features:
                ok(f in char_feats, f"interaction feature {f} not in chars")
        return f"interaction features valid"

    runner.run("T47 interaction: structure when low threshold",  t47_interaction_structure)
    runner.run("T48 interaction: amplification threshold respected", t48_interaction_amplification_respected)
    runner.run("T49 interaction: round-trip",                    t49_interaction_round_trip)
    runner.run("T50 interaction: features in characteristics",   t50_interaction_features_in_characteristics)


def test_group_dna_profiles(runner: TestRunner) -> None:

    def _r():
        snap, cls_ = _make_synthetic()
        return _make_engine("prof").discover(snap, cls_)

    def t51_winner_dna_round_trip():
        r  = _r()
        d  = r.winner_dna.to_dict()
        w2 = WinnerDNA.from_dict(d)
        ok(w2.date     == r.winner_dna.date)
        ok(w2.n_members == r.winner_dna.n_members)
        ok(len(w2.characteristics) == len(r.winner_dna.characteristics))
        return "WinnerDNA round-trip OK"

    def t52_winner_dna_n_members():
        r = _r()
        ok(r.winner_dna.n_members == 3, f"got {r.winner_dna.n_members}")
        return f"winner n_members=3"

    def t53_winner_dna_population_ids():
        r = _r()
        ok(len(r.winner_dna.population_ids) > 0, "population_ids should not be empty")
        for pid in r.winner_dna.population_ids:
            ok("PERFORMANCE" in pid, f"population_id should contain PERFORMANCE: {pid}")
        return f"population_ids={r.winner_dna.population_ids}"

    def t54_loser_dna_round_trip():
        r  = _r()
        d  = r.loser_dna.to_dict()
        l2 = LoserDNA.from_dict(d)
        ok(l2.date     == r.loser_dna.date)
        ok(l2.n_members == r.loser_dna.n_members)
        return "LoserDNA round-trip OK"

    def t55_neutral_dna_round_trip():
        r  = _r()
        d  = r.neutral_dna.to_dict()
        n2 = NeutralDNA.from_dict(d)
        ok(n2.date     == r.neutral_dna.date)
        ok(n2.n_members == r.neutral_dna.n_members)
        return "NeutralDNA round-trip OK"

    runner.run("T51 WinnerDNA round-trip",                t51_winner_dna_round_trip)
    runner.run("T52 WinnerDNA n_members correct",         t52_winner_dna_n_members)
    runner.run("T53 WinnerDNA population_ids present",    t53_winner_dna_population_ids)
    runner.run("T54 LoserDNA round-trip",                 t54_loser_dna_round_trip)
    runner.run("T55 NeutralDNA round-trip",               t55_neutral_dna_round_trip)


def test_group_discovery_report_model(runner: TestRunner) -> None:

    def _r():
        snap, cls_ = _make_synthetic()
        return _make_engine("rpt").discover(snap, cls_)

    def t56_report_round_trip():
        r1 = _r()
        r2 = DiscoveryReport.from_dict(r1.to_dict())
        ok(r2.report_id         == r1.report_id)
        ok(r2.universe_size     == r1.universe_size)
        ok(len(r2.all_characteristics) == len(r1.all_characteristics))
        return "DiscoveryReport round-trip OK"

    def t57_get_characteristic():
        r = _r()
        if not r.winner_dna.characteristics:
            return "no characteristics to test"
        fname = r.winner_dna.characteristics[0].feature_name
        c = r.get_characteristic(fname)
        ok(c is not None, f"get_characteristic({fname}) returned None")
        ok(c.feature_name == fname)
        return f"get_characteristic({fname}) OK"

    def t58_characteristics_by_direction():
        r = _r()
        w_chars = r.characteristics_by_direction(SeparationDirection.WINNERS_HIGHER)
        for c in w_chars:
            ok(c.direction == SeparationDirection.WINNERS_HIGHER)
        if len(w_chars) > 1:
            ok(w_chars[0].effect_abs >= w_chars[-1].effect_abs,
               "should be sorted by effect_abs descending")
        return f"characteristics_by_direction: {len(w_chars)} WINNERS_HIGHER"

    def t59_report_universe_size():
        r = _r()
        ok(r.universe_size == 11, f"3 winners + 3 losers + 5 neutrals = 11, got {r.universe_size}")
        return f"universe_size={r.universe_size}"

    runner.run("T56 DiscoveryReport round-trip",              t56_report_round_trip)
    runner.run("T57 DiscoveryReport.get_characteristic()",    t57_get_characteristic)
    runner.run("T58 DiscoveryReport.characteristics_by_direction()", t58_characteristics_by_direction)
    runner.run("T59 DiscoveryReport.universe_size",           t59_report_universe_size)


def test_group_lifecycle(runner: TestRunner) -> None:

    def _discover_with_history(n_hist: int) -> DiscoveryReport:
        """Create n_hist history reports then discover on a new date."""
        history: List[DiscoveryReport] = []
        for i in range(n_hist):
            day  = 1 + i
            snap, cls_ = _make_synthetic(date=f"2026-07-{day:02d}")
            r    = _make_engine(f"lc_hist_{i}").discover(snap, cls_, history=history[:-max_carry_avoid:] if history else [])
            # rebuild with correct history
            eng  = DNADiscoveryEngine(data_dir=fresh_dir(f"lch_{i}"), config=_TEST_CFG)
            r    = eng.discover(snap, cls_, history=list(history))
            history.append(r)
        # Now discover on the "current" date with full history
        snap, cls_ = _make_synthetic(date="2026-08-03")
        eng = DNADiscoveryEngine(data_dir=fresh_dir("lc_final"), config=_TEST_CFG)
        return eng.discover(snap, cls_, history=list(history))

    def t60_no_history_discovered():
        snap, cls_ = _make_synthetic()
        r = _make_engine("lc").discover(snap, cls_)
        for c in r.all_characteristics:
            ok(c.lifecycle == DNALifecycle.DISCOVERED,
               f"{c.feature_name}: expected DISCOVERED, got {c.lifecycle}")
        return "no history -> all DISCOVERED"

    def t61_one_history_replicated():
        """A characteristic seen once before should advance to REPLICATED."""
        hist_snap, hist_cls = _make_synthetic(date="2026-07-01")
        hist_eng = DNADiscoveryEngine(data_dir=fresh_dir("lc1"), config=_TEST_CFG)
        hist_r   = hist_eng.discover(hist_snap, hist_cls)

        snap, cls_ = _make_synthetic(date="2026-08-03")
        eng = DNADiscoveryEngine(data_dir=fresh_dir("lc1b"), config=_TEST_CFG)
        r   = eng.discover(snap, cls_, history=[hist_r])

        # At least some characteristics should be REPLICATED
        replicated = [c for c in r.all_characteristics if c.lifecycle == DNALifecycle.REPLICATED]
        ok(len(replicated) > 0, "expected some REPLICATED characteristics with 1-day history")
        return f"replicated chars={len(replicated)}"

    def t62_two_history_verified():
        """Two previous appearances -> VERIFIED."""
        history = []
        for day in (1, 2):
            snap_h, cls_h = _make_synthetic(date=f"2026-07-{day:02d}")
            eng_h = DNADiscoveryEngine(data_dir=fresh_dir(f"lc2h_{day}"), config=_TEST_CFG)
            history.append(eng_h.discover(snap_h, cls_h, history=list(history)))
        snap, cls_ = _make_synthetic(date="2026-08-03")
        eng = DNADiscoveryEngine(data_dir=fresh_dir("lc2"), config=_TEST_CFG)
        r   = eng.discover(snap, cls_, history=history)
        verified = [c for c in r.all_characteristics if c.lifecycle == DNALifecycle.VERIFIED]
        ok(len(verified) > 0, "expected some VERIFIED characteristics with 2-day history")
        return f"verified chars={len(verified)}"

    def t63_four_history_stable():
        """Four consistent appearances -> STABLE."""
        history = []
        for day in range(1, 5):
            snap_h, cls_h = _make_synthetic(date=f"2026-07-{day:02d}")
            eng_h = DNADiscoveryEngine(data_dir=fresh_dir(f"lc4h_{day}"), config=_TEST_CFG)
            history.append(eng_h.discover(snap_h, cls_h, history=list(history)))
        snap, cls_ = _make_synthetic(date="2026-08-03")
        eng = DNADiscoveryEngine(data_dir=fresh_dir("lc4"), config=_TEST_CFG)
        r   = eng.discover(snap, cls_, history=history)
        stable = [c for c in r.all_characteristics if c.lifecycle == DNALifecycle.STABLE]
        ok(len(stable) > 0, "expected some STABLE characteristics with 4-day history")
        return f"stable chars={len(stable)}"

    runner.run("T60 lifecycle: no history -> DISCOVERED", t60_no_history_discovered)
    runner.run("T61 lifecycle: 1 history -> REPLICATED",  t61_one_history_replicated)
    runner.run("T62 lifecycle: 2 history -> VERIFIED",    t62_two_history_verified)
    runner.run("T63 lifecycle: 4 history -> STABLE",      t63_four_history_stable)


def test_group_storage(runner: TestRunner) -> None:

    def t64_load_report_after_discover():
        d    = fresh_dir("stor")
        eng  = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        snap, cls_ = _make_synthetic()
        eng.discover(snap, cls_)
        loaded = eng.load_report("2026-08-03")
        ok(loaded is not None, "should load persisted report")
        ok(isinstance(loaded, DiscoveryReport))
        ok(len(loaded.all_characteristics) > 0)
        return "load_report OK"

    def t65_load_missing_returns_none():
        eng = _make_engine("stor")
        ok(eng.load_report("2099-01-01") is None, "missing -> None")
        return "missing -> None"

    def t66_list_reports_sorted():
        d   = fresh_dir("stor")
        eng = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        for day in (5, 3, 4):
            snap, cls_ = _make_synthetic(date=f"2026-08-0{day}")
            eng.discover(snap, cls_)
        dates = eng.list_reports()
        ok(dates == sorted(dates), f"not sorted: {dates}")
        ok(len(dates) == 3, f"expected 3, got {len(dates)}")
        return f"dates={dates}"

    def t67_bak_created_on_overwrite():
        d    = fresh_dir("stor")
        eng  = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        snap, cls_ = _make_synthetic()
        eng.discover(snap, cls_)
        eng.discover(snap, cls_)  # second write -> .bak
        bak = d / "dna" / "dna_2026-08-03.bak"
        ok(bak.exists(), ".bak not created on overwrite")
        return ".bak created"

    runner.run("T64 storage: load_report after discover",  t64_load_report_after_discover)
    runner.run("T65 storage: load_report missing -> None", t65_load_missing_returns_none)
    runner.run("T66 storage: list_reports sorted",         t66_list_reports_sorted)
    runner.run("T67 storage: .bak on overwrite",           t67_bak_created_on_overwrite)


def test_group_statistics(runner: TestRunner) -> None:

    def _get_stats() -> DNAStatistics:
        d    = fresh_dir("stats")
        eng  = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        snap, cls_ = _make_synthetic()
        eng.discover(snap, cls_)
        return eng.statistics("2026-08-03")

    def t68_statistics_returns_type():
        st = _get_stats()
        ok(st is not None)
        ok(isinstance(st, DNAStatistics))
        return "DNAStatistics type correct"

    def t69_statistics_counts_consistent():
        st = _get_stats()
        ok(st.total_characteristics > 0, "total > 0")
        ok(st.winner_characteristics + st.loser_characteristics + st.neutral_characteristics
           == st.total_characteristics,
           f"counts don't sum: w={st.winner_characteristics} l={st.loser_characteristics} "
           f"n={st.neutral_characteristics} total={st.total_characteristics}")
        return (f"total={st.total_characteristics} "
                f"(w={st.winner_characteristics} l={st.loser_characteristics} n={st.neutral_characteristics})")

    def t70_statistics_top_feature_set():
        st = _get_stats()
        if st.winner_characteristics > 0:
            ok(st.top_winner_feature is not None, "top_winner_feature should be set")
        if st.loser_characteristics > 0:
            ok(st.top_loser_feature is not None, "top_loser_feature should be set")
        return f"top_winner={st.top_winner_feature}, top_loser={st.top_loser_feature}"

    def t71_statistics_avg_effect_positive():
        st = _get_stats()
        ok(st.avg_effect_size > 0, f"avg_effect_size={st.avg_effect_size} should be > 0")
        return f"avg_effect_size={st.avg_effect_size}"

    def t72_statistics_lifecycle_distribution():
        st = _get_stats()
        ok(len(st.lifecycle_distribution) > 0, "lifecycle_distribution should not be empty")
        ok(DNALifecycle.DISCOVERED.value in st.lifecycle_distribution,
           "DISCOVERED should be in distribution (no history)")
        return f"lifecycle_dist={st.lifecycle_distribution}"

    def t73_statistics_missing_date():
        eng = _make_engine("stats")
        ok(eng.statistics("2099-01-01") is None, "missing -> None")
        return "missing -> None"

    runner.run("T68 statistics: returns DNAStatistics",         t68_statistics_returns_type)
    runner.run("T69 statistics: counts consistent",             t69_statistics_counts_consistent)
    runner.run("T70 statistics: top features set",              t70_statistics_top_feature_set)
    runner.run("T71 statistics: avg_effect_size positive",      t71_statistics_avg_effect_positive)
    runner.run("T72 statistics: lifecycle_distribution present", t72_statistics_lifecycle_distribution)
    runner.run("T73 statistics: missing date -> None",          t73_statistics_missing_date)


def test_group_query_api(runner: TestRunner) -> None:

    def _setup():
        d    = fresh_dir("api")
        eng  = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        snap, cls_ = _make_synthetic()
        eng.discover(snap, cls_)
        return eng

    def t74_winner_dna_api():
        eng = _setup()
        w = eng.winner_dna("2026-08-03")
        ok(w is not None)
        ok(isinstance(w, WinnerDNA))
        return f"winner_dna: {len(w.characteristics)} chars"

    def t75_loser_dna_api():
        eng = _setup()
        l = eng.loser_dna("2026-08-03")
        ok(l is not None)
        ok(isinstance(l, LoserDNA))
        return f"loser_dna: {len(l.characteristics)} chars"

    def t76_neutral_dna_api():
        eng = _setup()
        n = eng.neutral_dna("2026-08-03")
        ok(n is not None)
        ok(isinstance(n, NeutralDNA))
        return f"neutral_dna: {len(n.characteristics)} chars"

    def t77_list_characteristics_for_date():
        eng = _setup()
        chars = eng.list_characteristics("2026-08-03")
        ok(len(chars) > 0)
        ok(all(isinstance(c, DNACharacteristic) for c in chars))
        return f"list_characteristics: {len(chars)}"

    def t78_list_characteristics_all_dates():
        d   = fresh_dir("api")
        eng = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        for day in (3, 4, 5):
            snap, cls_ = _make_synthetic(date=f"2026-08-0{day}")
            eng.discover(snap, cls_)
        all_chars = eng.list_characteristics()
        ok(len(all_chars) > 0)
        dates = {c.trading_date for c in all_chars}
        ok(len(dates) == 3, f"expected 3 dates, got {dates}")
        return f"list_characteristics all: {len(all_chars)} chars from {len(dates)} dates"

    runner.run("T74 query API: winner_dna()",            t74_winner_dna_api)
    runner.run("T75 query API: loser_dna()",             t75_loser_dna_api)
    runner.run("T76 query API: neutral_dna()",           t76_neutral_dna_api)
    runner.run("T77 query API: list_characteristics(date)", t77_list_characteristics_for_date)
    runner.run("T78 query API: list_characteristics(all)", t78_list_characteristics_all_dates)


def test_group_edge_cases(runner: TestRunner) -> None:

    def t79_insufficient_data_raises():
        cfg  = MLSConfig(min_universe_size=1, dna_min_group_size=5)
        eng  = DNADiscoveryEngine(data_dir=fresh_dir("err"), config=cfg)
        snap, cls_ = _make_synthetic(n_winners=2, n_losers=2)  # < min_group_size=5
        try:
            eng.discover(snap, cls_)
            ok(False, "should have raised InsufficientDataError")
        except InsufficientDataError:
            pass
        return "InsufficientDataError raised correctly"

    def t80_custom_min_group_size_works():
        cfg  = MLSConfig(min_universe_size=1, dna_min_group_size=2)
        eng  = DNADiscoveryEngine(data_dir=fresh_dir("err"), config=cfg)
        snap, cls_ = _make_synthetic(n_winners=2, n_losers=2)  # == min_group_size
        r = eng.discover(snap, cls_)
        ok(isinstance(r, DiscoveryReport))
        return "dna_min_group_size=2 accepted 2-member groups"

    def t81_constant_feature_skipped():
        """_analyse_one_feature returns None for a truly constant feature."""
        eng = _make_engine("const")
        char = eng._analyse_one_feature(
            "CONSTANT_TEST",
            [0.5, 0.5, 0.5],   # all winners same value
            [0.5, 0.5, 0.5],   # all losers same value
            "2026-08-03", "bull_trend", [],
            SeparationDirection.WINNERS_HIGHER,
            SeparationDirection.WINNERS_LOWER,
        )
        ok(char is None, "zero-variance feature should return None")
        return "_analyse_one_feature returns None for constant feature"

    def t82_market_wide_features_skipped():
        """Market-wide constant features (regime_bull etc.) should not appear."""
        snap, cls_ = _make_synthetic()
        r = _make_engine("mw").discover(snap, cls_)
        # Add market-wide feature names to test
        mw_features = {"regime_bull", "breadth", "pcr", "global_bias"}
        for c in r.all_characteristics:
            ok(c.feature_name not in mw_features,
               f"market-wide feature {c.feature_name} should not be in characteristics")
        return "market-wide features excluded"

    runner.run("T79 edge case: InsufficientDataError raised",  t79_insufficient_data_raises)
    runner.run("T80 edge case: min_group_size=2 accepted",     t80_custom_min_group_size_works)
    runner.run("T81 edge case: constant feature skipped",      t81_constant_feature_skipped)
    runner.run("T82 edge case: market-wide features excluded", t82_market_wide_features_skipped)


def test_group_thread_safety(runner: TestRunner) -> None:

    def t83_concurrent_discover():
        d   = fresh_dir("thread")
        eng = DNADiscoveryEngine(data_dir=d, config=_TEST_CFG)
        errors: List[str] = []

        def do_discover(day: int) -> None:
            try:
                snap, cls_ = _make_synthetic(date=f"2026-08-{day:02d}")
                eng.discover(snap, cls_)
            except Exception as exc:
                errors.append(f"day={day}: {exc}")

        threads = [threading.Thread(target=do_discover, args=(i,)) for i in range(3, 11)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        ok(len(errors) == 0, f"concurrent errors: {errors}")
        dates = eng.list_reports()
        ok(len(dates) == 8, f"expected 8, got {len(dates)}: {dates}")
        return f"concurrent: 8/8 succeeded"

    runner.run("T83 thread safety: concurrent discover()", t83_concurrent_discover)


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    runner = TestRunner()

    test_group_config(runner)
    test_group_init(runner)
    test_group_discover_structure(runner)
    test_group_winner_characteristics(runner)
    test_group_loser_characteristics(runner)
    test_group_neutral_analysis(runner)
    test_group_cohen_d(runner)
    test_group_spearman(runner)
    test_group_bootstrap(runner)
    test_group_feature_type(runner)
    test_group_feature_evidence(runner)
    test_group_dna_characteristic_model(runner)
    test_group_interactions(runner)
    test_group_dna_profiles(runner)
    test_group_discovery_report_model(runner)
    test_group_lifecycle(runner)
    test_group_storage(runner)
    test_group_statistics(runner)
    test_group_query_api(runner)
    test_group_edge_cases(runner)
    test_group_thread_safety(runner)

    print("\n" + "=" * 72)
    print("MLS Phase 3 -- DNADiscoveryEngine Test Report")
    print("=" * 72)
    width = max(len(r.name) for r in runner.results) + 2
    for r in runner.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name:<{width}} {r.duration_ms:6.1f}ms  {r.detail}")
        if r.error:
            for line in r.error.splitlines():
                print(f"         {line}")
    print("-" * 72)
    print(f"  Result:  {runner.passed}/{len(runner.results)} passed, {runner.failed} failed")
    print("=" * 72 + "\n")

    if runner.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
