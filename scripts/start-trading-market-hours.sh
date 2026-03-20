#!/bin/bash
# Start trading engine 10 minutes before market open
# Time: 08:50 IST (03:20 UTC) on weekdays

systemctl start trading-brain-schedule
systemctl status trading-brain-schedule

echo "[$(date)] Trading engine started for market hours" >> /var/log/trading-brain-cron.log
