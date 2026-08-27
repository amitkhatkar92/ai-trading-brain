import os, sys

creds = {
    "DHAN_CLIENT_ID":   bool(os.getenv("DHAN_CLIENT_ID", "").strip()),
    "DHAN_PIN":         bool(os.getenv("DHAN_PIN", "").strip()),
    "DHAN_TOTP_SECRET": bool(os.getenv("DHAN_TOTP_SECRET", "").strip()),
    "DHAN_ACCESS_TOKEN": bool(os.getenv("DHAN_ACCESS_TOKEN", "").strip()),
}
for k, v in creds.items():
    print(f"{k}: {'PRESENT' if v else 'MISSING'}")

# Check token health file
import json, pathlib
health = pathlib.Path("data/dhan_token_health.json")
store  = pathlib.Path("data/dhan_token_store.json")
print()
if health.exists():
    print("TOKEN HEALTH:", json.loads(health.read_text()))
else:
    print("TOKEN HEALTH FILE: NOT FOUND")
if store.exists():
    data = json.loads(store.read_text())
    # Never print actual token values
    safe = {k: v for k, v in data.items()
            if k not in ("access_token", "token", "jwt")}
    print("TOKEN STORE:", safe)
else:
    print("TOKEN STORE FILE: NOT FOUND")

# Check cron log
cron_log = pathlib.Path("data/logs/dta_cron.log")
if cron_log.exists():
    lines = cron_log.read_text().splitlines()
    print(f"\nCRON LOG (last 10 lines of {len(lines)} total):")
    for line in lines[-10:]:
        print(" ", line)
else:
    print("CRON LOG: NOT FOUND")

# Dry-run check
try:
    sys.path.insert(0, "/app")
    from scripts.dhan_auth.dhan_token_agent import DhanTokenAgent
    agent = DhanTokenAgent()
    result = agent.run_dry_run()
    print("\nDRY RUN:", {k: v for k, v in result.items()
                          if k not in ("access_token", "token", "credentials")})
except Exception as e:
    print(f"\nDRY RUN FAILED: {e}")

# Token sync status
try:
    from scripts.dhan_auth.dhan_token_sync import get_token_sync
    state = get_token_sync().get_token_state()
    print(f"\nTOKEN SYNC STATE: {state}")
except Exception as e:
    print(f"\nTOKEN SYNC CHECK FAILED: {e}")
