"""
First-Month KPI Dashboard — Streamlit Page
===========================================
Real-time monitoring of first-month KPI goals.

Add to main dashboard by including in tab:
    with tab_kpi:
        show_first_month_kpi_dashboard()
"""

import streamlit as st
from datetime import datetime
import json
import os
from pathlib import Path

# Import monitoring
try:
    from monitoring.first_month_tracker import FirstMonthTracker
    from monitoring.generate_monitoring_report import generate_report, print_monitoring_summary
except ImportError:
    st.error("Monitoring module not found. Please ensure monitoring/ is in PYTHONPATH.")
    st.stop()


def show_first_month_kpi_dashboard():
    """Display first-month KPI monitoring dashboard."""
    
    # Title
    st.markdown("# 📊 First-Month KPI Monitoring")
    st.markdown("**Goals for March 2026:** Track 4 critical metrics")
    
    # Initialize tracker
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tracker = FirstMonthTracker(initial_capital=1_000_000, root_dir=root_dir)
    tracker.update()
    
    kpi_data = tracker.export_json()
    kpis = kpi_data["kpis"]
    trading = kpi_data["trading"]
    
    # ═══════════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ═══════════════════════════════════════════════════════════════════════
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Signal Accuracy
    with col1:
        win_rate = kpis["signal_accuracy"]["percent"]
        is_ok = kpis["signal_accuracy"]["ok"]
        status_color = "🟢" if is_ok else "🔴"
        
        st.metric(
            label="Signal Accuracy",
            value=f"{win_rate:.1f}%",
            delta=f"Goal: ≥40%",
            delta_color="normal"
        )
        st.markdown(f"{status_color} {'✅ ON TARGET' if is_ok else '⚠️  BELOW TARGET'}".center(22))
    
    # Execution Slippage
    with col2:
        slippage = kpis["execution_slippage"]["percent"]
        is_ok = kpis["execution_slippage"]["ok"]
        status_color = "🟢" if is_ok else "🔴"
        
        st.metric(
            label="Execution Slippage",
            value=f"{slippage:.4f}%",
            delta=f"Goal: <0.15%",
            delta_color="normal"
        )
        st.markdown(f"{status_color} {'✅ ON TARGET' if is_ok else '⚠️  EXCEEDED'}".center(22))
    
    # Drawdown
    with col3:
        drawdown = kpis["drawdown"]["percent"]
        max_dd = kpis["drawdown"]["maximum"]
        is_ok = kpis["drawdown"]["ok"]
        status_color = "🟢" if is_ok else "🔴"
        
        st.metric(
            label="Current Drawdown",
            value=f"{drawdown:.2f}%",
            delta=f"Goal: <5%",
            delta_color="normal"
        )
        st.markdown(f"{status_color} {'✅ ON TARGET' if is_ok else '⚠️  EXCEEDED'}".center(22))
    
    # System Uptime
    with col4:
        uptime = kpis["uptime"]["percent"]
        is_ok = kpis["uptime"]["ok"]
        status_color = "🟢" if is_ok else "🔴"
        
        st.metric(
            label="System Uptime",
            value=f"{uptime:.1f}%",
            delta=f"Goal: 100%",
            delta_color="normal"
        )
        st.markdown(f"{status_color} {'✅ ON TARGET' if is_ok else '⚠️  DEGRADED'}".center(22))
    
    # ═══════════════════════════════════════════════════════════════════════
    # DETAILED METRICS TABLE
    # ═══════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    st.subheader("📈 Detailed Metrics")
    
    metrics_df = {
        "Metric": [
            "Signal Accuracy",
            "Execution Slippage",
            "Current Drawdown",
            "Max Drawdown",
            "System Uptime"
        ],
        "Actual": [
            f"{kpis['signal_accuracy']['percent']:.2f}%",
            f"{kpis['execution_slippage']['percent']:.4f}%",
            f"{kpis['drawdown']['percent']:.2f}%",
            f"{kpis['drawdown']['maximum']:.2f}%",
            f"{kpis['uptime']['percent']:.2f}%"
        ],
        "Goal": [
            "≥ 40.00%",
            "< 0.15%",
            "< 5.00%",
            "N/A",
            "100.00%"
        ],
        "Status": [
            "✅" if kpis["signal_accuracy"]["ok"] else "⚠️",
            "✅" if kpis["execution_slippage"]["ok"] else "⚠️",
            "✅" if kpis["drawdown"]["ok"] else "⚠️",
            "—",
            "✅" if kpis["uptime"]["ok"] else "⚠️"
        ]
    }
    
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # TRADING ACTIVITY
    # ═══════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    st.subheader("📊 Trading Activity")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Closed Trades", trading["closed_trades"])
    with col2:
        st.metric("Open Trades", trading["open_trades"])
    with col3:
        st.metric("Total Trades", trading["total_trades"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Avg Win (R)", f"+{trading['avg_win_r']:.2f}")
    with col2:
        st.metric("Avg Loss (R)", f"{trading['avg_loss_r']:.2f}")
    with col3:
        st.metric("Best Trade (R)", f"+{trading['best_trade_r']:.2f}")
    with col4:
        st.metric("Worst Trade (R)", f"{trading['worst_trade_r']:.2f}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ALERTS
    # ═══════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    if kpi_data["alerts"]:
        st.subheader("⚠️  Alerts")
        alert_col1, alert_col2 = st.columns([0.1, 0.9])
        with alert_col1:
            st.markdown("🔴")
        with alert_col2:
            for alert in kpi_data["alerts"]:
                st.warning(alert)
    else:
        st.success("✅ All KPIs within targets — No alerts")
    
    # ═══════════════════════════════════════════════════════════════════════
    # OVERALL STATUS
    # ═══════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    if kpi_data["all_kpis_met"]:
        st.markdown(
            "### ✅ Status: ON TRACK\nAll first-month KPI goals are being met.",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "### 🔴 Status: NEEDS ATTENTION\nSome KPI goals are not being met. Review alerts above.",
            unsafe_allow_html=True
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # DOWNLOAD REPORT
    # ═══════════════════════════════════════════════════════════════════════
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        report_json = json.dumps(kpi_data, indent=2)
        st.download_button(
            label="📥 Download KPI Report (JSON)",
            data=report_json,
            file_name=f"kpi_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Display last update time
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    st.set_page_config(page_title="First-Month KPI Monitoring", layout="wide")
    show_first_month_kpi_dashboard()
