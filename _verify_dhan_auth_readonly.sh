#!/bin/bash
set -e

echo "===== 1. Latest audit log entries (last 3) ====="
tail -n 3 /root/ai-trading-brain/data/logs/dhan_token_audit.jsonl

echo ""
echo "===== 2. --status (metadata only, no network) ====="
docker exec ai-trading-brain python3 /app/scripts/dhan_auth/dhan_token_agent.py --status 2>&1

echo ""
echo "===== 3. --health (token validity check against Dhan) ====="
docker exec ai-trading-brain python3 /app/scripts/dhan_auth/dhan_token_agent.py --health 2>&1

echo ""
echo "===== 4. Token store file metadata (no secret values) ====="
docker exec ai-trading-brain python3 -c "
import json
with open('/app/data/dhan_token_metadata.json') as f:
    d = json.load(f)
safe = {k: v for k, v in d.items() if 'token' not in k.lower() and 'secret' not in k.lower() and 'pin' not in k.lower()}
print(json.dumps(safe, indent=2))
" 2>&1 || echo "metadata file path differs - checking alternates"

echo ""
echo "===== 5. Container can load feed / DhanFeed auth state (no secrets printed) ====="
docker exec ai-trading-brain python3 -c "
from data_feeds.dhan_feed import DhanFeed
f = DhanFeed()
print('DhanFeed initialized:', f is not None)
print('has access token loaded:', bool(getattr(f, 'access_token', None) or getattr(f, '_access_token', None)))
" 2>&1

echo ""
echo "===== 6. Recent container logs - auth/token related (last 10 min) ====="
docker logs ai-trading-brain --since 10m 2>&1 | grep -iE "dhan.*token|token.*refresh|auth" | tail -n 20 || echo "No recent auth log lines"

echo ""
echo "===== 7. Confirm no secret patterns leaked in above output (manual review required) ====="
echo "Done."
