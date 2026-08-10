"""
test_cre_strategy_share.py — Capital Risk Engine strategy-share mapping tests.

Covers:
  T01  Trend_Pullback registered at 0.18
  T02  Equity_Breakout registered at 0.28
  T03  Equity_Retest registered at 0.18
  T04  Momentum_Retest unchanged at 0.18
  T05  Breakout_Volume unchanged at 0.28
  T06  Short_Straddle_IV_Spike unchanged at 0.14
  T07  EDG_* evolved variant inherits base Breakout_Volume share (0.28)
  T08  Unknown strategy → _DEFAULT_SHARE 0.10
  T09  Strategy with missing base_strategy → _DEFAULT_SHARE 0.10
  T10  Strategy with invalid/unknown base_strategy → _DEFAULT_SHARE 0.10
  T11  Strategy share is capital-independent (same % at different capital levels)
  T12  MAX_RISK_PER_TRADE_PCT unchanged at 0.25%
  T13  All other _STRATEGY_SHARE entries exist (no regression on existing entries)
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

# ── Bootstrap path ──────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Lazy import so we can patch the cache before loading ────────────────────
import risk_control.capital_risk_engine as _cre_mod
from risk_control.capital_risk_engine import (
    CapitalRiskEngine,
    _STRATEGY_SHARE,
    _DEFAULT_SHARE,
)
from config import MAX_RISK_PER_TRADE_PCT, MAX_PORTFOLIO_RISK_PCT


# ── Helpers ──────────────────────────────────────────────────────────────────

def _budget_share(strategy_name: str) -> float:
    """Return the fractional share _strategy_budget() applies for a given name."""
    cre = CapitalRiskEngine()
    deployable = 100_000.0
    budget = cre._strategy_budget(strategy_name, deployable)
    return round(budget / deployable, 10)


def _reset_evolved_cache():
    """Reset the module-level evolved base map cache between tests."""
    _cre_mod._EVOLVED_BASE_MAP = {}
    _cre_mod._EVOLVED_BASE_MAP_LOADED = False


# ── Test suite ────────────────────────────────────────────────────────────────

_PASS = _FAIL = 0
_DETAILS: list[str] = []


def _check(tid: str, condition: bool, msg: str) -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  PASS  {tid}  {msg}")
    else:
        _FAIL += 1
        _DETAILS.append(f"  FAIL  {tid}  {msg}")
        print(f"  FAIL  {tid}  {msg}")


# ────────────────────────────────────────────────────────────────────────────
# T01 — Trend_Pullback registered at 0.18
# ────────────────────────────────────────────────────────────────────────────
def t01():
    share = _STRATEGY_SHARE.get("Trend_Pullback")
    _check("T01", share == 0.18,
           f"Trend_Pullback in _STRATEGY_SHARE = {share} (expected 0.18)")


# ────────────────────────────────────────────────────────────────────────────
# T02 — Equity_Breakout registered at 0.28
# ────────────────────────────────────────────────────────────────────────────
def t02():
    share = _STRATEGY_SHARE.get("Equity_Breakout")
    _check("T02", share == 0.28,
           f"Equity_Breakout in _STRATEGY_SHARE = {share} (expected 0.28)")


# ────────────────────────────────────────────────────────────────────────────
# T03 — Equity_Retest registered at 0.18
# ────────────────────────────────────────────────────────────────────────────
def t03():
    share = _STRATEGY_SHARE.get("Equity_Retest")
    _check("T03", share == 0.18,
           f"Equity_Retest in _STRATEGY_SHARE = {share} (expected 0.18)")


# ────────────────────────────────────────────────────────────────────────────
# T04 — Momentum_Retest unchanged at 0.18
# ────────────────────────────────────────────────────────────────────────────
def t04():
    share = _budget_share("Momentum_Retest")
    _check("T04", share == 0.18,
           f"Momentum_Retest budget share = {share} (expected 0.18 — regression guard)")


# ────────────────────────────────────────────────────────────────────────────
# T05 — Breakout_Volume unchanged at 0.28
# ────────────────────────────────────────────────────────────────────────────
def t05():
    share = _budget_share("Breakout_Volume")
    _check("T05", share == 0.28,
           f"Breakout_Volume budget share = {share} (expected 0.28 — regression guard)")


# ────────────────────────────────────────────────────────────────────────────
# T06 — Short_Straddle_IV_Spike unchanged at 0.14
# ────────────────────────────────────────────────────────────────────────────
def t06():
    share = _budget_share("Short_Straddle_IV_Spike")
    _check("T06", share == 0.14,
           f"Short_Straddle_IV_Spike budget share = {share} (expected 0.14 — regression guard)")


# ────────────────────────────────────────────────────────────────────────────
# T07 — EDG_* evolved variant inherits base Breakout_Volume share (0.28)
# ────────────────────────────────────────────────────────────────────────────
def t07():
    """Create a temporary evolved_strategies.json with one EDG variant."""
    _reset_evolved_cache()
    evolved_data = {
        "EDG_TEST_99_T07": {
            "approved": True,
            "base_strategy": "Breakout_Volume",
            "min_rr": 2.5,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(evolved_data, tmp)
        tmp_path = tmp.name

    try:
        with patch.object(_cre_mod, "_EVOLVED_STRATEGIES_PATH", tmp_path):
            _reset_evolved_cache()
            share = _budget_share("EDG_TEST_99_T07")
        _check("T07", share == 0.28,
               f"EDG_TEST_99_T07 (base=Breakout_Volume) budget share = {share} (expected 0.28)")
    finally:
        os.unlink(tmp_path)
        _reset_evolved_cache()


# ────────────────────────────────────────────────────────────────────────────
# T08 — Unknown strategy → _DEFAULT_SHARE 0.10
# ────────────────────────────────────────────────────────────────────────────
def t08():
    _reset_evolved_cache()
    # Use an empty evolved map so no base lookup succeeds
    with patch.object(_cre_mod, "_EVOLVED_STRATEGIES_PATH", "/nonexistent/path.json"):
        _reset_evolved_cache()
        share = _budget_share("COMPLETELY_UNKNOWN_STRATEGY_XYZ")
    _check("T08", share == _DEFAULT_SHARE,
           f"Unknown strategy budget share = {share} (expected {_DEFAULT_SHARE})")
    _reset_evolved_cache()


# ────────────────────────────────────────────────────────────────────────────
# T09 — Approved evolved variant WITHOUT base_strategy → _DEFAULT_SHARE
# ────────────────────────────────────────────────────────────────────────────
def t09():
    _reset_evolved_cache()
    evolved_data = {
        "EDG_NO_BASE_T09": {
            "approved": True,
            # base_strategy intentionally absent
            "min_rr": 2.5,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(evolved_data, tmp)
        tmp_path = tmp.name

    try:
        with patch.object(_cre_mod, "_EVOLVED_STRATEGIES_PATH", tmp_path):
            _reset_evolved_cache()
            share = _budget_share("EDG_NO_BASE_T09")
        _check("T09", share == _DEFAULT_SHARE,
               f"EDG_NO_BASE_T09 (no base_strategy) share = {share} (expected {_DEFAULT_SHARE})")
    finally:
        os.unlink(tmp_path)
        _reset_evolved_cache()


# ────────────────────────────────────────────────────────────────────────────
# T10 — Evolved variant with invalid (unknown) base_strategy → _DEFAULT_SHARE
# ────────────────────────────────────────────────────────────────────────────
def t10():
    _reset_evolved_cache()
    evolved_data = {
        "EDG_BAD_BASE_T10": {
            "approved": True,
            "base_strategy": "Nonexistent_Base_Strategy_999",
            "min_rr": 2.5,
        }
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(evolved_data, tmp)
        tmp_path = tmp.name

    try:
        with patch.object(_cre_mod, "_EVOLVED_STRATEGIES_PATH", tmp_path):
            _reset_evolved_cache()
            share = _budget_share("EDG_BAD_BASE_T10")
        _check("T10", share == _DEFAULT_SHARE,
               f"EDG_BAD_BASE_T10 (invalid base) share = {share} (expected {_DEFAULT_SHARE})")
    finally:
        os.unlink(tmp_path)
        _reset_evolved_cache()


# ────────────────────────────────────────────────────────────────────────────
# T11 — Strategy share is capital-independent (same % at every capital level)
# ────────────────────────────────────────────────────────────────────────────
def t11():
    """The FRACTION returned by _strategy_budget must not depend on TOTAL_CAPITAL."""
    cre = CapitalRiskEngine()
    strategies = [
        "Breakout_Volume", "Momentum_Retest", "Trend_Pullback",
        "Equity_Breakout", "Equity_Retest", "Mean_Reversion",
    ]
    capitals = [10_000, 50_000, 1_00_000, 2_00_000, 5_00_000, 1_00_00_000]
    all_ok = True
    for strat in strategies:
        fractions = [
            round(cre._strategy_budget(strat, cap * 0.8) / (cap * 0.8), 10)
            for cap in capitals
        ]
        if len(set(fractions)) != 1:
            all_ok = False
            print(f"    MISMATCH {strat}: {fractions}")
    _check("T11", all_ok,
           "strategy share % is capital-independent for all named strategies")


# ────────────────────────────────────────────────────────────────────────────
# T12 — MAX_RISK_PER_TRADE_PCT unchanged at 0.25%
# ────────────────────────────────────────────────────────────────────────────
def t12():
    _check("T12", MAX_RISK_PER_TRADE_PCT == 0.0025,
           f"MAX_RISK_PER_TRADE_PCT = {MAX_RISK_PER_TRADE_PCT} (must remain 0.0025)")


# ────────────────────────────────────────────────────────────────────────────
# T13 — Regression: all original 10 _STRATEGY_SHARE entries still present
# ────────────────────────────────────────────────────────────────────────────
def t13():
    expected = {
        "Breakout_Volume": 0.28, "Momentum_Retest": 0.18, "Mean_Reversion": 0.22,
        "Bull_Call_Spread": 0.12, "Iron_Condor_Range": 0.18, "Hedging_Model": 0.10,
        "Short_Straddle_IV_Spike": 0.14, "Long_Straddle_Pre_Event": 0.08,
        "Futures_Basis_Arb": 0.14, "ETF_NAV_Arb": 0.12,
    }
    mismatches = [
        f"{k}: got {_STRATEGY_SHARE.get(k)} expected {v}"
        for k, v in expected.items()
        if _STRATEGY_SHARE.get(k) != v
    ]
    _check("T13", len(mismatches) == 0,
           f"Original 10 entries unchanged — {', '.join(mismatches) or 'all OK'}")


# ── EDG integration test using real evolved_strategies.json if available ────
def t14_real_edg():
    """T14 (bonus): real EDG variant from data/evolved_strategies.json → 0.28."""
    json_path = os.path.join(_ROOT, "data", "evolved_strategies.json")
    if not os.path.exists(json_path):
        print("  SKIP  T14  data/evolved_strategies.json not found")
        return
    _reset_evolved_cache()
    try:
        with open(json_path) as f:
            d = json.load(f)
        edg_variants = [
            (k, v["base_strategy"]) for k, v in d.items()
            if v.get("approved") and v.get("base_strategy") == "Breakout_Volume"
            and k.startswith("EDG_")
        ]
        if not edg_variants:
            print("  SKIP  T14  no approved EDG_*/Breakout_Volume variants found")
            return
        name, base = edg_variants[0]
        share = _budget_share(name)
        _check("T14", share == 0.28,
               f"Real EDG variant {name} (base={base}) share = {share} (expected 0.28)")
    finally:
        _reset_evolved_cache()


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  CRE STRATEGY-SHARE MAPPING TESTS")
    print("=" * 60)

    for fn in [t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12, t13, t14_real_edg]:
        try:
            fn()
        except Exception as exc:
            tid = fn.__name__.upper()
            _FAIL += 1
            _DETAILS.append(f"  ERROR  {tid}  {exc}")
            print(f"  ERROR  {tid}  {exc}")

    print()
    print("=" * 60)
    total = _PASS + _FAIL
    print(f"  {total} tests run  |  {_PASS} passed  |  {_FAIL} failed")
    if _DETAILS:
        print()
        for d in _DETAILS:
            print(d)
    print("=" * 60)
    sys.exit(0 if _FAIL == 0 else 1)
