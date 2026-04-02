#!/bin/bash
# verify_single_instance.sh
# Run on the VPS to confirm ONLY Docker is running the trading brain.
# Pass: "Checking host processes..." shows no main.py lines.
# Pass: Docker container is Up.
# Pass: Exactly one main.py inside the container.

set -euo pipefail

RC=0

echo "════════════════════════════════════════════"
echo "  Single-Instance Verification"
echo "════════════════════════════════════════════"

# ── 1. No main.py on host ─────────────────────────────────────────────
echo ""
echo "[ 1 ] Host processes running main.py:"
HOST_PROCS=$(ps aux | grep "[m]ain.py" | grep -v grep || true)
if [ -z "$HOST_PROCS" ]; then
    echo "      ✅  None — host is clean"
else
    echo "      ❌  FOUND (must be killed):"
    echo "$HOST_PROCS"
    RC=1
fi

# ── 2. Systemd service is dead ────────────────────────────────────────
echo ""
echo "[ 2 ] Systemd service status:"
SVC_STATE=$(systemctl is-active trading-brain-schedule 2>/dev/null || echo "inactive")
SVC_ENABLED=$(systemctl is-enabled trading-brain-schedule 2>/dev/null || echo "disabled")
if [ "$SVC_STATE" = "inactive" ] || [ "$SVC_STATE" = "failed" ] || [ "$SVC_STATE" = "unknown" ]; then
    echo "      ✅  trading-brain-schedule is $SVC_STATE / $SVC_ENABLED"
else
    echo "      ❌  Service is $SVC_STATE — disable it: systemctl disable --now trading-brain-schedule"
    RC=1
fi

# ── 3. Docker container is running ───────────────────────────────────
echo ""
echo "[ 3 ] Docker containers:"
docker ps --filter name=ai-trading-brain --format "      {{.Names}}  {{.Status}}"
CONTAINER_UP=$(docker ps --filter name=ai-trading-brain --filter status=running -q || true)
if [ -n "$CONTAINER_UP" ]; then
    echo "      ✅  ai-trading-brain container is running"
else
    echo "      ❌  ai-trading-brain container is NOT running"
    RC=1
fi

# ── 4. Exactly one main.py inside the container ───────────────────────
echo ""
echo "[ 4 ] Processes inside container:"
if [ -n "$CONTAINER_UP" ]; then
    INNER=$(docker exec ai-trading-brain ps aux 2>/dev/null | grep "[m]ain.py" || true)
    COUNT=$(echo "$INNER" | grep -c "main.py" || true)
    if [ "$COUNT" -eq 1 ]; then
        echo "      ✅  Exactly 1 main.py process inside container"
        echo "      $INNER"
    elif [ "$COUNT" -eq 0 ]; then
        echo "      ⚠️   No main.py inside container (may still be starting)"
    else
        echo "      ❌  $COUNT main.py processes inside container — duplicate!"
        echo "$INNER"
        RC=1
    fi
else
    echo "      ⚠️   Skipped — container not running"
fi

# ── 5. Cron check ────────────────────────────────────────────────────
echo ""
echo "[ 5 ] Cron entries referencing main.py or ai-trading-brain:"
CRON_HITS=$(
    { crontab -l 2>/dev/null; cat /etc/crontab 2>/dev/null; ls /etc/cron.d/ 2>/dev/null | xargs -I{} cat /etc/cron.d/{} 2>/dev/null; } \
    | grep -E "main\.py|ai.trading.brain|autostart" || true
)
if [ -z "$CRON_HITS" ]; then
    echo "      ✅  No cron entries found"
else
    echo "      ❌  Found cron entries (remove them):"
    echo "$CRON_HITS"
    RC=1
fi

# ── Summary ───────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
if [ "$RC" -eq 0 ]; then
    echo "  ✅  ALL CHECKS PASSED — single Docker runtime confirmed"
else
    echo "  ❌  ISSUES FOUND — see above and remediate"
fi
echo "════════════════════════════════════════════"
exit $RC
