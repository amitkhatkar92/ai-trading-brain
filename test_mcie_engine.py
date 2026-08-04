"""
test_mcie_engine.py — MLS Phase 5A: Market Context Intelligence Engine.

90-test suite.  Run with:
    .venv\Scripts\python.exe test_mcie_engine.py

Uses the same minimal test framework as Phases 3, 4, and 5.
No pytest dependency.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.market_data import (
    FIIDIIData,
    MarketSnapshot,
    RegimeLabel,
    SectorFlow,
    VolatilityLevel,
)
from market_learning import (
    MCIEngine,
    MLSConfig,
    MarketContext,
    ContextComponent,
    ContextDrift,
    ContextHistory,
    ContextStatistics,
    MCIEError,
    MCIEInputError,
)
from market_learning.mcie_engine import (
    _clamp,
    _mean,
    _make_context_id,
    _score_regime,
    _score_volatility,
    _score_liquidity,
    _score_sector,
    _score_institutional,
    _score_global,
    _score_risk,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Minimal test framework
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name:    str
    passed:  bool
    message: str
    ms:      float


class TestRunner:
    def __init__(self):
        self._results: List[TestResult] = []

    def run(self, name: str, fn: Callable) -> None:
        import time
        t0 = time.monotonic()
        try:
            label = fn()
            ms    = (time.monotonic() - t0) * 1000
            self._results.append(TestResult(name, True, str(label or ""), ms))
        except AssertionError as e:
            ms = (time.monotonic() - t0) * 1000
            self._results.append(TestResult(name, False, f"ASSERTION FAILED\n          {e}", ms))
        except Exception as e:
            import traceback
            ms = (time.monotonic() - t0) * 1000
            tb = traceback.format_exc()
            self._results.append(TestResult(name, False, f"EXCEPTION\n{tb}", ms))

    def report(self) -> int:
        print("=" * 72)
        for r in self._results:
            tag    = "[PASS]" if r.passed else "[FAIL]"
            label  = r.message.split("\n")[0][:50] if r.passed else r.message
            if r.passed:
                print(f"  {tag} {r.name:<45} {r.ms:5.1f}ms  {label}")
            else:
                print(f"  {tag} {r.name:<45} {r.ms:5.1f}ms  {label}")
                for extra in r.message.split("\n")[1:]:
                    if extra.strip():
                        print(f"          {extra}")
        total   = len(self._results)
        passed  = sum(1 for r in self._results if r.passed)
        failed  = total - passed
        print("-" * 72)
        print(f"  Result:  {passed}/{total} passed, {failed} failed")
        print("=" * 72)
        return failed


def ok(cond: bool, msg: str = "") -> None:
    assert cond, msg


# ═══════════════════════════════════════════════════════════════════════════════
# Test helpers
# ═══════════════════════════════════════════════════════════════════════════════

_TEST_CFG = MLSConfig(min_universe_size=1, dna_min_group_size=2)


def _make_snapshot(
    regime=RegimeLabel.BULL_TREND,
    vix: float = 15.0,
    pcr: float = 1.0,
    breadth: float = 0.6,
    global_sentiment: float = 0.2,
    global_bias: str = "neutral",
    fii_net: Optional[float] = None,
    dii_net: Optional[float] = None,
    sector_flows: Optional[List[SectorFlow]] = None,
    ts: str = "2026-08-04T09:00:00",
) -> MarketSnapshot:
    """Build a MarketSnapshot suitable for MCIE tests."""
    dt = datetime.fromisoformat(ts)
    fii_dii = None
    if fii_net is not None or dii_net is not None:
        fn = float(fii_net or 0.0)
        dn = float(dii_net or 0.0)
        fii_dii = FIIDIIData(
            date=dt,
            fii_buy=max(0.0, fn),
            fii_sell=max(0.0, -fn),
            dii_buy=max(0.0, dn),
            dii_sell=max(0.0, -dn),
        )
    return MarketSnapshot(
        timestamp=dt,
        indices={},
        regime=regime,
        volatility=VolatilityLevel.MEDIUM,
        vix=vix,
        fii_dii=fii_dii,
        sector_flows=sector_flows or [],
        market_breadth=breadth,
        pcr=pcr,
        global_bias=global_bias,
        global_sentiment_score=global_sentiment,
    )


def _make_sector_flows(n_pos: int = 3, n_neg: int = 0) -> List[SectorFlow]:
    flows = []
    for i in range(n_pos):
        flows.append(SectorFlow(sector_name=f"Sector_P{i}", flow_score=0.70, rank=i + 1))
    for i in range(n_neg):
        flows.append(SectorFlow(sector_name=f"Sector_N{i}", flow_score=-0.50, rank=n_pos + i + 1))
    return flows


def _engine(cfg: Optional[MLSConfig] = None) -> MCIEngine:
    return MCIEngine(config=cfg or _TEST_CFG)


def _favorable_snapshot() -> MarketSnapshot:
    return _make_snapshot(
        regime=RegimeLabel.BULL_TREND, vix=10.0, pcr=1.0, breadth=0.90,
        global_sentiment=0.80, global_bias="bullish",
        fii_net=2000.0, dii_net=500.0,
        sector_flows=_make_sector_flows(5, 0),
    )


def _adverse_snapshot() -> MarketSnapshot:
    return _make_snapshot(
        regime=RegimeLabel.VOLATILE, vix=50.0, pcr=0.30, breadth=0.10,
        global_sentiment=-0.90, global_bias="bearish",
        fii_net=-3000.0, dii_net=-2000.0,
        sector_flows=_make_sector_flows(0, 4),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

def run_all() -> int:
    runner = TestRunner()

    # ── T01–T05: MLSConfig Phase 5A defaults ─────────────────────────────────

    def t01_cfg_w_regime():
        cfg = MLSConfig()
        ok(cfg.mcie_w_regime == 0.20, f"mcie_w_regime={cfg.mcie_w_regime}")
        return f"mcie_w_regime={cfg.mcie_w_regime}"

    def t02_cfg_w_risk():
        cfg = MLSConfig()
        ok(cfg.mcie_w_risk == 0.06, f"mcie_w_risk={cfg.mcie_w_risk}")
        return f"mcie_w_risk={cfg.mcie_w_risk}"

    def t03_cfg_weights_sum_to_1():
        cfg = MLSConfig()
        total = (cfg.mcie_w_regime + cfg.mcie_w_volatility + cfg.mcie_w_liquidity
                 + cfg.mcie_w_participation + cfg.mcie_w_sector + cfg.mcie_w_institutional
                 + cfg.mcie_w_global + cfg.mcie_w_risk)
        ok(abs(total - 1.0) < 1e-9, f"weights sum={total:.9f}")
        return f"8 weights sum={total:.9f}"

    def t04_cfg_thresholds():
        cfg = MLSConfig()
        ok(cfg.mcie_vix_low   == 15.0)
        ok(cfg.mcie_high_context_threshold == 0.65)
        ok(cfg.mcie_low_context_threshold  == 0.35)
        ok(cfg.mcie_drift_threshold        == 0.10)
        ok(cfg.mcie_pcr_balanced_lo        == 0.80)
        ok(cfg.mcie_pcr_balanced_hi        == 1.20)
        return "thresholds correct"

    def t05_cfg_overrides():
        cfg = MLSConfig(mcie_w_regime=0.25, mcie_high_context_threshold=0.60)
        ok(cfg.mcie_w_regime == 0.25)
        ok(cfg.mcie_high_context_threshold == 0.60)
        return "overrides applied"

    runner.run("T01 cfg mcie_w_regime",             t01_cfg_w_regime)
    runner.run("T02 cfg mcie_w_risk",               t02_cfg_w_risk)
    runner.run("T03 8 weights sum to 1.0",           t03_cfg_weights_sum_to_1)
    runner.run("T04 cfg thresholds correct",         t04_cfg_thresholds)
    runner.run("T05 cfg custom overrides",           t05_cfg_overrides)

    # ── T06–T08: Engine instantiation ────────────────────────────────────────

    def t06_engine_default_init():
        eng = MCIEngine()
        ok(eng is not None)
        return "default init OK"

    def t07_engine_custom_config():
        cfg = MLSConfig(mcie_w_regime=0.25)
        eng = MCIEngine(config=cfg)
        ok(eng._cfg.mcie_w_regime == 0.25)
        return "custom config stored"

    def t08_engine_starts_empty():
        eng = MCIEngine()
        ok(eng.current_context() is None, "should start empty")
        ok(len(eng.history().contexts) == 0, "history should be empty")
        return "engine starts with empty history"

    runner.run("T06 Engine default init",            t06_engine_default_init)
    runner.run("T07 Engine custom config",           t07_engine_custom_config)
    runner.run("T08 Engine starts with empty hist",  t08_engine_starts_empty)

    # ── T09–T13: MarketContext structure ─────────────────────────────────────

    def t09_context_id_prefix():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(ctx.context_id.startswith("MCE-"), f"id={ctx.context_id}")
        return f"context_id={ctx.context_id}"

    def t10_context_evaluation_date():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot(ts="2026-08-04T09:00:00"))
        ok(ctx.evaluation_date == "2026-08-04", f"date={ctx.evaluation_date}")
        return f"evaluation_date={ctx.evaluation_date}"

    def t11_context_score_bounds():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(0.0 <= ctx.context_score <= 1.0, f"score={ctx.context_score}")
        return f"context_score={ctx.context_score:.6f}"

    def t12_context_has_8_components():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(len(ctx.components) == 8, f"components={len(ctx.components)}")
        return f"components={len(ctx.components)}"

    def t13_context_summary_nonempty():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(len(ctx.summary) > 0, "summary should not be empty")
        return f"summary length={len(ctx.summary)}"

    runner.run("T09 context_id prefix MCE-",         t09_context_id_prefix)
    runner.run("T10 evaluation_date from snapshot",  t10_context_evaluation_date)
    runner.run("T11 context_score in [0,1]",         t11_context_score_bounds)
    runner.run("T12 has exactly 8 components",       t12_context_has_8_components)
    runner.run("T13 summary nonempty",               t13_context_summary_nonempty)

    # ── T14–T18: ContextComponent structure ──────────────────────────────────

    _EXPECTED_NAMES = {
        "regime_context", "volatility_context", "liquidity_context",
        "participation_context", "sector_context", "institutional_context",
        "global_context", "risk_context",
    }

    def t14_component_names():
        eng   = _engine()
        ctx   = eng.evaluate(_make_snapshot())
        names = {c.name for c in ctx.components}
        ok(names == _EXPECTED_NAMES, f"names={names}")
        return "all 8 component names present"

    def t15_component_scores_in_range():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        for c in ctx.components:
            ok(0.0 <= c.score <= 1.0, f"{c.name}.score={c.score}")
        return "all component scores in [0,1]"

    def t16_component_weighted_score_formula():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        for c in ctx.components:
            ok(abs(c.weighted_score - c.score * c.weight) < 1e-9,
               f"{c.name}: {c.weighted_score} != {c.score}*{c.weight}")
        return "weighted_score = score × weight for all"

    def t17_component_weights_match_config():
        cfg = _TEST_CFG
        eng = MCIEngine(config=cfg)
        ctx = eng.evaluate(_make_snapshot())
        wmap = {c.name: c.weight for c in ctx.components}
        ok(wmap["regime_context"]        == cfg.mcie_w_regime)
        ok(wmap["volatility_context"]    == cfg.mcie_w_volatility)
        ok(wmap["liquidity_context"]     == cfg.mcie_w_liquidity)
        ok(wmap["participation_context"] == cfg.mcie_w_participation)
        ok(wmap["sector_context"]        == cfg.mcie_w_sector)
        ok(wmap["institutional_context"] == cfg.mcie_w_institutional)
        ok(wmap["global_context"]        == cfg.mcie_w_global)
        ok(wmap["risk_context"]          == cfg.mcie_w_risk)
        return "all component weights match MLSConfig"

    def t18_component_explanations_nonempty():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        for c in ctx.components:
            ok(len(c.explanation) > 0, f"{c.name} explanation empty")
        return "all 8 explanations nonempty"

    runner.run("T14 all 8 component names present",  t14_component_names)
    runner.run("T15 all component scores in [0,1]",  t15_component_scores_in_range)
    runner.run("T16 weighted_score = score*weight",  t16_component_weighted_score_formula)
    runner.run("T17 component weights match config", t17_component_weights_match_config)
    runner.run("T18 all explanations nonempty",      t18_component_explanations_nonempty)

    # ── T19–T22: Regime context scoring ──────────────────────────────────────

    def _regime_score(regime: RegimeLabel) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_make_snapshot(regime=regime))
        return next(c.score for c in ctx.components if c.name == "regime_context")

    def t19_regime_bull_high():
        s = _regime_score(RegimeLabel.BULL_TREND)
        ok(s >= 0.80, f"BULL_TREND regime_context={s}")
        return f"BULL_TREND regime_context={s:.2f} ≥ 0.80"

    def t20_regime_range_medium():
        s = _regime_score(RegimeLabel.RANGE_MARKET)
        ok(s <= 0.60, f"RANGE_MARKET regime_context={s}")
        return f"RANGE_MARKET regime_context={s:.2f} ≤ 0.60"

    def t21_regime_volatile_low():
        s = _regime_score(RegimeLabel.VOLATILE)
        ok(s <= 0.35, f"VOLATILE regime_context={s}")
        return f"VOLATILE regime_context={s:.2f} ≤ 0.35"

    def t22_regime_bear_between_range_and_bull():
        s_bear  = _regime_score(RegimeLabel.BEAR_MARKET)
        s_range = _regime_score(RegimeLabel.RANGE_MARKET)
        s_bull  = _regime_score(RegimeLabel.BULL_TREND)
        ok(s_range < s_bear < s_bull,
           f"range={s_range:.2f} bear={s_bear:.2f} bull={s_bull:.2f}")
        return f"BEAR regime_context={s_bear:.2f} between RANGE and BULL"

    runner.run("T19 BULL_TREND regime_context ≥ 0.80",  t19_regime_bull_high)
    runner.run("T20 RANGE_MARKET regime_context ≤ 0.60", t20_regime_range_medium)
    runner.run("T21 VOLATILE regime_context ≤ 0.35",    t21_regime_volatile_low)
    runner.run("T22 BEAR between RANGE and BULL",        t22_regime_bear_between_range_and_bull)

    # ── T23–T27: Volatility context scoring ──────────────────────────────────

    def _vol_score(vix: float) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_make_snapshot(vix=vix))
        return next(c.score for c in ctx.components if c.name == "volatility_context")

    def t23_vix_low_high_score():
        s = _vol_score(10.0)
        ok(s >= 0.85, f"VIX=10 volatility_context={s}")
        return f"VIX=10 → volatility_context={s:.2f} ≥ 0.85"

    def t24_vix_medium():
        s = _vol_score(20.0)
        ok(0.50 <= s <= 0.80, f"VIX=20 volatility_context={s}")
        return f"VIX=20 → volatility_context={s:.2f} in [0.50, 0.80]"

    def t25_vix_high_low_score():
        s = _vol_score(30.0)
        ok(s <= 0.40, f"VIX=30 volatility_context={s}")
        return f"VIX=30 → volatility_context={s:.2f} ≤ 0.40"

    def t26_vix_extreme():
        s = _vol_score(50.0)
        ok(s <= 0.15, f"VIX=50 volatility_context={s}")
        return f"VIX=50 → volatility_context={s:.2f} ≤ 0.15"

    def t27_vix_monotone():
        s10, s20, s30, s50 = _vol_score(10), _vol_score(20), _vol_score(30), _vol_score(50)
        ok(s10 >= s20 >= s30 >= s50,
           f"VIX monotone: {s10:.2f} ≥ {s20:.2f} ≥ {s30:.2f} ≥ {s50:.2f}")
        return f"monotone: VIX10={s10:.2f} VIX20={s20:.2f} VIX30={s30:.2f} VIX50={s50:.2f}"

    runner.run("T23 VIX=10 volatility_context ≥ 0.85", t23_vix_low_high_score)
    runner.run("T24 VIX=20 volatility_context [0.50,0.80]", t24_vix_medium)
    runner.run("T25 VIX=30 volatility_context ≤ 0.40", t25_vix_high_low_score)
    runner.run("T26 VIX=50 volatility_context ≤ 0.15", t26_vix_extreme)
    runner.run("T27 VIX monotone lower → higher score", t27_vix_monotone)

    # ── T28–T32: Liquidity context scoring ───────────────────────────────────

    def _liq_score(snap: MarketSnapshot) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(snap)
        return next(c.score for c in ctx.components if c.name == "liquidity_context")

    def t28_liquidity_high_fii():
        snap_hi = _make_snapshot(breadth=0.9, fii_net=2000.0, dii_net=1000.0)
        snap_lo = _make_snapshot(breadth=0.4, fii_net=-1000.0)
        ok(_liq_score(snap_hi) > _liq_score(snap_lo))
        return f"hi={_liq_score(snap_hi):.3f} > lo={_liq_score(snap_lo):.3f}"

    def t29_liquidity_no_fii_uses_breadth():
        snap = _make_snapshot(breadth=0.7)   # no fii_net → fii_dii=None
        s = _liq_score(snap)
        ok(abs(s - 0.7) < 1e-9, f"expected 0.7, got {s}")
        return f"no FII → liquidity=breadth={s:.3f}"

    def t30_liquidity_negative_fii_lower():
        snap_neutral  = _make_snapshot(breadth=0.6)
        snap_negative = _make_snapshot(breadth=0.6, fii_net=-2000.0, dii_net=-500.0)
        ok(_liq_score(snap_negative) < _liq_score(snap_neutral),
           f"neg={_liq_score(snap_negative):.3f} neutral={_liq_score(snap_neutral):.3f}")
        return f"negative FII → lower liquidity"

    def t31_liquidity_in_range():
        for vv in [0.0, 0.3, 0.6, 1.0]:
            s = _liq_score(_make_snapshot(breadth=vv))
            ok(0.0 <= s <= 1.0, f"breadth={vv} liquidity={s}")
        return "liquidity_context always in [0,1]"

    def t32_liquidity_in_components():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        names = [c.name for c in ctx.components]
        ok("liquidity_context" in names)
        return "liquidity_context present in components"

    runner.run("T28 high breadth+FII → high liquidity", t28_liquidity_high_fii)
    runner.run("T29 no FII → liquidity = breadth",     t29_liquidity_no_fii_uses_breadth)
    runner.run("T30 negative FII → lower liquidity",   t30_liquidity_negative_fii_lower)
    runner.run("T31 liquidity_context in [0,1]",       t31_liquidity_in_range)
    runner.run("T32 liquidity_context in components",  t32_liquidity_in_components)

    # ── T33–T37: Participation context scoring ────────────────────────────────

    def _part_score(breadth: float) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_make_snapshot(breadth=breadth))
        return next(c.score for c in ctx.components if c.name == "participation_context")

    def t33_participation_full():
        ok(abs(_part_score(1.0) - 1.0) < 1e-9, f"breadth=1 → {_part_score(1.0)}")
        return "breadth=1.0 → participation=1.0"

    def t34_participation_zero():
        ok(abs(_part_score(0.0) - 0.0) < 1e-9, f"breadth=0 → {_part_score(0.0)}")
        return "breadth=0.0 → participation=0.0"

    def t35_participation_half():
        ok(abs(_part_score(0.5) - 0.5) < 1e-9, f"breadth=0.5 → {_part_score(0.5)}")
        return "breadth=0.5 → participation=0.5"

    def t36_participation_monotone():
        s03, s05, s07, s09 = _part_score(0.3), _part_score(0.5), _part_score(0.7), _part_score(0.9)
        ok(s03 < s05 < s07 < s09, f"{s03} < {s05} < {s07} < {s09}")
        return f"participation monotone: {s03:.2f}<{s05:.2f}<{s07:.2f}<{s09:.2f}"

    def t37_participation_in_range():
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            s = _part_score(v)
            ok(0.0 <= s <= 1.0)
        return "participation_context always in [0,1]"

    runner.run("T33 breadth=1.0 → participation=1.0", t33_participation_full)
    runner.run("T34 breadth=0.0 → participation=0.0", t34_participation_zero)
    runner.run("T35 breadth=0.5 → participation=0.5", t35_participation_half)
    runner.run("T36 participation monotone",           t36_participation_monotone)
    runner.run("T37 participation in [0,1]",           t37_participation_in_range)

    # ── T38–T42: Sector context scoring ──────────────────────────────────────

    def _sector_score(snap: MarketSnapshot) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(snap)
        return next(c.score for c in ctx.components if c.name == "sector_context")

    def t38_sector_all_positive():
        s = _sector_score(_make_snapshot(sector_flows=_make_sector_flows(5, 0)))
        ok(s == 1.0, f"all positive → {s}")
        return f"all positive sectors → sector_context={s:.4f}"

    def t39_sector_empty_neutral():
        s = _sector_score(_make_snapshot(sector_flows=[]))
        ok(abs(s - 0.5) < 1e-9, f"empty → {s}")
        return f"empty sector flows → sector_context={s:.4f}"

    def t40_sector_all_negative():
        s = _sector_score(_make_snapshot(sector_flows=_make_sector_flows(0, 4)))
        ok(s == 0.0, f"all negative → {s}")
        return f"all negative sectors → sector_context={s:.4f}"

    def t41_sector_mixed():
        # 2 positive, 2 negative → 0.5
        s = _sector_score(_make_snapshot(sector_flows=_make_sector_flows(2, 2)))
        ok(abs(s - 0.5) < 1e-9, f"2/4 positive → {s}")
        return f"2/4 positive sectors → sector_context={s:.4f}"

    def t42_sector_in_range():
        for n_pos in [0, 1, 3, 5]:
            s = _sector_score(_make_snapshot(sector_flows=_make_sector_flows(n_pos, 5 - n_pos)))
            ok(0.0 <= s <= 1.0)
        return "sector_context always in [0,1]"

    runner.run("T38 all positive sectors → 1.0",   t38_sector_all_positive)
    runner.run("T39 empty sector flows → 0.5",      t39_sector_empty_neutral)
    runner.run("T40 all negative sectors → 0.0",   t40_sector_all_negative)
    runner.run("T41 mixed sectors → 0.5",           t41_sector_mixed)
    runner.run("T42 sector_context in [0,1]",       t42_sector_in_range)

    # ── T43–T47: Institutional context scoring ────────────────────────────────

    def _inst_score(fii: Optional[float] = None, dii: Optional[float] = None) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_make_snapshot(fii_net=fii, dii_net=dii))
        return next(c.score for c in ctx.components if c.name == "institutional_context")

    def t43_institutional_positive_fii():
        s = _inst_score(fii=3000.0, dii=0.0)
        ok(s >= 0.80, f"FII+3000 → {s}")
        return f"FII=+3000 → institutional={s:.4f} ≥ 0.80"

    def t44_institutional_negative_fii():
        s = _inst_score(fii=-3000.0, dii=0.0)
        ok(s <= 0.30, f"FII-3000 → {s}")
        return f"FII=-3000 → institutional={s:.4f} ≤ 0.30"

    def t45_institutional_no_data():
        s = _inst_score()    # fii=None, dii=None
        ok(abs(s - 0.5) < 1e-9, f"no FII → {s}")
        return f"no FII/DII data → institutional={s:.4f}"

    def t46_institutional_both_buying():
        s_fii_only = _inst_score(fii=1500.0, dii=0.0)
        s_both     = _inst_score(fii=1500.0, dii=1500.0)
        ok(s_both > s_fii_only, f"both={s_both:.3f} > fii_only={s_fii_only:.3f}")
        return f"FII+DII buying → {s_both:.3f} > FII only={s_fii_only:.3f}"

    def t47_institutional_in_range():
        for v in [-3000, 0, 3000]:
            s = _inst_score(fii=float(v), dii=0.0)
            ok(0.0 <= s <= 1.0, f"fii={v} institutional={s}")
        return "institutional_context always in [0,1]"

    runner.run("T43 FII=+3000 → institutional ≥ 0.80",  t43_institutional_positive_fii)
    runner.run("T44 FII=-3000 → institutional ≤ 0.30",  t44_institutional_negative_fii)
    runner.run("T45 no FII → institutional = 0.5",      t45_institutional_no_data)
    runner.run("T46 FII+DII buying > FII alone",         t46_institutional_both_buying)
    runner.run("T47 institutional_context in [0,1]",     t47_institutional_in_range)

    # ── T48–T52: Global context scoring ──────────────────────────────────────

    def _global_score(gss: float, bias: str = "neutral") -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(
            _make_snapshot(global_sentiment=gss, global_bias=bias)
        )
        return next(c.score for c in ctx.components if c.name == "global_context")

    def t48_global_positive():
        s = _global_score(1.0)
        ok(s >= 0.95, f"sentiment=1.0 → {s}")
        return f"global_sentiment=1.0 → global_context={s:.4f} ≥ 0.95"

    def t49_global_negative():
        s = _global_score(-1.0)
        ok(s <= 0.05, f"sentiment=-1.0 → {s}")
        return f"global_sentiment=-1.0 → global_context={s:.4f} ≤ 0.05"

    def t50_global_neutral():
        s = _global_score(0.0, bias="neutral")
        ok(abs(s - 0.5) < 1e-9, f"sentiment=0.0 → {s}")
        return f"global_sentiment=0.0 → global_context={s:.4f} = 0.5"

    def t51_global_bias_effect():
        s_bull = _global_score(0.0, bias="bullish")
        s_bear = _global_score(0.0, bias="bearish")
        ok(s_bull > s_bear, f"bullish={s_bull:.4f} bearish={s_bear:.4f}")
        return f"bullish bias ({s_bull:.4f}) > bearish bias ({s_bear:.4f})"

    def t52_global_in_range():
        for v in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            s = _global_score(v)
            ok(0.0 <= s <= 1.0, f"sentiment={v} global={s}")
        return "global_context always in [0,1]"

    runner.run("T48 global_sentiment=1.0 → ≥ 0.95",   t48_global_positive)
    runner.run("T49 global_sentiment=-1.0 → ≤ 0.05",  t49_global_negative)
    runner.run("T50 global_sentiment=0.0 → 0.5",      t50_global_neutral)
    runner.run("T51 bullish bias > bearish bias",      t51_global_bias_effect)
    runner.run("T52 global_context in [0,1]",          t52_global_in_range)

    # ── T53–T57: Risk context scoring ────────────────────────────────────────

    def _risk_score(pcr: float, vix: float = 15.0) -> float:
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_make_snapshot(pcr=pcr, vix=vix))
        return next(c.score for c in ctx.components if c.name == "risk_context")

    def t53_risk_balanced_pcr():
        s = _risk_score(pcr=0.9, vix=15.0)
        ok(s >= 0.70, f"PCR=0.9 VIX=15 → risk={s}")
        return f"balanced PCR=0.9 → risk_context={s:.4f} ≥ 0.70"

    def t54_risk_low_pcr():
        s_balanced = _risk_score(pcr=0.9, vix=15.0)
        s_low      = _risk_score(pcr=0.5, vix=15.0)
        ok(s_low < s_balanced, f"low pcr={s_low:.3f} >= balanced={s_balanced:.3f}")
        return f"PCR=0.5 risk={s_low:.3f} < balanced risk={s_balanced:.3f}"

    def t55_risk_high_pcr():
        s_balanced = _risk_score(pcr=0.9, vix=15.0)
        s_high     = _risk_score(pcr=2.0, vix=15.0)
        ok(s_high < s_balanced, f"high pcr={s_high:.3f} >= balanced={s_balanced:.3f}")
        return f"PCR=2.0 risk={s_high:.3f} < balanced risk={s_balanced:.3f}"

    def t56_risk_high_vix_low_pcr():
        s = _risk_score(pcr=0.5, vix=42.0)   # VIX>40 → vix_score=0.05
        ok(s <= 0.40, f"PCR=0.5 VIX=42 → risk={s}")
        return f"high VIX + low PCR → risk_context={s:.4f} ≤ 0.40"

    def t57_risk_in_range():
        for pcr, vix in [(0.3, 50), (1.0, 15), (2.5, 10)]:
            s = _risk_score(pcr, vix)
            ok(0.0 <= s <= 1.0, f"pcr={pcr} vix={vix} risk={s}")
        return "risk_context always in [0,1]"

    runner.run("T53 balanced PCR → risk_context ≥ 0.70", t53_risk_balanced_pcr)
    runner.run("T54 PCR=0.5 → risk lower than balanced", t54_risk_low_pcr)
    runner.run("T55 PCR=2.0 → risk lower than balanced", t55_risk_high_pcr)
    runner.run("T56 high VIX + low PCR → risk ≤ 0.40",   t56_risk_high_vix_low_pcr)
    runner.run("T57 risk_context in [0,1]",               t57_risk_in_range)

    # ── T58–T62: context_score and confidence ────────────────────────────────

    def t58_context_score_is_weighted_sum():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        weighted_sum = sum(c.weighted_score for c in ctx.components)
        ok(abs(ctx.context_score - weighted_sum) < 1e-9,
           f"score={ctx.context_score} sum={weighted_sum}")
        return f"context_score = weighted sum ({ctx.context_score:.6f})"

    def t59_context_score_always_in_range():
        for snap in [_make_snapshot(), _favorable_snapshot(), _adverse_snapshot()]:
            ctx = MCIEngine(config=_TEST_CFG).evaluate(snap)
            ok(0.0 <= ctx.context_score <= 1.0, f"score={ctx.context_score}")
        return "context_score in [0,1] for all scenarios"

    def t60_favorable_inputs_high_score():
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_favorable_snapshot())
        ok(ctx.context_score > 0.65, f"favorable → score={ctx.context_score:.3f}")
        return f"all-favorable → context_score={ctx.context_score:.3f} > 0.65"

    def t61_adverse_inputs_low_score():
        ctx = MCIEngine(config=_TEST_CFG).evaluate(_adverse_snapshot())
        ok(ctx.context_score < 0.35, f"adverse → score={ctx.context_score:.3f}")
        return f"all-adverse → context_score={ctx.context_score:.3f} < 0.35"

    def t62_confidence_in_range():
        eng = _engine()
        for snap in [_make_snapshot(), _favorable_snapshot(), _adverse_snapshot()]:
            ctx = MCIEngine(config=_TEST_CFG).evaluate(snap)
            ok(0.0 <= ctx.confidence <= 1.0, f"confidence={ctx.confidence}")
        return "confidence in [0,1] for all scenarios"

    runner.run("T58 context_score = weighted sum",      t58_context_score_is_weighted_sum)
    runner.run("T59 context_score always in [0,1]",     t59_context_score_always_in_range)
    runner.run("T60 favorable inputs → score > 0.65",   t60_favorable_inputs_high_score)
    runner.run("T61 adverse inputs → score < 0.35",     t61_adverse_inputs_low_score)
    runner.run("T62 confidence in [0,1]",               t62_confidence_in_range)

    # ── T63–T67: evaluate / current_context / history ────────────────────────

    def t63_evaluate_returns_context():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(isinstance(ctx, MarketContext), type(ctx).__name__)
        return f"evaluate() → MarketContext (score={ctx.context_score:.3f})"

    def t64_current_context_is_last():
        eng = _engine()
        ctx1 = eng.evaluate(_make_snapshot(vix=10.0))
        ctx2 = eng.evaluate(_make_snapshot(vix=30.0))
        ok(eng.current_context() is ctx2)
        return "current_context() returns most recent"

    def t65_history_contains_all():
        eng = _engine()
        for vix in [10.0, 20.0, 30.0]:
            eng.evaluate(_make_snapshot(vix=vix))
        h = eng.history()
        ok(len(h.contexts) == 3, f"history size={len(h.contexts)}")
        return f"history() returns {len(h.contexts)} contexts"

    def t66_evaluate_twice_history_two():
        eng = _engine()
        eng.evaluate(_make_snapshot())
        eng.evaluate(_make_snapshot(vix=25.0))
        ok(len(eng.history().contexts) == 2)
        return "2 evaluations → history size=2"

    def t67_evaluate_does_not_mutate_snapshot():
        snap = _make_snapshot(vix=15.0, breadth=0.6)
        vix_before = snap.vix
        pcr_before = snap.pcr
        _engine().evaluate(snap)
        ok(snap.vix == vix_before and snap.pcr == pcr_before, "snapshot mutated!")
        return "evaluate() does not mutate snapshot"

    runner.run("T63 evaluate() returns MarketContext",    t63_evaluate_returns_context)
    runner.run("T64 current_context() = last evaluated",  t64_current_context_is_last)
    runner.run("T65 history() contains all contexts",     t65_history_contains_all)
    runner.run("T66 evaluate() twice → history size 2",   t66_evaluate_twice_history_two)
    runner.run("T67 evaluate() does not mutate snapshot", t67_evaluate_does_not_mutate_snapshot)

    # ── T68–T72: drift() ─────────────────────────────────────────────────────

    def t68_drift_none_before_two():
        eng = _engine()
        ok(eng.drift() is None, "drift before first eval should be None")
        eng.evaluate(_make_snapshot())
        ok(eng.drift() is None, "drift after exactly 1 eval should be None")
        return "drift() is None with < 2 evaluations"

    def t69_drift_after_two():
        eng = _engine()
        eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE, vix=40.0))
        d = eng.drift()
        ok(d is not None)
        ok(isinstance(d, ContextDrift))
        return f"drift() → ContextDrift after 2 evaluations"

    def t70_drift_score_delta():
        eng = _engine()
        ctx1 = eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND, vix=12.0))
        ctx2 = eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE, vix=45.0))
        d = eng.drift()
        expected = round(ctx2.context_score - ctx1.context_score, 6)
        ok(abs(d.score_delta - expected) < 1e-9,
           f"delta={d.score_delta} expected={expected}")
        return f"score_delta={d.score_delta:+.4f} = ctx2 - ctx1"

    def t71_drift_regime_changed():
        eng = _engine()
        eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE))
        ok(eng.drift().regime_changed is True, "regime should have changed")
        # same regime → False
        eng2 = _engine()
        eng2.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        eng2.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        ok(eng2.drift().regime_changed is False)
        return "regime_changed=True when regime changes, False otherwise"

    def t72_drift_magnitude_bounds():
        eng = _engine()
        eng.evaluate(_make_snapshot())
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE, vix=50.0))
        d = eng.drift()
        ok(0.0 <= d.drift_magnitude <= 1.0, f"drift_magnitude={d.drift_magnitude}")
        return f"drift_magnitude={d.drift_magnitude:.4f} in [0,1]"

    runner.run("T68 drift() None with < 2 evals",    t68_drift_none_before_two)
    runner.run("T69 drift() ContextDrift after 2",   t69_drift_after_two)
    runner.run("T70 drift().score_delta correct",    t70_drift_score_delta)
    runner.run("T71 drift().regime_changed correct", t71_drift_regime_changed)
    runner.run("T72 drift_magnitude in [0,1]",       t72_drift_magnitude_bounds)

    # ── T73–T77: statistics() ────────────────────────────────────────────────

    def t73_stats_total_count():
        eng = _engine()
        for _ in range(5):
            eng.evaluate(_make_snapshot())
        ok(eng.statistics().total_evaluations == 5)
        return "statistics().total_evaluations=5"

    def t74_stats_avg_score():
        eng = _engine()
        snap = _make_snapshot()
        for _ in range(3):
            eng.evaluate(snap)
        stats = eng.statistics()
        expected = eng.current_context().context_score
        ok(abs(stats.avg_context_score - expected) < 1e-6,
           f"avg={stats.avg_context_score} expected={expected}")
        return f"avg_context_score={stats.avg_context_score:.6f}"

    def t75_stats_high_count():
        cfg = MLSConfig(mcie_high_context_threshold=0.50)
        eng = MCIEngine(config=cfg)
        for _ in range(3):
            eng.evaluate(_favorable_snapshot())
        for _ in range(2):
            eng.evaluate(_adverse_snapshot())
        stats = eng.statistics()
        ok(stats.high_context_count == 3, f"high_count={stats.high_context_count}")
        return f"high_context_count=3 (threshold=0.50)"

    def t76_stats_regime_distribution():
        eng = _engine()
        eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE))
        dist = eng.statistics().regime_distribution
        ok(dist.get("bull_trend") == 2, f"bull_trend={dist.get('bull_trend')}")
        ok(dist.get("volatile")   == 1, f"volatile={dist.get('volatile')}")
        return f"regime_distribution={dist}"

    def t77_stats_empty_safe():
        eng = _engine()
        stats = eng.statistics()
        ok(stats.total_evaluations == 0)
        ok(stats.avg_context_score  == 0.0)
        ok(stats.regime_distribution == {})
        return "statistics() on empty engine → safe defaults"

    runner.run("T73 statistics() total_evaluations",   t73_stats_total_count)
    runner.run("T74 statistics() avg_context_score",   t74_stats_avg_score)
    runner.run("T75 statistics() high_context_count",  t75_stats_high_count)
    runner.run("T76 statistics() regime_distribution", t76_stats_regime_distribution)
    runner.run("T77 statistics() empty → safe defaults", t77_stats_empty_safe)

    # ── T78–T82: Explainability and stability ────────────────────────────────

    def t78_component_evidence_has_raw_inputs():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot(vix=18.0))
        vola = next(c for c in ctx.components if c.name == "volatility_context")
        ok("vix" in vola.evidence, f"evidence keys={list(vola.evidence)}")
        ok(abs(vola.evidence["vix"] - 18.0) < 1e-9)
        return f"volatility evidence contains vix={vola.evidence['vix']}"

    def t79_context_id_deterministic():
        snap = _make_snapshot(ts="2026-08-04T09:00:00")
        id1 = MCIEngine(config=_TEST_CFG).evaluate(snap).context_id
        id2 = MCIEngine(config=_TEST_CFG).evaluate(snap).context_id
        ok(id1 == id2, f"id1={id1} id2={id2}")
        return f"context_id={id1} is deterministic"

    def t80_stability_half_on_first():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot())
        ok(abs(ctx.stability - 0.5) < 1e-9, f"first stability={ctx.stability}")
        return f"first evaluation → stability={ctx.stability}"

    def t81_stability_high_same_snapshot():
        eng  = _engine()
        snap = _make_snapshot()
        eng.evaluate(snap)
        ctx2 = eng.evaluate(snap)
        ok(ctx2.stability >= 0.99, f"second eval (same snap) stability={ctx2.stability}")
        return f"same snapshot twice → stability={ctx2.stability:.4f} ≈ 1.0"

    def t82_summary_mentions_regime():
        eng = _engine()
        ctx = eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND))
        ok("bull_trend" in ctx.summary, f"summary={ctx.summary[:80]}")
        return f"summary mentions regime: ✓"

    runner.run("T78 component evidence has raw inputs",    t78_component_evidence_has_raw_inputs)
    runner.run("T79 context_id deterministic",             t79_context_id_deterministic)
    runner.run("T80 stability=0.5 on first evaluation",   t80_stability_half_on_first)
    runner.run("T81 stability≈1.0 for identical snapshot", t81_stability_high_same_snapshot)
    runner.run("T82 summary mentions regime",              t82_summary_mentions_regime)

    # ── T83–T87: ContextDrift ────────────────────────────────────────────────

    def t83_drift_dates_set():
        eng = _engine()
        eng.evaluate(_make_snapshot(ts="2026-08-03T09:00:00"),
                     evaluation_date="2026-08-03")
        eng.evaluate(_make_snapshot(ts="2026-08-04T09:00:00"),
                     evaluation_date="2026-08-04")
        d = eng.drift()
        ok(d.from_date == "2026-08-03", f"from_date={d.from_date}")
        ok(d.to_date   == "2026-08-04", f"to_date={d.to_date}")
        return f"drift from={d.from_date} to={d.to_date}"

    def t84_drift_drifting_components_nonempty_for_large_change():
        eng = _engine()
        eng.evaluate(_make_snapshot(regime=RegimeLabel.BULL_TREND, vix=10.0))
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE,   vix=50.0))
        d = eng.drift()
        ok(len(d.drifting_components) > 0,
           f"expected drifting components, got: {d.drifting_components}")
        return f"drifting_components={d.drifting_components}"

    def t85_drift_no_drifting_when_identical():
        eng  = _engine()
        snap = _make_snapshot()
        eng.evaluate(snap)
        eng.evaluate(snap)
        d = eng.drift()
        ok(len(d.drifting_components) == 0,
           f"expected no drifting, got: {d.drifting_components}")
        return "identical snapshots → no drifting_components"

    def t86_drift_magnitude_zero_when_identical():
        eng  = _engine()
        snap = _make_snapshot()
        eng.evaluate(snap)
        eng.evaluate(snap)
        d = eng.drift()
        ok(d.drift_magnitude == 0.0, f"expected 0.0, got {d.drift_magnitude}")
        return f"identical snapshots → drift_magnitude=0.0"

    def t87_drift_serialization():
        eng = _engine()
        eng.evaluate(_make_snapshot())
        eng.evaluate(_make_snapshot(regime=RegimeLabel.VOLATILE, vix=35.0))
        d  = eng.drift()
        d2 = ContextDrift.from_dict(d.to_dict())
        ok(d2.from_date           == d.from_date)
        ok(d2.to_date             == d.to_date)
        ok(d2.score_delta         == d.score_delta)
        ok(d2.regime_changed      == d.regime_changed)
        ok(d2.drifting_components == d.drifting_components)
        ok(d2.drift_magnitude     == d.drift_magnitude)
        return "ContextDrift to_dict/from_dict round-trip OK"

    runner.run("T83 ContextDrift from_date and to_date",  t83_drift_dates_set)
    runner.run("T84 drifting_components for large change", t84_drift_drifting_components_nonempty_for_large_change)
    runner.run("T85 no drifting when identical",           t85_drift_no_drifting_when_identical)
    runner.run("T86 drift_magnitude=0 when identical",     t86_drift_magnitude_zero_when_identical)
    runner.run("T87 ContextDrift serialization round-trip", t87_drift_serialization)

    # ── T88–T90: Edge cases ───────────────────────────────────────────────────

    def t88_missing_fii_data_safe():
        snap = _make_snapshot()      # fii_dii=None
        ctx  = MCIEngine(config=_TEST_CFG).evaluate(snap)
        ok(0.0 <= ctx.context_score <= 1.0)
        ok(len(ctx.components) == 8)
        return f"missing FII → context_score={ctx.context_score:.4f} OK"

    def t89_none_global_fields_treated_as_zero():
        # global_sentiment_score=0.0 and global_bias=None
        snap = MarketSnapshot(
            timestamp=datetime(2026, 8, 4, 9, 0),
            indices={},
            regime=RegimeLabel.RANGE_MARKET,
            volatility=VolatilityLevel.MEDIUM,
            vix=15.0,
            pcr=1.0,
            market_breadth=0.5,
            global_sentiment_score=0.0,
            global_bias=None,
        )
        ctx = MCIEngine(config=_TEST_CFG).evaluate(snap)
        g_comp = next(c for c in ctx.components if c.name == "global_context")
        ok(abs(g_comp.score - 0.5) < 1e-9, f"None bias → global={g_comp.score}")
        return f"None global fields handled → global_context={g_comp.score}"

    def t90_empty_indices_valid():
        snap = _make_snapshot()   # indices={} by default
        ctx  = MCIEngine(config=_TEST_CFG).evaluate(snap)
        ok(len(ctx.components) == 8)
        ok(0.0 <= ctx.context_score <= 1.0)
        return f"empty indices → context_score={ctx.context_score:.4f} valid"

    runner.run("T88 missing FII data → score still valid",    t88_missing_fii_data_safe)
    runner.run("T89 None global fields → treated as 0.0",    t89_none_global_fields_treated_as_zero)
    runner.run("T90 empty indices → context_score valid",    t90_empty_indices_valid)

    return runner.report()


if __name__ == "__main__":
    sys.exit(run_all())
