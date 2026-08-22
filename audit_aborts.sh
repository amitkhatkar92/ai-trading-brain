#!/bin/bash
LOGDIR="/var/lib/docker/containers/23d5c943c60723eef504d892eeffb36ba360bb730041d286376143e3b147ed76"

python3 << 'PYEOF'
import subprocess, json, sys

logdir = "/var/lib/docker/containers/23d5c943c60723eef504d892eeffb36ba360bb730041d286376143e3b147ed76"
import glob, os

files = sorted(glob.glob(logdir + "/*.log") + glob.glob(logdir + "/*.log.1") + glob.glob(logdir + "/*.log.2"))

aborts = []
for f in files:
    try:
        with open(f, 'r', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    log_line = data.get('log', '').strip()
                except:
                    log_line = line
                if 'CRITICAL latency: MarketIntelligence' in log_line and 'ALERT' not in log_line:
                    aborts.append(log_line)
    except Exception as e:
        print(f"Error reading {f}: {e}", file=sys.stderr)

aborts.sort()
for a in aborts:
    print(a)
PYEOF
