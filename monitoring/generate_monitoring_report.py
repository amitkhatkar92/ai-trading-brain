"""
Daily First-Month Monitoring Report Generator
==============================================
Run this daily to export KPI snapshots and alert on deviations.

Usage:
    python monitoring/generate_monitoring_report.py
    
Or run from main.py:
    from monitoring.generate_monitoring_report import generate_report
    generate_report(root_dir)
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict
from monitoring.first_month_tracker import FirstMonthTracker


def generate_report(root_dir: str = None) -> Dict:
    """
    Generate and save daily monitoring report.
    
    Returns:
        Dict with KPI snapshot and alerts
    """
    if root_dir is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Initialize tracker
    tracker = FirstMonthTracker(initial_capital=1_000_000, root_dir=root_dir)
    tracker.update()
    
    # Get KPI snapshot
    kpi_data = tracker.export_json()
    
    # Generate alerts for any KPIs below goal
    alerts = []
    if not kpi_data["kpis"]["signal_accuracy"]["ok"]:
        win_rate = kpi_data["kpis"]["signal_accuracy"]["percent"]
        alerts.append(f"⚠️  SIGNAL ACCURACY BELOW TARGET: {win_rate:.2f}% (goal: 40%)")
    
    if not kpi_data["kpis"]["execution_slippage"]["ok"]:
        slippage = kpi_data["kpis"]["execution_slippage"]["percent"]
        alerts.append(f"⚠️  EXECUTION SLIPPAGE EXCEEDED: {slippage:.4f}% (goal: < 0.15%)")
    
    if not kpi_data["kpis"]["drawdown"]["ok"]:
        dd = kpi_data["kpis"]["drawdown"]["percent"]
        alerts.append(f"⚠️  DRAWDOWN EXCEEDED: {dd:.2f}% (goal: < 5%)")
    
    if not kpi_data["kpis"]["uptime"]["ok"]:
        uptime = kpi_data["kpis"]["uptime"]["percent"]
        alerts.append(f"⚠️  SYSTEM UPTIME BELOW TARGET: {uptime:.2f}% (goal: 100%)")
    
    # Save daily snapshot
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(data_dir, f"monitoring_report_{today}.json")
    
    report_data = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "kpi_snapshot": kpi_data,
        "alerts": alerts,
        "status": "OK" if kpi_data["all_kpis_met"] else "ALERT"
    }
    
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    return report_data


def print_monitoring_summary(report: Dict) -> None:
    """Print formatted summary of monitoring report."""
    
    kpis = report["kpi_snapshot"]["kpis"]
    trading = report["kpi_snapshot"]["trading"]
    
    print("\n" + "="*80)
    print(f"FIRST-MONTH MONITORING REPORT — {report['date']}")
    print("="*80)
    
    print("\n📊 KPI STATUS:")
    print(f"  ✅ Signal Accuracy:    {kpis['signal_accuracy']['percent']:6.2f}% (goal: ≥ 40.00%)" if kpis['signal_accuracy']['ok'] else f"  ⚠️  Signal Accuracy:    {kpis['signal_accuracy']['percent']:6.2f}% (goal: ≥ 40.00%)")
    print(f"  ✅ Exec Slippage:      {kpis['execution_slippage']['percent']:6.4f}% (goal: < 0.15%)" if kpis['execution_slippage']['ok'] else f"  ⚠️  Exec Slippage:      {kpis['execution_slippage']['percent']:6.4f}% (goal: < 0.15%)")
    print(f"  ✅ Drawdown:           {kpis['drawdown']['percent']:6.2f}% (goal: < 5.00%)" if kpis['drawdown']['ok'] else f"  ⚠️  Drawdown:           {kpis['drawdown']['percent']:6.2f}% (goal: < 5.00%)")
    print(f"  ✅ System Uptime:      {kpis['uptime']['percent']:6.2f}% (goal: 100%)" if kpis['uptime']['ok'] else f"  ⚠️  System Uptime:      {kpis['uptime']['percent']:6.2f}% (goal: 100%)")
    
    print(f"\n📈 TRADING ACTIVITY:")
    print(f"  Closed Trades:  {trading['closed_trades']}")
    print(f"  Open Trades:    {trading['open_trades']}")
    print(f"  Total Trades:   {trading['total_trades']}")
    print(f"  Avg Win (R):    +{trading['avg_win_r']:.2f}")
    print(f"  Avg Loss (R):   {trading['avg_loss_r']:.2f}")
    print(f"  Best Trade:     +{trading['best_trade_r']:.2f}R")
    print(f"  Worst Trade:    {trading['worst_trade_r']:.2f}R")
    
    if report["alerts"]:
        print(f"\n⚠️  ALERTS ({len(report['alerts'])}):")
        for alert in report["alerts"]:
            print(f"  {alert}")
    else:
        print("\n✅ NO ALERTS — All KPIs within targets")
    
    print(f"\n🎯 OVERALL STATUS: {report['status']}")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run report generator
    report = generate_report()
    print_monitoring_summary(report)
    
    # Also print detailed reports
    tracker = FirstMonthTracker()
    tracker.update()
    print(tracker.get_daily_report())
    print("\n")
    print(tracker.get_weekly_report())
