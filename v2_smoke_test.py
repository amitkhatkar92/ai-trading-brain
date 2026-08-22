"""V2 smoke test — run inside container to verify all V2 symbols import and behave correctly."""
from opportunity_engine.candidate_store import (
    CandidateStore, compute_lifecycle_state,
    LIFECYCLE_FRESH, LIFECYCLE_ACTIVE, LIFECYCLE_WEAKENING,
    LIFECYCLE_INVALIDATED, LIFECYCLE_EXPIRED, LIFECYCLE_REACTIVATED,
)
from opportunity_engine.equity_scanner_ai import (
    get_pending_mini_rescan, _check_breakout_invalidation,
    _fallback_severity_tier, _get_fallback_trend,
)
from orchestrator.master_orchestrator import MasterOrchestrator

print("ALL V2 IMPORTS OK")
print("LIFECYCLE_STATES:", LIFECYCLE_FRESH, LIFECYCLE_ACTIVE, LIFECYCLE_WEAKENING, LIFECYCLE_INVALIDATED, LIFECYCLE_EXPIRED, LIFECYCLE_REACTIVATED)

# Test get_pending_mini_rescan returns empty dict by default
assert get_pending_mini_rescan() == {}, "Expected empty dict"
print("pending_rescan: OK (empty)")

# Test fallback severity tiers
assert _fallback_severity_tier(75.0) == "NONE"
assert _fallback_severity_tier(55.0) == "LOW"
assert _fallback_severity_tier(35.0) == "MEDIUM"
assert _fallback_severity_tier(15.0) == "HIGH"
assert _fallback_severity_tier(5.0)  == "CRITICAL"
print("fallback_severity_tiers: OK")

# Test breakout invalidation: support breakdown (ltp=97 < sup-atr = 100-2 = 98)
inv, reason = _check_breakout_invalidation(
    {"support": 100, "resistance": 110, "base_ltp": 108, "atr14": 2},
    live_ltp=97.0,
)
assert inv is True, f"Expected invalidated, got {inv} {reason}"
assert "support_breakdown" in reason, f"Expected support_breakdown, got {reason}"
print("breakout_invalidation support_breakdown: OK")

# Test breakout invalidation: no invalidation when price is healthy
inv2, _ = _check_breakout_invalidation(
    {"support": 100, "resistance": 110, "base_ltp": 104, "atr14": 2},
    live_ltp=106.0,
)
assert inv2 is False, f"Expected not invalidated, got {inv2}"
print("breakout_invalidation healthy: OK")

# Test lifecycle EXPIRED
lc_exp = compute_lifecycle_state({"valid_until_utc": "2020-01-01T00:00:00Z"})
assert lc_exp == LIFECYCLE_EXPIRED, f"Expected EXPIRED, got {lc_exp}"
print("lifecycle_EXPIRED: OK")

# Test lifecycle FRESH (prepared_at = far future to simulate new candidate)
import datetime
future_pa = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
lc_fresh = compute_lifecycle_state({
    "rsi": 55, "volume_ratio": 1.2, "score": 0.7,
    "prepared_at": future_pa,
})
assert lc_fresh == LIFECYCLE_FRESH, f"Expected FRESH, got {lc_fresh}"
print("lifecycle_FRESH: OK")

# Test lifecycle WEAKENING (vol_ratio < 0.40 + rsi extreme = 2+ signals)
lc_weak = compute_lifecycle_state({
    "rsi": 80, "volume_ratio": 0.30, "score": 0.7,
})
assert lc_weak == LIFECYCLE_WEAKENING, f"Expected WEAKENING, got {lc_weak}"
print("lifecycle_WEAKENING: OK")

# Test MasterOrchestrator has _check_scanner_events
assert hasattr(MasterOrchestrator, "_check_scanner_events"), "Missing _check_scanner_events method"
print("_check_scanner_events: OK")

# Test apply_conviction_decay on CandidateStore
candidates = [
    {"symbol": "TEST1", "score": 0.9, "volume_ratio": 0.25, "rsi": 50},  # vol_collapse → 0.840
    {"symbol": "TEST2", "score": 0.9, "volume_ratio": 1.2,  "rsi": 50},  # normal → 0.980
]
decayed, log_lines = CandidateStore.apply_conviction_decay(candidates, price_map={})
assert abs(decayed[0]["score"] - 0.9 * 0.840) < 0.001, f"vol_collapse decay wrong: {decayed[0]['score']}"
assert abs(decayed[1]["score"] - 0.9 * 0.980) < 0.001, f"normal decay wrong: {decayed[1]['score']}"
assert any("vol_collapse" in l for l in log_lines), "Expected vol_collapse in log_lines"
print("apply_conviction_decay: OK")

print()
print("=" * 60)
print("ALL V2 SMOKE TESTS PASSED")
print("=" * 60)
