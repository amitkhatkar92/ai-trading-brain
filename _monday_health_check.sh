#!/bin/bash
set -e

echo "===== 1. Container status ====="
docker compose ps

echo ""
echo "===== 2. Git HEAD on VPS ====="
cd /root/ai-trading-brain && git log -1 --format='%H %s'

echo ""
echo "===== 3. DB integrity ====="
docker exec ai-trading-brain python3 -c "
import sqlite3
c = sqlite3.connect('/app/data/control_tower.db')
cur = c.execute('PRAGMA integrity_check')
print(cur.fetchone())
"

echo ""
echo "===== 4. Dhan token status (today, Monday) ====="
docker exec ai-trading-brain python3 /app/scripts/dhan_auth/dhan_token_agent.py --status 2>&1

echo ""
echo "===== 5. Latest Dhan token audit log entries ====="
tail -n 5 /root/ai-trading-brain/data/logs/dhan_token_audit.jsonl

echo ""
echo "===== 6. Cron log (today's auto-refresh attempts) ====="
tail -n 30 /root/ai-trading-brain/data/logs/dta_cron.log 2>&1 || echo "No cron log yet"

echo ""
echo "===== 7. V3ShadowDay / KSL-001 firing (since last EOD, Friday 15:35 IST) ====="
docker logs ai-trading-brain --since 60h 2>&1 | grep -E "V3ShadowDay|KSL-001" | tail -n 20 || echo "No V3ShadowDay/KSL-001 log lines found in last 60h"

echo ""
echo "===== 8. Readiness test (18-check) ====="
docker exec -e RUNNING_IN_DOCKER=1 ai-trading-brain python3 /app/main.py --readiness 2>&1 | tail -n 30

echo ""
echo "===== 9. Recent errors/exceptions (last 30 min) ====="
docker logs ai-trading-brain --since 30m 2>&1 | grep -iE "error|exception|traceback|CRITICAL" | tail -n 30 || echo "No errors in last 30 min"

echo ""
echo "===== 10. Live market/signal flow check (last 30 min) ====="
docker logs ai-trading-brain --since 30m 2>&1 | grep -iE "\[Scanner\]|\[EquityScannerAI\]|\[Cycle\]|full cycle" | tail -n 20 || echo "No scan/cycle activity in last 30 min"
