"""Dependency analysis script for A1 foundation packages."""
import sys, importlib, ast, os

BASE = "iios.ai.foundation"
FOUNDATION_DIR = r"C:\Users\UCIC\OneDrive\Desktop\ai_trading_brain\iios\ai\foundation"

packages = [
    "lifecycle", "adapters", "events", "cost", "metrics", "timeout",
    "retry", "session", "context", "request", "exceptions", "health",
    "config", "observability", "pipeline", "snapshot", "provider",
    "runtime", "container", "gateway",
]

def get_ai_imports(pkg_name, path):
    deps = set()
    for root, dirs, files in os.walk(path):
        for f in files:
            if not f.endswith(".py"): continue
            fp = os.path.join(root, f)
            try:
                tree = ast.parse(open(fp, encoding="utf-8").read())
            except:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Absolute: from iios.ai.foundation.X import ...
                    if node.module.startswith(BASE + "."):
                        sub = node.module[len(BASE)+1:].split(".")[0]
                        deps.add(sub)
                    # Relative: from ..X.Y import ... (level=2 means from parent pkg)
                    elif node.level >= 2 and node.module:
                        # level=2: go up 1 from current pkg = foundation.X
                        sub = node.module.split(".")[0]
                        if sub in packages:
                            deps.add(sub)
    return deps

print("Package dependency analysis:")
print("-" * 60)
for pkg in packages:
    path = os.path.join(FOUNDATION_DIR, pkg)
    if not os.path.isdir(path):
        continue
    deps = get_ai_imports(pkg, path)
    deps.discard(pkg)
    print(f"  {pkg:20s} -> {sorted(deps)}")
