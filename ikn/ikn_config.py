"""
ikn_config.py — Configuration for IKN-001.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IKNConfig:
    db_path:         str  = "data/ikn/ikn.db"
    reports_root:    str  = "data/ikn/reports"
    max_path_length: int  = 10
    dry_run:         bool = False

    def __post_init__(self) -> None:
        if self.max_path_length < 1:
            raise ValueError("max_path_length must be >= 1")
        if self.max_path_length > 50:
            raise ValueError("max_path_length must be <= 50")
