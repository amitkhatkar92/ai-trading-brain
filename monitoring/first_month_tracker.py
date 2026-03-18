"""
First-Month KPI Monitoring System
==================================
Tracks 4 critical metrics against first-month goals:
  • Signal Accuracy:    ≥ 40% win rate
  • Execution Slippage: < 0.15% per trade
  • Drawdown:          < 5% of capital
  • System Uptime:     100% (no crashes)

Usage:
    tracker = FirstMonthTracker(initial_capital=1_000_000)
    tracker.update()  # Refresh data from files
    report = tracker.get_daily_report()
    print(report)
"""

import json
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import csv


class FirstMonthTracker:
    """Tracks first-month KPIs against monitoring goals."""
    
    GOAL_WIN_RATE = 0.40           # ≥ 40%
    GOAL_SLIPPAGE = 0.0015         # < 0.15%
    GOAL_DRAWDOWN = 0.05           # < 5% of capital
    GOAL_UPTIME = 1.00             # 100%
    
    def __init__(self, initial_capital: float = 1_000_000, root_dir: str = None):
        """
        Args:
            initial_capital: Starting capital (used for drawdown calculation)
            root_dir: Root project directory (auto-detected if None)
        """
        if root_dir is None:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        self.root_dir = root_dir
        self.initial_capital = initial_capital
        self.data_dir = os.path.join(root_dir, "data")
        self.trades_csv = os.path.join(self.data_dir, "paper_trades.csv")
        self.perf_json = os.path.join(self.data_dir, "strategy_performance.json")
        self.monitor_json = os.path.join(self.data_dir, "first_month_monitoring.json")
        
        # KPI state
        self.trades_closed = []  # Closed trades with P&L
        self.trades_open = []    # Open trades
        self.uptime_events = []  # System start/stop events
        self.last_update = None
        
        # Persist tracking data
        self._load_monitoring_state()
    
    def _load_monitoring_state(self) -> None:
        """Load persisted monitoring state if it exists."""
        if os.path.exists(self.monitor_json):
            try:
                with open(self.monitor_json, 'r') as f:
                    state = json.load(f)
                    self.uptime_events = state.get("uptime_events", [])
                    self.last_update = state.get("last_update")
            except Exception as e:
                print(f"Warning: Could not load monitoring state: {e}")
                self.uptime_events = []
    
    def _save_monitoring_state(self) -> None:
        """Persist monitoring state to JSON."""
        state = {
            "uptime_events": self.uptime_events,
            "last_update": datetime.now().isoformat(),
            "initial_capital": self.initial_capital
        }
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.monitor_json, 'w') as f:
            json.dump(state, f, indent=2)
    
    def update(self) -> None:
        """Refresh KPI data from trading logs."""
        self._load_trades()
        self._record_system_startup()
        self._save_monitoring_state()
        self.last_update = datetime.now()
    
    def _load_trades(self) -> None:
        """Parse paper_trades.csv and categorize closed vs open trades."""
        if not os.path.exists(self.trades_csv):
            self.trades_closed = []
            self.trades_open = []
            return
        
        closed = []
        open_trades = []
        seen_ids = set()
        
        try:
            with open(self.trades_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    order_id = row.get('order_id', '')
                    event = row.get('event', '').upper()
                    
                    # Skip duplicate processing
                    if order_id in seen_ids:
                        continue
                    seen_ids.add(order_id)
                    
                    # Parse trade row
                    try:
                        entry_price = float(row.get('entry_price', 0))
                        target = float(row.get('target', 0))
                        stop_loss = float(row.get('stop_loss', 0))
                        rr = float(row.get('rr', 0))
                        timestamp = row.get('timestamp', '')
                        direction = row.get('direction', 'BUY')
                        
                        trade_dict = {
                            'order_id': order_id,
                            'symbol': row.get('symbol', ''),
                            'direction': direction,
                            'quantity': int(row.get('quantity', 0)),
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'target': target,
                            'strategy': row.get('strategy', ''),
                            'confidence': float(row.get('confidence', 0)),
                            'rr': rr,
                            'timestamp': timestamp,
                            'event': event,
                        }
                        
                        if event in ('CLOSED', 'TARGET_HIT', 'STOPPED_OUT'):
                            # Trade closed - calculate P&L
                            if event == 'TARGET_HIT':
                                exit_price = target
                            elif event == 'STOPPED_OUT':
                                exit_price = stop_loss
                            else:
                                # Try to parse exit price from row
                                exit_price = float(row.get('exit_price', entry_price))
                            
                            trade_dict['exit_price'] = exit_price
                            trade_dict['pnl_r'] = rr if event == 'TARGET_HIT' else -rr
                            trade_dict['pnl_percent'] = self._calculate_pnl_percent(
                                entry_price, exit_price, direction
                            )
                            closed.append(trade_dict)
                        else:
                            # Trade still open
                            open_trades.append(trade_dict)
                    except (ValueError, KeyError) as e:
                        print(f"Warning: Could not parse trade row: {e}")
                        continue
        
        except Exception as e:
            print(f"Error reading trades CSV: {e}")
        
        self.trades_closed = closed
        self.trades_open = open_trades
    
    def _calculate_pnl_percent(self, entry: float, exit_p: float, direction: str) -> float:
        """Calculate P&L percentage for a trade."""
        if entry == 0:
            return 0.0
        if direction == 'BUY':
            return ((exit_p - entry) / entry) * 100
        else:  # SELL
            return ((entry - exit_p) / entry) * 100
    
    def _record_system_startup(self) -> None:
        """Record a system startup event (called on each update)."""
        if self.trades_closed or self.trades_open:
            # Only record if there's trading activity
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "startup",
                "total_trades": len(self.trades_closed) + len(self.trades_open)
            }
            # Avoid duplicate consecutive events
            if not self.uptime_events or self.uptime_events[-1]['type'] != 'startup':
                self.uptime_events.append(event)
    
    # ═════════════════════════════════════════════════════════════════════
    # KPI CALCULATIONS
    # ═════════════════════════════════════════════════════════════════════
    
    def get_signal_accuracy(self) -> float:
        """Calculate win rate (closed trades only)."""
        if not self.trades_closed:
            return 0.0
        wins = len([t for t in self.trades_closed if t.get('pnl_percent', 0) > 0])
        return wins / len(self.trades_closed)
    
    def get_execution_slippage(self) -> float:
        """
        Calculate average execution slippage.
        Slippage = abs(actual_execution_price - ideal_target_or_sl) / entry_price
        For now, simplified as average distance from target/SL relative to entry.
        """
        if not self.trades_closed:
            return 0.0
        
        total_slippage_pct = 0.0
        for trade in self.trades_closed:
            entry = trade.get('entry_price', 0)
            target = trade.get('target', 0)
            sl = trade.get('stop_loss', 0)
            
            if entry == 0:
                continue
            
            # Distance from entry to target/SL
            target_dist = abs(target - entry) / entry if target else 0
            sl_dist = abs(sl - entry) / entry if sl else 0
            
            # Average as a measure of expected vs actual
            expected_range = (target_dist + sl_dist) / 2 if (target_dist + sl_dist) > 0 else 0
            total_slippage_pct += expected_range
        
        avg_slippage = total_slippage_pct / len(self.trades_closed)
        return avg_slippage
    
    def get_drawdown(self) -> Tuple[float, float]:
        """
        Calculate current drawdown and max drawdown.
        Returns: (current_drawdown%, max_drawdown%)
        """
        if not self.trades_closed:
            return 0.0, 0.0
        
        # Calculate cumulative P&L
        cumulative_pnl = sum(t.get('pnl_r', 0) for t in self.trades_closed)
        peak_pnl = 0
        max_dd_percent = 0
        
        for i, trade in enumerate(self.trades_closed):
            cumsum = sum(t.get('pnl_r', 0) for t in self.trades_closed[:i+1])
            if cumsum > peak_pnl:
                peak_pnl = cumsum
            
            drawdown_r = peak_pnl - cumsum
            dd_percent = (drawdown_r / self.initial_capital) * 100
            if dd_percent > max_dd_percent:
                max_dd_percent = dd_percent
        
        current_dd_percent = ((peak_pnl - cumulative_pnl) / self.initial_capital) * 100
        return current_dd_percent, max_dd_percent
    
    def get_system_uptime(self) -> float:
        """
        Calculate system uptime percentage.
        Based on startup/crash events (simplified: assume 1 = 100% if no crashes).
        """
        if not self.uptime_events:
            return 0.0  # No data yet
        
        # For simplicity: count crashes (unexpected shutdowns)
        crashes = len([e for e in self.uptime_events if e.get('type') == 'crash'])
        uptime_pct = 1.0 - (crashes * 0.1)  # Each crash = -10% (simplified)
        return max(0.0, min(1.0, uptime_pct))
    
    # ═════════════════════════════════════════════════════════════════════
    # REPORTING
    # ═════════════════════════════════════════════════════════════════════
    
    def get_kpi_status(self) -> Dict[str, bool]:
        """Check if each KPI meets its goal."""
        win_rate = self.get_signal_accuracy()
        slippage = self.get_execution_slippage()
        current_dd, _ = self.get_drawdown()
        uptime = self.get_system_uptime()
        
        return {
            "signal_accuracy_ok": win_rate >= self.GOAL_WIN_RATE,
            "slippage_ok": slippage < self.GOAL_SLIPPAGE,
            "drawdown_ok": current_dd < (self.GOAL_DRAWDOWN * 100),
            "uptime_ok": uptime >= self.GOAL_UPTIME,
        }
    
    def get_daily_report(self) -> str:
        """Generate a formatted daily report."""
        self.update()
        
        win_rate = self.get_signal_accuracy()
        slippage = self.get_execution_slippage()
        current_dd, max_dd = self.get_drawdown()
        uptime = self.get_system_uptime()
        
        status = self.get_kpi_status()
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FIRST-MONTH KPI MONITORING REPORT                         ║
║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  METRIC                           ACTUAL         GOAL           STATUS        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Signal Accuracy (Win Rate)       {win_rate*100:6.2f}%        ≥ 40.00%       {self._status_icon(status['signal_accuracy_ok'])}    ║
║  Execution Slippage               {slippage*100:6.4f}%        < 0.15%        {self._status_icon(status['slippage_ok'])}    ║
║  Current Drawdown                 {current_dd:6.2f}%         < 5.00%        {self._status_icon(status['drawdown_ok'])}    ║
║  Maximum Drawdown (this month)    {max_dd:6.2f}%                            ║
║  System Uptime                    {uptime*100:6.2f}%        100.00%        {self._status_icon(status['uptime_ok'])}    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TRADES SUMMARY                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Closed Trades:                   {len(self.trades_closed):6d}                                     ║
║  Open Trades:                     {len(self.trades_open):6d}                                     ║
║  Total Trades:                    {len(self.trades_closed) + len(self.trades_open):6d}                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        return report
    
    def get_weekly_report(self) -> str:
        """Generate a formatted weekly report with trend analysis."""
        self.update()
        
        win_rate = self.get_signal_accuracy()
        slippage = self.get_execution_slippage()
        current_dd, max_dd = self.get_drawdown()
        uptime = self.get_system_uptime()
        
        status = self.get_kpi_status()
        
        # Calculate win/loss streaks
        recent_trades = self.trades_closed[-20:] if len(self.trades_closed) > 0 else []
        recent_wins = sum(1 for t in recent_trades if t.get('pnl_percent', 0) > 0)
        recent_win_rate = (recent_wins / len(recent_trades)) if recent_trades else 0.0
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              WEEKLY KPI MONITORING REPORT (ALL-TIME + RECENT)                ║
║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  METRIC                       ALL-TIME    RECENT(20)  GOAL          STATUS    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Signal Accuracy              {win_rate*100:7.2f}%    {recent_win_rate*100:7.2f}%    ≥ 40.00%     {self._status_icon(status['signal_accuracy_ok'])}  ║
║  Execution Slippage           {slippage*100:7.4f}%    —         < 0.15%     {self._status_icon(status['slippage_ok'])}  ║
║  Current Drawdown             {current_dd:7.2f}%    —         < 5.00%     {self._status_icon(status['drawdown_ok'])}  ║
║  Max Drawdown (Month)         {max_dd:7.2f}%    —                        ║
║  System Uptime                {uptime*100:7.2f}%    —        100.00%     {self._status_icon(status['uptime_ok'])}  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TRADING ACTIVITY                                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Total Closed Trades:           {len(self.trades_closed):6d}                                     ║
║  Total Open Trades:             {len(self.trades_open):6d}                                     ║
║  Average Win Amount (R):        {self._avg_win_r():7.2f}R                                      ║
║  Average Loss Amount (R):       {self._avg_loss_r():7.2f}R                                      ║
║  Best Trade:                    +{self._best_trade_r():7.2f}R                                      ║
║  Worst Trade:                   {self._worst_trade_r():7.2f}R                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        return report
    
    def _status_icon(self, is_ok: bool) -> str:
        """Return ✅ or ⚠️  based on status."""
        return "✅" if is_ok else "⚠️"
    
    def _avg_win_r(self) -> float:
        """Average R for winning trades."""
        wins = [t.get('pnl_r', 0) for t in self.trades_closed if t.get('pnl_r', 0) > 0]
        return sum(wins) / len(wins) if wins else 0.0
    
    def _avg_loss_r(self) -> float:
        """Average R for losing trades."""
        losses = [t.get('pnl_r', 0) for t in self.trades_closed if t.get('pnl_r', 0) < 0]
        return sum(losses) / len(losses) if losses else 0.0
    
    def _best_trade_r(self) -> float:
        """Best trade in R."""
        if self.trades_closed:
            return max(t.get('pnl_r', 0) for t in self.trades_closed)
        return 0.0
    
    def _worst_trade_r(self) -> float:
        """Worst trade in R."""
        if self.trades_closed:
            return min(t.get('pnl_r', 0) for t in self.trades_closed)
        return 0.0
    
    def export_json(self) -> Dict:
        """Export KPI data as JSON for programmatic access."""
        self.update()
        
        win_rate = self.get_signal_accuracy()
        slippage = self.get_execution_slippage()
        current_dd, max_dd = self.get_drawdown()
        uptime = self.get_system_uptime()
        status = self.get_kpi_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "kpis": {
                "signal_accuracy": {
                    "actual": win_rate,
                    "goal": self.GOAL_WIN_RATE,
                    "ok": status['signal_accuracy_ok'],
                    "percent": round(win_rate * 100, 2)
                },
                "execution_slippage": {
                    "actual": slippage,
                    "goal": self.GOAL_SLIPPAGE,
                    "ok": status['slippage_ok'],
                    "percent": round(slippage * 100, 4)
                },
                "drawdown": {
                    "current": current_dd,
                    "maximum": max_dd,
                    "goal": self.GOAL_DRAWDOWN * 100,
                    "ok": status['drawdown_ok'],
                    "percent": round(current_dd, 2)
                },
                "uptime": {
                    "actual": uptime,
                    "goal": self.GOAL_UPTIME,
                    "ok": status['uptime_ok'],
                    "percent": round(uptime * 100, 2)
                }
            },
            "trading": {
                "closed_trades": len(self.trades_closed),
                "open_trades": len(self.trades_open),
                "total_trades": len(self.trades_closed) + len(self.trades_open),
                "avg_win_r": round(self._avg_win_r(), 2),
                "avg_loss_r": round(self._avg_loss_r(), 2),
                "best_trade_r": round(self._best_trade_r(), 2),
                "worst_trade_r": round(self._worst_trade_r(), 2)
            },
            "all_kpis_met": all(status.values())
        }


if __name__ == "__main__":
    # Quick test
    tracker = FirstMonthTracker(initial_capital=1_000_000)
    tracker.update()
    
    print(tracker.get_daily_report())
    print("\n")
    print(tracker.get_weekly_report())
    
    # Export JSON
    import sys
    json_data = tracker.export_json()
    print("\nJSON Export:")
    print(json.dumps(json_data, indent=2))
