"""Smoke test: verify _PRICE_CACHE_READY Event exists in equity_scanner_ai."""
import sys, threading
sys.path.insert(0, "/app")
from opportunity_engine import equity_scanner_ai as m
assert isinstance(m._PRICE_CACHE_READY, threading.Event), "_PRICE_CACHE_READY missing"
assert hasattr(m, "_PRICE_CACHE_LOCK"), "_PRICE_CACHE_LOCK missing"
assert hasattr(m, "_PRICE_REFRESH_RUNNING"), "_PRICE_REFRESH_RUNNING missing"
print("VPS_P6_PRICEGUARD_PASS — _PRICE_CACHE_READY Event present")
