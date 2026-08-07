"""
release_manager/ph1_system_version.py — Phase 1: Architecture Freeze Version File.

Creates and manages SYSTEM_VERSION.json — the single authoritative version
record for IIOS. Extends the existing build_manifest.json (never replaces it).
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .frz_config import (
    DATA,
    INITIAL_VERSION,
    PROTECTED_MODULES,
    ROOT,
    VERSION_FILE,
    VERSION_FILE_SCHEMA,
)
from .frz_models import SystemVersion

log = logging.getLogger(__name__)

_BUILD_MANIFEST = ROOT / "build_manifest.json"


def _git(cmd: str) -> str:
    """Run a git command and return stripped stdout, '' on error."""
    try:
        result = subprocess.run(
            f"git {cmd}", shell=True, capture_output=True, text=True, cwd=ROOT
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]   # 16-char prefix is sufficient for change detection
    except Exception:
        return ""


def _db_version(db_rel_path: str) -> str:
    """Get SQLite user_version pragma for a DB file."""
    try:
        import sqlite3
        db = DATA / db_rel_path.lstrip("data/")
        if not db.exists():
            return "absent"
        with sqlite3.connect(db) as conn:
            v = conn.execute("PRAGMA user_version").fetchone()[0]
        return str(v)
    except Exception:
        return "unknown"


def _count_table(db_path: str, table: str) -> int:
    try:
        import sqlite3
        p = ROOT / db_path
        if not p.exists():
            return 0
        with sqlite3.connect(p) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return 0


def _protected_hashes() -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for mod in PROTECTED_MODULES:
        p = ROOT / mod
        if p.is_file():
            hashes[mod] = _sha256(p)
        elif p.is_dir():
            # Hash each .py file in the directory (non-recursive for simplicity)
            for f in sorted(p.glob("*.py")):
                rel = str(f.relative_to(ROOT))
                hashes[rel] = _sha256(f)
    return hashes


def load_version() -> Optional[SystemVersion]:
    """Load current SYSTEM_VERSION.json, return None if absent."""
    if not VERSION_FILE.exists():
        return None
    try:
        d = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        return SystemVersion(**{k: v for k, v in d.items() if k in SystemVersion.__dataclass_fields__})
    except Exception as e:
        log.warning("[SystemVersion] Cannot load %s: %s", VERSION_FILE, e)
        return None


def write_version(sv: SystemVersion) -> None:
    """Write SYSTEM_VERSION.json to disk."""
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version":        sv.schema_version,
        "platform_version":      sv.platform_version,
        "build_number":          sv.build_number,
        "git_commit":            sv.git_commit,
        "git_commit_full":       sv.git_commit_full,
        "release_date":          sv.release_date,
        "release_name":          sv.release_name,
        "db_versions":           sv.db_versions,
        "research_version":      sv.research_version,
        "dna_version":           sv.dna_version,
        "knowledge_version":     sv.knowledge_version,
        "config_version":        sv.config_version,
        "container_version":     sv.container_version,
        "certification_status":  sv.certification_status,
        "frz_status":            sv.frz_status,
        "previous_version":      sv.previous_version,
        "release_notes":         sv.release_notes,
        "protected_module_hashes": sv.protected_module_hashes,
    }
    VERSION_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("[SystemVersion] Written: %s (%s)", sv.release_name, sv.git_commit)


def create_or_update_version(
    bump: str = "patch",          # major | minor | patch | none
    release_notes: str = "",
    frz_status: str = "FROZEN",
) -> SystemVersion:
    """
    Create or bump SYSTEM_VERSION.json.
    Reads existing version, bumps it, writes updated version.
    """
    existing = load_version()
    commit_full = _git("rev-parse HEAD") or "unknown"
    commit      = commit_full[:7] if len(commit_full) >= 7 else commit_full
    today       = datetime.now(timezone.utc).date().isoformat()

    if existing:
        prev_ver = existing.platform_version
        prev_build = existing.build_number
        parts = [int(x) for x in prev_ver.split(".")]
        if bump == "major":
            parts = [parts[0]+1, 0, 0]
        elif bump == "minor":
            parts = [parts[0], parts[1]+1, 0]
        elif bump == "patch":
            parts = [parts[0], parts[1], parts[2]+1]
        new_ver = ".".join(str(p) for p in parts)
        build_num = prev_build + 1
    else:
        prev_ver  = ""
        new_ver   = INITIAL_VERSION
        build_num = 1

    release_name = f"IIOS-V{new_ver}"

    # Load counts for descriptive versions
    dna_count = _count_table("data/mls/institutional_dna.db", "dna")
    edge_count = 0
    try:
        edge_file = ROOT / "data" / "discovered_edges.json"
        if edge_file.exists():
            edge_count = len(json.loads(edge_file.read_text(encoding="utf-8")))
    except Exception:
        pass

    sv = SystemVersion(
        schema_version       = VERSION_FILE_SCHEMA,
        platform_version     = new_ver,
        build_number         = build_num,
        git_commit           = commit,
        git_commit_full      = commit_full,
        release_date         = today,
        release_name         = release_name,
        db_versions          = {
            "control_tower":       _db_version("control_tower.db"),
            "institutional_dna":   _db_version("mls/institutional_dna.db"),
            "schema_version":      VERSION_FILE_SCHEMA,
        },
        research_version     = "H001:CONFIRMED",
        dna_version          = f"{dna_count}-records",
        knowledge_version    = f"{edge_count}-edges",
        config_version       = commit,
        container_version    = new_ver,
        certification_status = "PRODUCTION_READY_WITH_OBSERVATIONS",
        frz_status           = frz_status,
        previous_version     = prev_ver,
        release_notes        = release_notes or f"FRZ-001: Architecture Freeze (build {build_num})",
        protected_module_hashes = _protected_hashes(),
    )
    write_version(sv)
    return sv
