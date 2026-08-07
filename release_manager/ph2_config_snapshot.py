"""
release_manager/ph2_config_snapshot.py — Phase 2: Master Config Snapshot.

Saves a read-only point-in-time snapshot of all configuration parameters.
Sensitive values (tokens, keys) are masked. Never stored in git.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .frz_config import CONFIG_SNAPSHOT_DIR, ROOT
from .frz_models import ConfigSnapshot

log = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "ACCESS_TOKEN", "CLIENT_ID", "SECRET", "PASSWORD", "TOKEN", "API_KEY",
    "DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
}


def _mask(key: str, val: Any) -> Any:
    key_up = key.upper()
    if any(s in key_up for s in _SENSITIVE_KEYS):
        return "***MASKED***"
    return val


def _load_env_keys() -> List[str]:
    """Return list of .env key names (no values)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return []
    keys = []
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                keys.append(line.split("=", 1)[0].strip())
    except Exception:
        pass
    return keys


def _load_config_params() -> Dict[str, Any]:
    """Load non-sensitive config values from config.py."""
    params: Dict[str, Any] = {}
    try:
        import config as _cfg
        for key in dir(_cfg):
            if key.startswith("_"):
                continue
            val = getattr(_cfg, key)
            if callable(val) or hasattr(val, "__module__"):
                continue
            params[key] = _mask(key, val)
    except Exception as e:
        log.warning("[ConfigSnapshot] Cannot load config: %s", e)
    return params


def _scheduler_config() -> Dict[str, Any]:
    """Extract SCHEDULE and timing constants from config."""
    try:
        import config as _cfg
        sched: Dict[str, Any] = {}
        if hasattr(_cfg, "SCHEDULE"):
            sched["SCHEDULE"] = {k: str(v) for k, v in _cfg.SCHEDULE.items()}
        if hasattr(_cfg, "CONTINUOUS_SCAN_INTERVAL"):
            sched["CONTINUOUS_SCAN_INTERVAL"] = _cfg.CONTINUOUS_SCAN_INTERVAL
        return sched
    except Exception:
        return {}


def _risk_config() -> Dict[str, Any]:
    """Extract risk management parameters."""
    try:
        import config as _cfg
        return {
            k: getattr(_cfg, k)
            for k in (
                "TOTAL_CAPITAL", "MIN_CONFIDENCE_SCORE", "MIN_ADV_CRORE",
                "MAX_ADV_PCT", "PAPER_TRADING",
            )
            if hasattr(_cfg, k)
        }
    except Exception:
        return {}


def _portfolio_config() -> Dict[str, Any]:
    try:
        import config as _cfg
        return {k: getattr(_cfg, k) for k in ("ALLOCATION",) if hasattr(_cfg, k)}
    except Exception:
        return {}


def _broker_config() -> Dict[str, str]:
    try:
        import config as _cfg
        return {
            "active_broker": str(getattr(_cfg, "ACTIVE_BROKER", "?")),
            "paper_trading":  str(getattr(_cfg, "PAPER_TRADING", True)),
        }
    except Exception:
        return {}


def take_config_snapshot(commit: str = "") -> ConfigSnapshot:
    """Take a full configuration snapshot and write it to disk."""
    CONFIG_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    snap = ConfigSnapshot(
        timestamp       = ts,
        git_commit      = commit,
        env_keys        = _load_env_keys(),
        config_params   = _load_config_params(),
        scheduler_config= _scheduler_config(),
        risk_config     = _risk_config(),
        portfolio_config= _portfolio_config(),
        broker_config   = _broker_config(),
    )

    # Write the snapshot (date-stamped, read-only by convention)
    snap_path = CONFIG_SNAPSHOT_DIR / f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    payload = {
        "timestamp":        snap.timestamp,
        "git_commit":       snap.git_commit,
        "env_keys":         snap.env_keys,
        "config_params":    snap.config_params,
        "scheduler_config": snap.scheduler_config,
        "risk_config":      snap.risk_config,
        "portfolio_config": snap.portfolio_config,
        "broker_config":    snap.broker_config,
    }
    snap_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    log.info("[ConfigSnapshot] Saved %s (%d config keys)", snap_path.name, len(snap.config_params))

    # Also write latest symlink (just overwrite latest.json)
    latest = CONFIG_SNAPSHOT_DIR / "latest.json"
    latest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    return snap


def build_config_snapshot_md(snap: ConfigSnapshot) -> str:
    """Render CONFIGURATION_SNAPSHOT.md content."""
    risk_rows = "\n".join(
        f"| {k} | {v} |" for k, v in snap.risk_config.items()
    )
    sched_rows = "\n".join(
        f"| {k} | {v} |"
        for k, v in (snap.scheduler_config.get("SCHEDULE") or snap.scheduler_config).items()
    )
    broker_rows = "\n".join(f"| {k} | {v} |" for k, v in snap.broker_config.items())
    env_list    = "\n".join(f"- {k}" for k in snap.env_keys)

    return f"""# CONFIGURATION_SNAPSHOT
_Captured: {snap.timestamp} | Commit: {snap.git_commit}_

## Environment Variables (keys only)

{env_list or "_No .env file found_"}

## Risk Configuration

| Parameter | Value |
|-----------|-------|
{risk_rows or "_N/A_"}

## Scheduler Configuration

| Slot | Time |
|------|------|
{sched_rows or "_N/A_"}

## Broker Configuration

| Parameter | Value |
|-----------|-------|
{broker_rows or "_N/A_"}

## Portfolio Allocation

```json
{json.dumps(snap.portfolio_config, indent=2, default=str)}
```

_This snapshot is read-only. Produced automatically before each deployment._
"""
