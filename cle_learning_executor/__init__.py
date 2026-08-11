"""
cle_learning_executor — Cat-E Automatic DNA Learning Executor (CLE-001)

Public API:
    run_cat_e_learning(dry_run=False) -> dict   # main entry point
"""
from .cle_executor import run_cat_e_learning

__all__ = ["run_cat_e_learning"]
