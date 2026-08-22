#!/bin/bash
# Run on VPS: bash /tmp/rebuild_manifest.sh
cd /root/ai-trading-brain
echo "=== Generating build_manifest.json ==="
python3 scripts/generate_build_manifest.py
echo ""
echo "=== Manifest contents ==="
python3 - <<'EOF'
import json
m = json.load(open("build_manifest.json"))
print(f"commit : {m.get('commit')}")
print(f"built  : {m.get('built_at')}")
fh = m.get("file_hashes", {})
print(f"files  : {len(fh)}")
for k, v in fh.items():
    print(f"  {k[:12]:<55} {v[:12]}")
missing = m.get("missing", [])
if missing:
    print(f"MISSING: {missing}")
EOF
echo ""
echo "=== Done ==="
