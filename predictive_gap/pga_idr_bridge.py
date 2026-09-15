"""predictive_gap/pga_idr_bridge.py — PGA Category B observation bridge.

Root-cause fix (2026-09-15): pga_learning.py::_try_reinforce_idr() called
IDRRepository.add_observation(symbol=..., direction=..., return_pct=..., ...)
— a method that does not exist. Audit confirmed this was not a simple typo:
IDRRepository (market_learning/idr_repository.py) is a feature/pattern-keyed
DNA store (dna_id = feature_name + direction) with NO symbol column anywhere
in its schema — it structurally cannot record a per-symbol observation.
HistoricalBehaviourEngine (opportunity_engine/historical_behaviour_engine.py)
is symbol-keyed but its OutcomeRecord requires many fields PGA's Category B
payload does not have (reference_entry, knowledge_target, knowledge_stop,
atr, scanner_confidence, ...) — fabricating those would inject zero-filled
noise into a live, trading-consequential evidence pool.

This module is the correctly-scoped fix: an isolated, append-only observation
log for PGA's own "was this symbol's move predicted?" signal. It does not
touch IDR or HBE and carries zero trading-decision weight — advisory/research
data only, exactly like every other Phase-3+ bridge in this project.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pga_config import PGA_DIR

log = logging.getLogger(__name__)

_OBS_FILE = PGA_DIR / "idr_reinforcement_observations.jsonl"


def record_reinforcement_observation(
    symbol: str,
    direction: str,
    return_pct: float,
    context: Optional[Dict[str, Any]] = None,
    obs_dir: Optional[Path] = None,
) -> bool:
    """
    Append a Category B "reinforce/weaken" observation for a symbol.

    Advisory-only — never read back into any live trading decision.
    Returns True on successful append, False on any I/O error (fail-open,
    matches the caller's existing try/except convention).
    """
    try:
        obs_dir = obs_dir if obs_dir is not None else PGA_DIR
        obs_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": symbol,
            "direction": direction,
            "return_pct": return_pct,
            "context": context or {},
        }
        with open(obs_dir / "idr_reinforcement_observations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return True
    except OSError as e:
        log.debug("[PGA-IDR-Bridge] Failed to append observation for %s: %s", symbol, e)
        return False


def get_observation_count(symbol: Optional[str] = None, obs_dir: Optional[Path] = None) -> int:
    """Read-only accessor: count of recorded observations, optionally filtered by symbol."""
    obs_dir = obs_dir if obs_dir is not None else PGA_DIR
    path = obs_dir / "idr_reinforcement_observations.jsonl"
    if not path.exists():
        return 0
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if symbol is None:
                    count += 1
                else:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("symbol") == symbol:
                        count += 1
    except OSError:
        return count
    return count


def get_last_observations(n: int = 20, obs_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read-only accessor (Phase 7 'Sandy' style): last n observations, oldest-first."""
    obs_dir = obs_dir if obs_dir is not None else PGA_DIR
    path = obs_dir / "idr_reinforcement_observations.jsonl"
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records[-n:]
