#!/bin/bash
# Safe git pull that preserves all runtime/research data files.
# Run from /root/ai-trading-brain/

set -e
D="/root/ai-trading-brain/data"
B="/tmp/data_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$B/ars"

echo "[safe-pull] Backing up runtime data to $B ..."

# Files about to be removed by git merge (delete mode in new commit)
FILES=(
  "strategy_performance.json"
  "odm_state.json"
  "knowledge_pipeline_health.json"
  "paper_trading_daily.json"
  "discovered_edges.json"
  "evolved_strategies.json"
  "ars_hypothesis_registry.json"
  "ars_study_003.json"
  "ars_study_h001.json"
  "mover_discovery_v3_shadow.jsonl"
  "mover_discovery_v3_shadow_raw.jsonl"
)

for f in "${FILES[@]}"; do
  [ -f "$D/$f" ] && cp "$D/$f" "$B/$f" && echo "  backed up: $f"
done

[ -f "$D/ars/rc/history.json" ] && mkdir -p "$B/ars/rc" && cp "$D/ars/rc/history.json" "$B/ars/rc/history.json" && echo "  backed up: ars/rc/history.json"
[ -f "$D/klp/knowledge_fusion/source_inventory.jsonl" ] && mkdir -p "$B/klp/knowledge_fusion" && cp "$D/klp/knowledge_fusion/source_inventory.jsonl" "$B/klp/knowledge_fusion/" && echo "  backed up: klp/knowledge_fusion/source_inventory.jsonl"

echo "[safe-pull] Removing tracked copies so git merge can proceed ..."
cd /root/ai-trading-brain
git rm --cached "${FILES[@]}" "data/ars/rc/history.json" "data/klp/knowledge_fusion/source_inventory.jsonl" 2>/dev/null || true
rm -f "${FILES[@]/#/$D/}"
rm -f "$D/ars/rc/history.json"
rm -f "$D/klp/knowledge_fusion/source_inventory.jsonl"

echo "[safe-pull] Pulling ..."
git pull origin main

echo "[safe-pull] Restoring backed-up files ..."
for f in "${FILES[@]}"; do
  [ -f "$B/$f" ] && cp "$B/$f" "$D/$f" && echo "  restored: $f"
done
[ -f "$B/ars/rc/history.json" ] && mkdir -p "$D/ars/rc" && cp "$B/ars/rc/history.json" "$D/ars/rc/" && echo "  restored: ars/rc/history.json"
[ -f "$B/klp/knowledge_fusion/source_inventory.jsonl" ] && mkdir -p "$D/klp/knowledge_fusion" && cp "$B/klp/knowledge_fusion/source_inventory.jsonl" "$D/klp/knowledge_fusion/" && echo "  restored: klp/knowledge_fusion/source_inventory.jsonl"

echo "[safe-pull] DONE. Backup kept at $B"
echo "[safe-pull] git log:"
git log --oneline -3
