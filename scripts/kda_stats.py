import json, pathlib
from collections import Counter

kda_dir = pathlib.Path("data/klp/kda")
c = Counter()
total = 0
if kda_dir.exists():
    for f in sorted(kda_dir.glob("kda_decisions_*.jsonl")):
        with f.open() as fh:
            for line in fh:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        c[rec.get("decision", "")] += 1
                        total += 1
                    except:
                        pass
print("KDA decisions:", dict(c))
print("Total KDA records:", total)

