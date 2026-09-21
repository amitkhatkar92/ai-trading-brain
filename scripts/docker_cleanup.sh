#!/bin/bash
# Safe automatic Docker disk cleanup — run BEFORE each deploy build, after
# safe_pull.sh and before docker compose build.
#
# Why safe:
#   - docker image prune -a only removes images with zero container
#     references. The old containers are still running at this point (down
#     happens later in the deploy), so their images are structurally
#     protected by Docker itself — never removed.
#   - docker builder prune removes build cache. This repo always builds
#     with `docker compose build --no-cache`, so accumulated build cache is
#     never reused anyway — safe to reclaim in full every run.
#   - Never touches data/ volumes, running containers, or container state.
#
# Found necessary 2026-09-21 (HKAP-IDR-AUTO-MERGE-001 deploy): VPS disk hit
# 100% full (127GB+ of stale build cache from repeated --no-cache builds),
# causing that deploy's build step to appear hung for ~15 minutes.

set -e

echo "[docker-cleanup] Disk before cleanup:"
df -h / | tail -1

echo "[docker-cleanup] Pruning unused images (running containers' images are never touched)..."
docker image prune -a -f

echo "[docker-cleanup] Pruning build cache (safe: this repo never reuses cache, always builds --no-cache)..."
docker builder prune -f

echo "[docker-cleanup] Disk after cleanup:"
df -h / | tail -1
