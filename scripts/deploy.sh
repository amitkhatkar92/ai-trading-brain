#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Single-source-of-truth deployment script for VPS
# =============================================================================
#
# Usage:
#   /root/ai-trading-brain/scripts/deploy.sh
#
# Flow:
#   1. git pull   — fetch latest code from origin/main
#   2. generate   — create build_manifest.json (git commit + file hashes)
#   3. docker build — bake manifest into image
#   4. docker up  — restart container from new image
#   5. record     — write deploy_record.json to data/ volume
#
# NEVER manually SCP files or edit files inside the container.
# All changes must flow: LOCAL → git push → deploy.sh
# =============================================================================

set -euo pipefail

APP_DIR="/root/ai-trading-brain"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"
DATA_DIR="$APP_DIR/data"

cd "$APP_DIR"
echo "============================================================"
echo "  AI Trading Brain — VPS Deploy"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"

# ── 1. Pull latest code ────────────────────────────────────────────────────
echo ""
echo "[1/5] git pull origin main..."
git pull origin main
COMMIT=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
MSG=$(git log -1 --pretty=%s)
echo "      commit  = $COMMIT"
echo "      branch  = $BRANCH"
echo "      message = $MSG"

# ── 2. Generate build manifest ────────────────────────────────────────────
echo ""
echo "[2/5] Generating build manifest..."
python3 scripts/generate_build_manifest.py

# ── 3. Build Docker image ─────────────────────────────────────────────────
echo ""
echo "[3/5] docker compose build..."
docker compose -f "$COMPOSE_FILE" build

# After compose build the image is named <project>-<service>
# docker compose project = directory basename = ai-trading-brain
# service name = ai-trading-brain  →  image = ai-trading-brain-ai-trading-brain
COMPOSE_IMAGE="ai-trading-brain-ai-trading-brain"
IMAGE_SHA=$(docker images "$COMPOSE_IMAGE" --format '{{.ID}}' 2>/dev/null | head -1)
# Fallback: inspect by repo tag
[ -z "$IMAGE_SHA" ] && IMAGE_SHA=$(docker images ai-trading-brain:latest --format '{{.ID}}' 2>/dev/null | head -1)
echo "      image = $IMAGE_SHA"

# ── 4. Restart container ──────────────────────────────────────────────────
echo ""
echo "[4/5] docker compose up -d..."
# Stop and remove any container named ai-trading-brain regardless of how it was started
docker stop ai-trading-brain 2>/dev/null || true
docker rm   ai-trading-brain 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" up -d
echo "      container restarted."

# ── 5. Write deploy record to data/ volume ────────────────────────────────
echo ""
echo "[5/5] Writing deploy_record.json..."
mkdir -p "$DATA_DIR"
python3 - <<PYEOF
import json, datetime, os, sys
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
rec = {
    "commit":           "$COMMIT",
    "branch":           "$BRANCH",
    "commit_message":   "$MSG",
    "image_sha":        "$IMAGE_SHA",
    "deploy_timestamp": datetime.datetime.now(IST).isoformat(),
    "deployed_by":      "deploy.sh",
}
path = "$DATA_DIR/deploy_record.json"
with open(path, "w") as f:
    json.dump(rec, f, indent=2)
print(f"      written → {path}")
PYEOF

echo ""
echo "============================================================"
echo "  Deploy complete."
echo "  COMMIT = $COMMIT  IMAGE = $IMAGE_SHA"
echo "  Run: docker logs ai-trading-brain -f"
echo "============================================================"
