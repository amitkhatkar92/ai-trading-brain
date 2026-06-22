"""
oios.reporting — OIOS operational reporting package.

Daily EOD reports (after market close):
    data_health       — OHLCV coverage, event ingestion, graph health
    oios_activity     — state distribution, transitions, score summaries
    phase_d_shadow    — RE snapshots, velocity, pending proposals
    phase_e_shadow    — cause scores, propagation, shadow OS delta
    readiness_gates   — D-Ready / E-Ready gate status

Weekly report (every Saturday):
    weekly_report     — opportunity statistics, archetype frequencies,
                        invalidation breakdown, sector conviction,
                        Phase D/E performance, pipeline health

All report generators are read-only (SELECT only).
Phase D and Phase E remain SHADOW MODE.
"""
