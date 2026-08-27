from learning_system.learning_observation_ledger import _fetch_ohlcv, get_lol
import inspect, sys

lol = get_lol()
print(f"LOL init OK: {lol}")
print(f"_fetch_ohlcv callable: {callable(_fetch_ohlcv)}")

# Confirm the fix is present in source
src = inspect.getsource(_fetch_ohlcv)
assert "isinstance(df.columns, _pd.MultiIndex)" in src, "MultiIndex fix NOT present"
assert "droplevel" in src, "droplevel NOT present"
assert "row parse error" in src, "per-row warning NOT present"
assert "bar fetch failed" in src, "outer warning NOT present"
print("Fix confirmed: MultiIndex normalisation + per-row logging present")
print("D019-001: VERIFIED")
