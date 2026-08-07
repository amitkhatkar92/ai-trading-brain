"""
release_manager/ph8_production_lock.py — Phase 8: Production Lock.

After certification, warns when core/protected modules are modified.
Requires explicit confirmation before deploying changes to protected modules.

Protected module list is defined in frz_config.PROTECTED_MODULES.
Hashes are stored in SYSTEM_VERSION.json.protected_module_hashes.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .frz_config import PROTECTED_MODULES, ROOT
from .frz_models import ProductionLockStatus

log = logging.getLogger(__name__)


def _sha256_short(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


def _current_hashes() -> Dict[str, str]:
    """Compute current hashes of all protected modules."""
    hashes: Dict[str, str] = {}
    for mod in PROTECTED_MODULES:
        p = ROOT / mod
        if p.is_file():
            hashes[mod] = _sha256_short(p)
        elif p.is_dir():
            for f in sorted(p.glob("*.py")):
                rel = str(f.relative_to(ROOT))
                hashes[rel] = _sha256_short(f)
    return hashes


def check_production_lock() -> ProductionLockStatus:
    """
    Compare current file hashes against hashes stored in SYSTEM_VERSION.json.
    Returns ProductionLockStatus with changed_protected_modules list.
    """
    ts = datetime.now(timezone.utc).isoformat()
    details: List[str] = []

    try:
        from .ph1_system_version import load_version
        sv = load_version()
        stored_hashes = sv.protected_module_hashes if sv else {}
        is_locked = sv.frz_status == "FROZEN" if sv else False
    except Exception:
        stored_hashes = {}
        is_locked = False

    if not stored_hashes:
        return ProductionLockStatus(
            timestamp=ts,
            is_locked=False,
            changed_protected_modules=[],
            all_hashes_ok=True,
            requires_confirmation=False,
            details=["No stored hashes — lock not yet established"],
        )

    current = _current_hashes()
    changed: List[str] = []

    for mod, stored_hash in stored_hashes.items():
        curr = current.get(mod, "")
        if not curr:
            changed.append(f"{mod} (MISSING)")
            details.append(f"MISSING: {mod}")
        elif curr != stored_hash:
            changed.append(mod)
            details.append(f"CHANGED: {mod} ({stored_hash[:8]} → {curr[:8]})")

    all_ok = (len(changed) == 0)
    requires_conf = (is_locked and not all_ok)

    if requires_conf:
        log.warning(
            "[ProductionLock] ⚠️  ARCHITECTURE FROZEN — %d protected module(s) changed: %s",
            len(changed), ", ".join(changed),
        )
        log.warning(
            "[ProductionLock] Run 'python -m release_manager.frz_runner lock --confirm' "
            "to acknowledge and proceed.",
        )
    elif not all_ok:
        log.info("[ProductionLock] %d module(s) changed (system not yet locked).", len(changed))
    else:
        log.info("[ProductionLock] All %d protected modules unchanged ✅", len(stored_hashes))

    return ProductionLockStatus(
        timestamp                = ts,
        is_locked                = is_locked,
        changed_protected_modules= changed,
        all_hashes_ok            = all_ok,
        requires_confirmation    = requires_conf,
        details                  = details,
    )


def confirm_production_changes(reason: str) -> bool:
    """
    Explicitly acknowledge changes to protected modules.
    Updates SYSTEM_VERSION.json hashes so the lock resets.
    """
    try:
        from .ph1_system_version import load_version, write_version
        sv = load_version()
        if sv is None:
            log.warning("[ProductionLock] No SYSTEM_VERSION.json to update")
            return False
        sv.protected_module_hashes = _current_hashes()
        sv.release_notes = f"Protected modules updated: {reason}"
        write_version(sv)
        log.info(
            "[ProductionLock] Hash snapshot updated — %d modules. Reason: %s",
            len(sv.protected_module_hashes), reason,
        )
        return True
    except Exception as e:
        log.error("[ProductionLock] Failed to update hashes: %s", e)
        return False
