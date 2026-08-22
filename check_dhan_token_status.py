import os, re
from pathlib import Path
from datetime import datetime

sources = [
    Path("data/dhan_token.json"),
    Path("data/dhan_credentials.json"),
    Path("data/oauth_token.json"),
    Path(".env"),
]

print("=== Token Sources ===")
for p in sources:
    if p.exists():
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        content = p.read_text(encoding="utf-8", errors="replace")
        # Mask actual token value but show keys/structure
        masked = re.sub(
            r'(["\']?(?:access_token|token|TOKEN|DHAN_TOKEN|client_secret)["\']?\s*[:=]\s*["\']?)([A-Za-z0-9._\-]{15,})(["\']?)',
            r'\1***MASKED***\3',
            content,
        )
        print(f"\n--- {p}  (modified: {mtime}) ---")
        print(masked[:400])

# Also check env vars
print("\n=== Env Vars ===")
for k, v in os.environ.items():
    if "DHAN" in k.upper() or "TOKEN" in k.upper() or "CLIENT" in k.upper():
        masked_v = v[:6] + "***" if len(v) > 6 else "***"
        print(f"  {k} = {masked_v}")

# Check how dhan_feed loads the token
print("\n=== DhanFeed token load path ===")
try:
    import sys; sys.path.insert(0, "/app")
    from data_feeds.dhan_feed import DhanFeed
    feed = DhanFeed.__new__(DhanFeed)
    print("DhanFeed class loaded OK")
except Exception as e:
    print(f"DhanFeed load: {e}")

# Check the live token expiry via dhanhq if available
print("\n=== Live token test ===")
try:
    from data_feeds.dhan_feed import DhanFeed
    import config as cfg
    client_id = getattr(cfg, "DHAN_CLIENT_ID", os.getenv("DHAN_CLIENT_ID", ""))
    print(f"  Client ID: {client_id[:8]}..." if client_id else "  Client ID: NOT SET")
    
    # Try a minimal data API call
    from dhanhq import dhanhq as DhanHQ
    import json
    token_file = Path("data/dhan_token.json")
    if token_file.exists():
        tok = json.loads(token_file.read_text())
        access_token = tok.get("access_token", "")
        masked_tok = access_token[:8] + "..." if access_token else "EMPTY"
        print(f"  Token from file: {masked_tok}")
        
        created = tok.get("created_at", tok.get("timestamp", "unknown"))
        print(f"  Token created/updated: {created}")
except Exception as e:
    print(f"  Token test failed: {e}")
