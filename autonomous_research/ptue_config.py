"""
ptue_config.py — Point-in-Time Universe Engine configuration.

IIOS Research Infrastructure — R-006.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PTUEConfig:
    """Configuration for the Point-in-Time Universe Engine.

    Parameters
    ----------
    history_root : str
        Root directory for universe history files.
        Structure: {history_root}/{UNIVERSE_NAME}/history.json
    static_fallback_path : str
        Path to the static nifty500_universe.json file.
        Used when history files are absent and fallback_enabled=True.
    fallback_enabled : bool
        Allow falling back to the static universe when history is unavailable.
        Every fallback is logged with a [PTUEFallback] tag.
    log_every_fallback : bool
        Emit a WARNING-level log for every individual fallback query.
        When False, only a single INFO is emitted at load time.
    cache_enabled : bool
        Cache resolved HistoricalUniverse objects.
        Cache key: (date, universe_name).
    dry_run : bool
        When True, never write any files (bootstrap/seed methods are no-ops).
    """
    history_root:           str   = "data/ars/ptue"
    static_fallback_path:   str   = "data/nifty500_universe.json"
    fallback_enabled:       bool  = True
    log_every_fallback:     bool  = True
    cache_enabled:          bool  = True
    dry_run:                bool  = False
