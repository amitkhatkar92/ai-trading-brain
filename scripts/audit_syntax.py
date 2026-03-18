"""Quick syntax audit — run from project root."""
import os, py_compile, sys

root = os.getcwd()   # must be run from project root
errors = []
ok = 0
SKIP = {'__pycache__', '.venv', '.git', 'node_modules'}

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if not f.endswith('.py'):
            continue
        fp = os.path.join(dirpath, f)
        try:
            py_compile.compile(fp, doraise=True)
            ok += 1
        except py_compile.PyCompileError as e:
            errors.append(fp.replace(root + os.sep, '') + ' :: ' + str(e))

print(f"\n{'='*60}")
print(f"  SYNTAX AUDIT — {ok} OK  |  {len(errors)} ERRORS")
print(f"{'='*60}")
if errors:
    for e in errors:
        print(f"  FAIL: {e}")
else:
    print("  All files clean.")
print(f"{'='*60}\n")
sys.exit(len(errors))
