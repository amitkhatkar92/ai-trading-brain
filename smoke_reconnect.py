import sys
sys.path.insert(0, '/app')
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

from data_feeds.angelone_feed import AngelOneFeed

# Test 1: verify _last_reconnect_attempt attribute exists
ao = AngelOneFeed()
print(f"_last_reconnect_attempt attr exists: {hasattr(ao, '_last_reconnect_attempt')}")
print(f"_last_reconnect_attempt initial: {ao._last_reconnect_attempt}")

# Test 2: force disconnected state and call _refresh_if_needed
print("\n--- Forcing disconnected state ---")
ao._connected = False
ao._smart = None
ao._last_reconnect_attempt = None
print("Calling _refresh_if_needed() with disconnected state...")
result = ao._refresh_if_needed()
print(f"_refresh_if_needed returned: {result}")
print(f"is_live after reconnect attempt: {ao.is_live}")

# Test 3: rate-limit (5-min backoff) — second call should NOT reconnect within 5 min
from datetime import datetime
ao._connected = False
ao._smart = None
ao._last_reconnect_attempt = datetime.now()  # just set it to now
print("\n--- Testing rate-limit (backoff) ---")
print("Calling _refresh_if_needed() again immediately (should be rate-limited)...")
result2 = ao._refresh_if_needed()
print(f"_refresh_if_needed returned (should be False due to backoff): {result2}")

print("\nRECONNECT SMOKE TEST DONE")
