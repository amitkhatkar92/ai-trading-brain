"""release_manager/frz_config.py — FRZ-001 configuration constants."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# ── Storage paths ─────────────────────────────────────────────────────────
FRZ_DIR              = DATA / "frz"
BACKUP_DIR           = FRZ_DIR / "backups"
REPORT_DIR           = FRZ_DIR / "reports"
CONFIG_SNAPSHOT_DIR  = FRZ_DIR / "config_snapshots"
VERSION_FILE         = ROOT / "SYSTEM_VERSION.json"

# ── VPS / deploy ──────────────────────────────────────────────────────────
VPS_HOST         = "root@178.18.252.24"
SSH_KEY          = str(Path.home() / ".ssh" / "trading_vps")
VPS_PROJECT_DIR  = "/root/ai-trading-brain"
VPS_BACKUP_DIR   = "/root/ai-trading-brain/backups"
CONTAINER_NAME   = "ai-trading-brain"
DASHBOARD_NAME   = "trading-dashboard"

# ── Version ───────────────────────────────────────────────────────────────
INITIAL_VERSION  = "1.0.0"
VERSION_FILE_SCHEMA = 1

# ── Production lock — protected modules (from ARCHITECTURE.md) ────────────
PROTECTED_MODULES: list[str] = [
    "risk_guardian/risk_guardian.py",
    "strategy_lab/backtesting_ai.py",
    "validation_engine/",
    "data_feeds/dhan_feed.py",
    "main.py",
    "config.py",
    "orchestrator/master_orchestrator.py",
    "execution_engine/order_manager.py",
]

# ── Backup items ─────────────────────────────────────────────────────────
LOCAL_BACKUP_ITEMS: list[str] = [
    "config.py",
    "main.py",
    "build_manifest.json",
    "SYSTEM_VERSION.json",
    "data/mls/institutional_dna.db",
    "data/control_tower.db",
    "data/ilc/learning_registry.json",
    "data/discovered_edges.json",
    "data/ars_hypothesis_registry.json",
    "data/nifty500_universe.json",
    "data/paper_trades.csv",
]

# ── Databases to integrity-check at startup ───────────────────────────────
DATABASES_TO_CHECK: list[str] = [
    "data/mls/institutional_dna.db",
    "data/control_tower.db",
]

# Disk space minimum before deployment (GB)
MIN_FREE_DISK_GB   = 1.0
MIN_FREE_MEMORY_MB = 256

# ── Sync verification: how many retries before failing ────────────────────
SYNC_VERIFY_TIMEOUT_S = 30

# ── Startup check items ───────────────────────────────────────────────────
REQUIRED_CONFIG_KEYS = [
    "TOTAL_CAPITAL", "MIN_CONFIDENCE_SCORE", "MIN_ADV_CRORE", "PAPER_TRADING",
]
