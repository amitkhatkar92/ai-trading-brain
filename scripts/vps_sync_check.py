import json, pathlib
from scripts.dhan_auth.dhan_token_sync import get_token_sync

sync = get_token_sync()
state = sync.get_token_state()
print(f"TOKEN_SYNC_STATE: {state}")
print(f"SAFE_FOR_API: {sync.is_token_safe_for_api()}")

health = json.loads(pathlib.Path("data/dhan_token_health.json").read_text())
print(f"HEALTH_STATUS: {health['status']}")
print(f"GENERATION_ID: {health['generation_id'][:8]}...")
print(f"EXPIRY: {health['expiry_time']}")
print(f"LIVE_RELOAD: {health.get('live_reload')}")
