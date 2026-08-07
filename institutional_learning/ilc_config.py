"""institutional_learning/ilc_config.py — ILC-001 configuration."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

ILC_DIR              = DATA / "ilc"
LEARNING_REGISTRY    = ILC_DIR / "learning_registry.json"
LIFECYCLE_DB_PATH    = ILC_DIR / "knowledge_lifecycle.json"
CT_DB                = DATA / "control_tower.db"
DNA_DB               = DATA / "mls" / "institutional_dna.db"
UNIVERSE_FILE        = DATA / "nifty500_universe.json"
PAPER_TRADES_CSV     = DATA / "paper_trades.csv"
EDGES_FILE           = DATA / "discovered_edges.json"
HYP_REGISTRY_PATH    = DATA / "ars_hypothesis_registry.json"

# Verification windows (trading days)
VERIFICATION_WINDOWS = [30, 60, 90]

# How many calendar days approximates each trading-day window
CALENDAR_DAYS_MAP    = {30: 45, 60: 90, 90: 135}

# ILC operates on top 20 (PGA does top 5 for speed; ILC does top 20 for completeness)
ILC_TOP_N = 20

# Expected Improvement Gain weights
EIG_WEIGHTS = {
    "A": 0.75,   # calibration — moderate gain, low cost
    "B": 0.60,   # knowledge reinforcement
    "C": 0.50,   # new hypothesis — uncertain gain
    "D": 0.65,   # scheduled research
    "E": 0.80,   # DNA candidate — high value when confirmed
    "F": 0.70,   # HKAP historical gap
    "G": 0.60,   # KDE relationship gap
}

# Target system implementation cost (0–1, lower = cheaper)
TARGET_COST = {
    "CALIBRATION":  0.10,
    "IDR":          0.20,
    "HYPOTHESIS":   0.15,
    "RC":           0.40,
    "HKAP":         0.35,
    "KDE":          0.35,
    "SD":           0.25,
}

# Confidence thresholds
CONFIDENCE_HIGH_DNA_MIN        = 3
CONFIDENCE_HIGH_MOVE_MIN_PCT   = 2.0
CONFIDENCE_MEDIUM_DNA_MIN      = 1
CONFIDENCE_MEDIUM_MOVE_MIN_PCT = 1.0

# Score weights (Phase 11)
SCORE_WEIGHTS = {
    "learning_efficiency":       0.25,
    "knowledge_efficiency":      0.20,
    "prediction_improvement":    0.25,
    "research_productivity":     0.15,
    "knowledge_roi":             0.15,
}
