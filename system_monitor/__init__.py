"""
System Monitor Layer
====================
Operational health tracking for the AI Trading Brain.

Public API::
    from system_monitor import SystemMonitor, HealthReport

    monitor = SystemMonitor()
    monitor.start_cycle()

    with monitor.time_layer("GlobalIntelligence"):
        bias = self.global_intelligence.run()

    report = monitor.finalize_cycle()
    monitor.print_cycle_table(report)
"""

from .system_monitor import SystemMonitor, HealthReport, LayerTiming

__all__ = ["SystemMonitor", "HealthReport", "LayerTiming"]
