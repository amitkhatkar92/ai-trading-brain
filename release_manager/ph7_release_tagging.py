"""
release_manager/ph7_release_tagging.py — Phase 7: Release Tagging.

Creates and manages IIOS-Vx.y.z git release tags with embedded release notes.
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .frz_config import ROOT
from .frz_models import ReleaseTag

log = logging.getLogger(__name__)


def _git(cmd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 1, str(e)


def list_release_tags() -> List[ReleaseTag]:
    """Return all IIOS-V* tags sorted by version (newest first)."""
    _, out = _git("git tag -l 'IIOS-V*' --sort=-version:refname")
    tags: List[ReleaseTag] = []
    for tag in out.splitlines():
        if not tag.strip():
            continue
        _, commit = _git(f"git rev-list -n 1 {tag}")
        _, tag_msg = _git(f"git tag -l --format='%(contents)' {tag}")
        tags.append(ReleaseTag(
            tag_name    = tag.strip(),
            version     = tag.strip().replace("IIOS-V", ""),
            git_commit  = commit[:7] if commit else "unknown",
            date        = "",
            release_notes = tag_msg or "",
            certified   = True,
        ))
    return tags


def create_release_tag(
    version: Optional[str] = None,
    release_notes: str = "",
    certified: bool = True,
    push: bool = True,
) -> ReleaseTag:
    """
    Create a signed/annotated git tag IIOS-V<version>.

    If version is None, reads from SYSTEM_VERSION.json.
    """
    if version is None:
        try:
            from .ph1_system_version import load_version
            sv = load_version()
            version = sv.platform_version if sv else "1.0.0"
        except Exception:
            version = "1.0.0"

    tag_name  = f"IIOS-V{version}"
    today     = datetime.now(timezone.utc).date().isoformat()
    _, commit = _git("git rev-parse --short HEAD")

    # Check if tag already exists
    _, existing = _git(f"git tag -l {tag_name}")
    if existing.strip():
        log.warning("[ReleaseTag] Tag %s already exists — skipping", tag_name)
        return ReleaseTag(
            tag_name=tag_name, version=version, git_commit=commit,
            date=today, release_notes=release_notes, certified=certified,
        )

    # Build tag message
    note_lines = [
        f"IIOS Release {tag_name}",
        f"Date: {today}",
        f"Commit: {commit}",
        f"Status: {'CERTIFIED' if certified else 'DEVELOPMENT'}",
        "",
        release_notes or f"Architecture Freeze release — FRZ-001",
    ]
    tag_message = "\n".join(note_lines)

    # Create annotated tag
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(tag_message)
        tmp_path = tmp.name
    try:
        rc, out = _git(f'git tag -a {tag_name} -F "{tmp_path}"')
    finally:
        os.unlink(tmp_path)

    if rc != 0:
        log.error("[ReleaseTag] Failed to create tag %s: %s", tag_name, out)
    else:
        log.info("[ReleaseTag] Created tag %s at %s", tag_name, commit)
        if push:
            rc2, out2 = _git(f"git push origin {tag_name}")
            if rc2 == 0:
                log.info("[ReleaseTag] Pushed %s to origin", tag_name)
            else:
                log.warning("[ReleaseTag] Push failed (non-critical): %s", out2)

    return ReleaseTag(
        tag_name      = tag_name,
        version       = version,
        git_commit    = commit,
        date          = today,
        release_notes = tag_message,
        certified     = certified,
    )
