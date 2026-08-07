"""
growth_validator/gva_config.py
================================
GVA-001 — Growth Validator & Assessor — Configuration

All constants used across the GVA package.
The validator is read-only: it never modifies any knowledge store.
"""
from __future__ import annotations

from pathlib import Path

# ── Workspace root ───────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
GVA_DIR = DATA / "gva"

# ── Primary data sources (READ ONLY) ────────────────────────────────────────
FILE_HYPOTHESIS_REG   = DATA / "ars_hypothesis_registry.json"
FILE_DISCOVERED_EDGES = DATA / "discovered_edges.json"
FILE_EDE_FEATURES     = DATA / "ede_feature_db.json"
FILE_STRATEGY_PERF    = DATA / "strategy_performance.json"
FILE_REPLAY_SUMMARY   = DATA / "replay_summary.json"
FILE_PAPER_DAILY      = DATA / "paper_trading_daily.json"
FILE_RE001A           = DATA / "re001a_results.json"

STUDY_FILES = {
    "study002":      DATA / "study002_results.json",
    "study002a":     DATA / "study002a_results.json",
    "ars_study_003": DATA / "ars_study_003.json",
    "ars_study_h001":DATA / "ars_study_h001.json",
    "ars_study_irp002": DATA / "ars_study_irp002.json",
}

# Report directories
REPORT_DIRS = {
    "kva":   DATA / "kva",      # KVA knowledge validator
    "h001":  DATA / "h001",
    "rii001":DATA / "rii001",
    "irp002":DATA / "irp002",
}

# ── DB paths ─────────────────────────────────────────────────────────────────
DB_IKN          = DATA / "ikn"   / "ikn.db"
DB_DNA          = DATA / "mls"   / "institutional_dna.db"
DB_CONTROL      = DATA / "control_tower.db"
DB_REPLAY       = DATA / "replay.db"
DB_STUDY002_REP = DATA / "study002_replay.db"

# ── Overall score thresholds ─────────────────────────────────────────────────
SCORE_SELF_IMPROVING    = 86   # 86–100
SCORE_RAPIDLY_IMPROVING = 71   # 71–85
SCORE_IMPROVING         = 56   # 56–70
SCORE_SLOWLY_IMPROVING  = 41   # 41–55
SCORE_STATIC            = 21   # 21–40
# Below 21 = DECLINING

# ── Growth direction thresholds ──────────────────────────────────────────────
DIR_IMPROVE_THRESHOLD = 5.0    # > 5% growth → IMPROVING
DIR_DECLINE_THRESHOLD = -5.0   # < -5% → DECLINING

# ── Dimension weights for overall score ──────────────────────────────────────
WEIGHT_KNOWLEDGE    = 0.25
WEIGHT_SCIENTIFIC   = 0.25
WEIGHT_DNA          = 0.20
WEIGHT_PLATFORM     = 0.15
WEIGHT_LEARNING     = 0.15
