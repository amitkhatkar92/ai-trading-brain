"""release_manager/frz_models.py — Data models for all FRZ-001 phases."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SystemVersion:
    platform_version: str          # semver: MAJOR.MINOR.PATCH
    build_number: int
    git_commit: str                 # short (7-char)
    git_commit_full: str
    release_date: str
    release_name: str               # IIOS-V1.0.0
    db_versions: Dict[str, Any]
    research_version: str
    dna_version: str
    knowledge_version: str
    config_version: str
    container_version: str
    certification_status: str
    frz_status: str                 # FROZEN | DEVELOPMENT
    schema_version: int = 1
    previous_version: str = ""
    release_notes: str = ""
    protected_module_hashes: Dict[str, str] = field(default_factory=dict)


@dataclass
class ConfigSnapshot:
    timestamp: str
    git_commit: str
    env_keys: List[str]             # keys present (values masked)
    config_params: Dict[str, Any]   # non-sensitive config values
    scheduler_config: Dict[str, Any]
    risk_config: Dict[str, Any]
    portfolio_config: Dict[str, Any]
    broker_config: Dict[str, str]   # broker name + mode only, no tokens


@dataclass
class SyncVerification:
    timestamp: str
    local_commit: str
    remote_commit: str
    vps_commit: str
    container_commit: str
    local_remote_match: bool
    local_vps_match: bool
    local_container_match: bool
    overall_status: str             # MATCH | MISMATCH
    details: List[str] = field(default_factory=list)


@dataclass
class BackupRecord:
    timestamp: str
    backup_id: str
    git_commit: str
    local_path: str
    vps_path: str
    files_backed_up: int
    size_bytes: int
    success: bool
    error: str = ""


@dataclass
class ContainerVerification:
    timestamp: str
    image_commit: str
    container_commit: str
    manifest_commit: str
    runtime_hashes_ok: bool
    drift_files: List[str]
    container_status: str           # healthy | unhealthy | not_running
    dashboard_status: str
    overall_ok: bool
    details: List[str] = field(default_factory=list)


@dataclass
class RecoveryPoint:
    backup_id: str
    timestamp: str
    git_commit: str
    version: str
    local_path: str
    vps_path: str
    is_certified: bool


@dataclass
class ReleaseTag:
    tag_name: str                   # IIOS-V1.0.0
    version: str
    git_commit: str
    date: str
    release_notes: str
    certified: bool


@dataclass
class ProductionLockStatus:
    timestamp: str
    is_locked: bool
    changed_protected_modules: List[str]
    all_hashes_ok: bool
    requires_confirmation: bool
    details: List[str] = field(default_factory=list)


@dataclass
class StartupCheckResult:
    timestamp: str
    overall_ok: bool
    db_integrity: Dict[str, bool]
    config_ok: bool
    knowledge_ok: bool
    dna_ok: bool
    container_healthy: bool
    broker_connection: str          # LIVE | DEGRADED | PAPER | UNKNOWN
    scheduler_ok: bool
    disk_free_gb: float
    memory_free_mb: float
    cpu_pct: float
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ReleaseCertificate:
    date: str
    platform_version: str
    release_name: str
    git_commit: str
    architecture_status: str
    production_status: str
    prr_verdict: str
    ils_score: float
    gva_score: float
    sync_status: str
    container_status: str
    backup_status: str
    scientific_director_approval: str
    methodology_auditor_approval: str
    growth_validator_approval: str
    production_readiness: str
    narrative: str = ""
    certifying_agents: List[str] = field(default_factory=list)
