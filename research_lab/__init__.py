"""
Research Lab — Experimental Strategy Sandbox
=============================================
Isolated environment for testing new strategy ideas.

Public API::
    from research_lab import ResearchLab, ExperimentConfig, LabResult

    lab    = ResearchLab()
    config = ExperimentConfig(name="MyStrategy", description="...", params={})
    result = lab.run_experiment(config, signal_fn, snapshots)
"""

from .research_lab import ResearchLab, ExperimentConfig, LabResult, LabTrade

__all__ = ["ResearchLab", "ExperimentConfig", "LabResult", "LabTrade"]
