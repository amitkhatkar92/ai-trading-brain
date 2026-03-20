#!/bin/bash
# Stop trading engine 5 minutes after market close
# Time: 15:40 IST (10:10 UTC) on weekdays

systemctl stop trading-brain-schedule
systemctl status trading-brain-schedule

echo "[$(date)] Trading engine stopped after market hours" >> /var/log/trading-brain-cron.log
