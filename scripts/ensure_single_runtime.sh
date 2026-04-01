#!/usr/bin/env bash
# =============================================================================
# ensure_single_runtime.sh
# -----------------------------------------------------------------------------
# Run this ONCE on the VPS to permanently switch from systemd → Docker-only.
#
# What it does:
#   1. Stops and disables the systemd trading service (if it exists)
#   2. Verifies no orphan main.py processes are left running
#   3. Reminds you to start via Docker
#
# Usage:
#   chmod +x scripts/ensure_single_runtime.sh
#   sudo bash scripts/ensure_single_runtime.sh
# =============================================================================

set -euo pipefail

SERVICE="trading-brain-schedule.service"
CONTAINER="ai-trading-brain"

echo ""
echo "============================================================"
echo "  AI Trading Brain — Single Runtime Enforcement"
echo "============================================================"
echo ""

# ── 1. Stop & disable systemd service ─────────────────────────────────────
if systemctl list-unit-files --type=service 2>/dev/null | grep -q "$SERVICE"; then
    echo "[1/3] Stopping systemd service: $SERVICE"
    systemctl stop "$SERVICE" || true

    echo "[1/3] Disabling systemd service: $SERVICE"
    systemctl disable "$SERVICE" || true

    echo "      ✅ systemd service stopped and disabled."
else
    echo "[1/3] systemd service '$SERVICE' not found — nothing to disable."
fi

echo ""

# ── 2. Check for orphan main.py processes ─────────────────────────────────
ORPHANS=$(pgrep -a -f "python.*main\.py" 2>/dev/null || true)

if [[ -n "$ORPHANS" ]]; then
    # Only kill processes NOT owned by the Docker container
    DOCKER_PID=$(docker inspect --format '{{.State.Pid}}' "$CONTAINER" 2>/dev/null || echo "")
    echo "[2/3] Found main.py process(es):"
    echo "$ORPHANS"
    while IFS= read -r line; do
        PID=$(echo "$line" | awk '{print $1}')
        if [[ "$PID" != "$DOCKER_PID" ]]; then
            echo "      Killing orphan PID $PID (not the Docker process)"
            kill "$PID" 2>/dev/null || true
        else
            echo "      PID $PID belongs to Docker container — leaving it."
        fi
    done <<< "$ORPHANS"
else
    echo "[2/3] No orphan main.py processes found outside Docker. ✅"
fi

echo ""

# ── 3. Verify Docker container status ─────────────────────────────────────
echo "[3/3] Docker container status:"
docker ps --filter "name=$CONTAINER" --format "  {{.Names}}  {{.Status}}  Restart:{{.RunningFor}}" \
    2>/dev/null || echo "  (docker not available or container not found)"

echo ""
echo "============================================================"
echo "  ✅ Runtime enforcement complete."
echo ""
echo "  ONLY Docker should run the trading engine now."
echo ""
echo "  To start the container:"
echo "    docker compose up -d"
echo ""
echo "  To verify:"
echo "    docker ps"
echo "    systemctl status $SERVICE"
echo "============================================================"
echo ""
