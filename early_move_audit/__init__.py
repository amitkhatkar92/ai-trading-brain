"""
early_move_audit — EMP-001: Early-Move Persistence & Previous-Day Predictive Value Audit
=========================================================================================

Pure observational research module.  Does NOT modify any live trading component.

Public API
----------
run_emp_audit(days, date_str, symbols, top_n, dry_run) -> EMPResult
"""
from __future__ import annotations

from .emp_runner import run_emp_audit
from .emp_config import EmpConfig

__all__ = ["run_emp_audit", "EmpConfig"]
