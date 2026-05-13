import os
from datetime import datetime

today = datetime(2026, 4, 15).date()
all_files = []
skip_dirs = {'.venv', '__pycache__', '.git', 'node_modules'}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        path = os.path.join(root, f)
        try:
            mt = os.path.getmtime(path)
            mdt = datetime.fromtimestamp(mt)
            if mdt.date() == today:
                all_files.append((mdt, path, os.path.getsize(path)))
        except Exception:
            pass

print(f"Files modified today ({today}): {len(all_files)}")
print()
for mdt, path, size in sorted(all_files, reverse=True):
    clean = path.replace('.\\', '')
    ts = mdt.strftime('%H:%M:%S')
    print(f"{ts}  {size:8d}  {clean}")
