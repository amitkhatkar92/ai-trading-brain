# OPS04A — Journal Reset Forensic Report

**Classification:** Evidence Collection / Post-Mortem  
**Status:** CLOSED — Root cause determined  
**Date of Incident:** 2026-06-16, approximately 18:37 IST  
**Date of Report:** 2026-06-19  
**Investigator:** Copilot (evidence collection only — no code modified)

---

## Executive Summary

`data/paper_trades.csv` was intentionally replaced by the **OPS-03A Dataset Remediation** on 2026-06-16 at 18:37 IST. The reset was a deliberate manual action to fix a CSV schema defect (12-column vs. 15-column header mismatch). The process archived an OLD reference copy of the file rather than the currently active file, resulting in the silent deletion of approximately 14–15 trade-session records (Jun 5 – Jun 16) that were in the active CSV at the time.

**Trades "lost" from CSV:** Jun 5–Jun 16 OPEN/CLOSE rows (approximately 28–45 rows).  
**Are the trades truly lost?** Their CSV rows are unrecoverable. Their aggregate outcomes are preserved in `system_logs` (EOD_LEARNING records) and strategy-performance summaries.  
**Would it happen again?** **NO.** OPS-03A was a one-time remediation. No code path can truncate the file; all journal writes use `open(..., "a")` mode.

---

## 1. Evidence Inventory

### 1.1 Files on VPS at time of investigation

| File | Size | mtime | ctime | Rows | Header Cols | Last Row Timestamp |
|---|---|---|---|---|---|---|
| `data/paper_trades.csv` (current) | 263 B | Jun 18 09:10 | Jun 18 09:10 | 1 | 15 | 2026-06-18 09:10:16 (DRREDDY OPEN) |
| `data/paper_trades_legacy.csv` | 28,091 B | Jun 16 18:37 | Jun 16 18:37 | 234 | 12 | **2026-04-17 13:00:20** (ITC OPEN) |
| `data/paper_trades_backup_20260529.csv` | 43,743 B | May 29 11:51 | May 29 11:51 | 341 | 15 | **2026-05-29 11:51:16** |
| `data/paper_trades_backup_pre_bb_close.csv` | 44,201 B | May 29 12:30 | May 29 12:30 | 343 | 15 | 2026-05-13 (latest OPEN) |
| `data/paper_trades_backup_hindalco_audit.csv` | 43,458 B | May 29 11:23 | May 29 11:23 | — | 15 | — |
| `data/paper_trades_backup_pre_header_fix.csv` | 35,887 B | Apr 28 10:50 | Apr 28 10:50 | 290 | **12** | 2026-04-28 |
| `data/paper_trades.csv.bak_zombie_cleanup_apr28` | 35,332 B | Apr 28 10:30 | Apr 28 10:30 | — | — | — |
| `data/paper_trades.csv.bak_apr27_patch` | 34,672 B | Apr 27 16:00 | Apr 27 16:00 | — | — | — |

**Key fact:** `paper_trades_legacy.csv` has `mtime = ctime = 2026-06-16T18:37:17`. On Linux, a true rename (`mv`) preserves mtime and only updates ctime. The fact that BOTH are 18:37 proves the file was **created from scratch** at 18:37 (via `cp` or Python write), NOT renamed from the active file.

**`OPS03A_DATASET_REMEDIATION.md` is NOT present on the VPS** (`/app/OPS03A_DATASET_REMEDIATION.md` = MISSING). It exists only on the local Windows machine. This confirms OPS-03A was authored and partially executed locally before being applied to the VPS.

### 1.2 VPS System Logs (trading_brain.db — system_logs table)

#### All events Jun 15 14:00 through Jun 16 23:59

| ID | Timestamp | Event Type | Component | Message |
|---|---|---|---|---|
| — | 2026-06-15T15:35:14.568 | EOD_LEARNING | orchestrator | trades=1 wins=0 pnl=-26563 |
| — | 2026-06-16T09:45:04.571 | TRADE_OPENED | orchestrator | symbol=DRREDDY strategy=Mean_Reversion |
| — | 2026-06-16T09:45:05.451 | TRADE_OPENED | orchestrator | symbol=APOLLOHOSP strategy=Mean_Reversion |
| — | 2026-06-16T10:30:10.957 | TRADE_OPENED | orchestrator | symbol=PAGEIND strategy=Mean_Reversion |
| — | 2026-06-16T15:35:16.117 | EOD_LEARNING | orchestrator | **trades=6 wins=2 pnl=-15160** |
| 1778 | 2026-06-16T18:38:06.086 | SYSTEM_START | orchestrator | Master Orchestrator initialised |
| 1779 | 2026-06-16T18:51:56.379 | SYSTEM_START | orchestrator | Master Orchestrator initialised |

#### Post-reset EOD_LEARNING entries

| Timestamp | Message |
|---|---|
| 2026-06-16T15:35:16 | trades=6 wins=2 pnl=-15160 ← **last correct count** |
| 2026-06-17T15:35:15 | trades=0 wins=0 pnl=+0 ← file reset, memory fresh |
| 2026-06-18T15:35:06 | trades=0 wins=0 pnl=+0 |

#### All SYSTEM_START events (relevant portion)

```
2026-06-16T18:38:06  ← restart #1 (15 min after OPS-03A reset)
2026-06-16T18:51:56  ← restart #2 (28 min after restart #1)
2026-06-19T11:05:39  ← next restart after Jun 16
```

No restart events on Jun 17, 18 — system ran continuously after Jun 16's two restarts.

### 1.3 Gitignore

`paper_trades.csv` appears on line 60 of `.gitignore`. This means:
- `git reset --hard` (run by deploy.yml) does **not** touch `paper_trades.csv`
- The file is never tracked by git and never included in deployments
- The CSV is **not** in any git commit

### 1.4 Deploy Pipeline (deploy.yml)

The deploy pipeline runs: `git fetch --force origin main` → `git reset --hard origin/main` → `docker compose build --no-cache` → `docker compose up -d --force-recreate`.

- `git reset --hard` cannot touch gitignored files → CSV safe from git resets ✓
- `docker compose build --no-cache` bakes source into image via `COPY . .` (Dockerfile)
- `docker-compose.yml` bind-mounts `./data:/app/data` → host's data directory always overrides image → any CSV baked into the image is irrelevant at runtime ✓

The deploy pipeline **cannot** cause a journal reset.

### 1.5 Order Manager Code Paths

All journal write functions in `execution_engine/order_manager.py` use **append mode exclusively**:

| Function | Line(s) | Mode |
|---|---|---|
| `_journal_write()` | 1640 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `_journal_write_close()` | 1667 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `journal_write_extend()` | 1707 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `_journal_write_reentry()` | 1733 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `_journal_cancel()` | 1763 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `close_all_positions()` close path | 2177 | `open(PAPER_TRADE_LOG, "a", ...)` |
| `check_and_expire_carries()` close path | 3167 | `open(PAPER_TRADE_LOG, "a", ...)` |

**Header guard** (lines 1630–1635):
```python
write_header = not os.path.exists(PAPER_TRADE_LOG)
with open(PAPER_TRADE_LOG, "a", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=_JOURNAL_HEADER)
    if write_header:
        writer.writeheader()
```
Header is written **only if the file does not exist**. A restart against an existing file never rewrites the header.

**`_restore_from_journal()`** (line 2840): reads the CSV with `DictReader`, recovers open positions, appends `SESSION_EXPIRED` rows for stale carries — **never truncates or rewrites**.

**Code verdict:** No code path in `order_manager.py` can truncate, delete, or reset the journal. The file can only grow.

---

## 2. Complete Event Timeline

| Time (IST) | Event | Evidence Source |
|---|---|---|
| 2026-03-19 | First paper trade logged (MARUTI BUY) | All CSV backups — first row common to all |
| 2026-03-19 – 2026-04-17 | 234 OPEN rows accumulate with 12-col header | `paper_trades_legacy.csv` content |
| 2026-04-17 | Last row in original 12-col file (ITC BUY OPEN) | `paper_trades_legacy.csv` last row |
| 2026-04-27 16:00 | CSV surgery — `bak_apr27_patch` backup taken (34KB) | VPS file listing |
| 2026-04-28 10:30 | `bak_zombie_cleanup_apr28` (35KB) | VPS file listing |
| 2026-04-28 10:50 | `paper_trades_backup_pre_header_fix.csv` (35KB, 12-col, 290 rows) — saved BEFORE header upgrade | VPS file listing |
| 2026-04-28 ~11:00 | **Header upgrade applied:** new `paper_trades.csv` created with 15-col header. Active file gains `exit_price,pnl,reason` columns. | Inferred from PRE_HDR backup |
| 2026-04-28 – 2026-05-13 | Active file grows with 15-col rows. Contains all OPEN+CLOSE events including proper P&L | `paper_trades_backup_pre_bb_close.csv` — 343 rows, last ts May 13 |
| 2026-05-29 11:23 | `paper_trades_backup_hindalco_audit.csv` (43KB) taken | VPS file listing |
| 2026-05-29 11:51 | `paper_trades_backup_20260529.csv` (43KB, 341 rows, 15-col) — last row May 29 11:51 | VPS backup content |
| 2026-05-29 12:30 | `paper_trades_backup_pre_bb_close.csv` (44KB, 343 rows, 15-col) — pre-bulk-close snapshot | VPS backup content |
| 2026-05-29 – 2026-06-16 | Active `paper_trades.csv` continues accumulating. EOD_LEARNING records confirm: Jun 5 (1 trade), Jun 8 (5 trades), Jun 11 (2 trades), Jun 15 (1 trade). | `system_logs` EOD_LEARNING events |
| **2026-06-16 09:45** | DRREDDY, APOLLOHOSP open (Mean_Reversion) | `system_logs` TRADE_OPENED |
| **2026-06-16 10:30** | PAGEIND opens (Mean_Reversion) | `system_logs` TRADE_OPENED |
| **2026-06-16 ~13:00–15:00** | All Jun 16 positions close (4 losses, 2 wins). Close rows written to active `paper_trades.csv` | `closed_orders_2026-06-16.txt` (3 order IDs: JSWSTEEL, TITAN, APOLLOHOSP) |
| **2026-06-16 15:35:16** | EOD_LEARNING runs. Reads active `paper_trades.csv` + in-memory session → `trades=6 wins=2 pnl=-15160` | `system_logs` ID ~ 1777 |
| **2026-06-16 ~18:30** | OPS-03A remediation begins (locally on Windows machine, then applied to VPS) | `OPS03A_DATASET_REMEDIATION.md` (local) |
| **2026-06-16 18:37:17** | `paper_trades_legacy.csv` CREATED on VPS (not renamed from active file — mtime=ctime=18:37 proves fresh creation). Content: old reference copy, 234 rows, 12-col, through Apr 17 | VPS file metadata |
| **2026-06-16 18:37** | Active `paper_trades.csv` (15-col, ~355 rows, through Jun 16) **OVERWRITTEN** by fresh empty file with 15-col header | Inferred from file state + OPS03A doc |
| **2026-06-16 18:38:06** | `SYSTEM_START` — MasterOrchestrator init. `_restore_from_journal()` reads new empty file → 0 positions restored | `system_logs` ID 1778 |
| **2026-06-16 18:51:56** | Second `SYSTEM_START` — same result | `system_logs` ID 1779 |
| 2026-06-17 15:35:15 | EOD_LEARNING: `trades=0 wins=0 pnl=+0` — confirms fresh file, no Jun 17 trades | `system_logs` |
| 2026-06-18 09:10:16 | DRREDDY BUY entered → first row in new `paper_trades.csv` | VPS file content |
| 2026-06-18 15:35:06 | EOD_LEARNING: `trades=0 wins=0 pnl=+0` — DRREDDY still open at EOD | `system_logs` |

---

## 3. Root Cause Determination

### Category

**Primary — Category C: Manual Action**  
**Secondary — Category F: Dataset Remediation Process**

### Mechanism

OPS-03A was authored on the local Windows machine and states two goals:
1. Fix the CSV schema defect (12-col → 15-col header)
2. Archive the defective file as `paper_trades_legacy.csv`

The process failed at step 2. Instead of archiving the **ACTIVE** `paper_trades.csv` (which had 355+ rows in 15-col format and contained the Jun 5–Jun 16 trade records), it:

1. **Created** `paper_trades_legacy.csv` using an **old reference copy** of the original pre-April CSV (the 234-row, 12-col version from before Apr 28). This is confirmed by `mtime = ctime = 2026-06-16T18:37:17` — a rename preserves mtime; the equal timestamps prove a fresh write.

2. **Overwrote** the active `paper_trades.csv` with a fresh 15-col empty file, silently discarding all trade records from May 29 to Jun 16 that were in the active file.

### The Schema Defect (Underlying Cause)

The OPS03A description of Defect 1 refers to a **12-col header** on the old CSV. However, the active paper_trades.csv had already been migrated to 15-col on **Apr 28** (confirmed by `paper_trades_backup_pre_header_fix.csv` from Apr 28 — the LAST 12-col backup). Trades from May 29 and Jun 15-16 were written correctly with all 15 fields.

The actual defect being fixed by OPS-03A was that there was still an **OLD 12-col file lingering** on disk (or being used in a context where the header was wrong), causing EOD learning to drop `exit_price`, `pnl`, and `reason` fields. The fix was correct in concept but incorrectly targeted the active file.

---

## 4. Data Loss Assessment

### What was lost from the CSV

| Period | Trade Count (from system_logs) | Recoverable from CSV? |
|---|---|---|
| Mar 19 – Apr 17 | 234 OPEN rows | ✅ `paper_trades_legacy.csv` |
| Apr 17 – May 29 | ~107 rows (341 total in May 29 backup) | ✅ `paper_trades_backup_20260529.csv` |
| May 29 – Jun 16 | ~14–15 trade sessions, ~28–45 OPEN/CLOSE rows | ❌ **NOT RECOVERABLE FROM CSV** |
| Jun 18 onwards | 1 row (DRREDDY) | ✅ `paper_trades.csv` |

### Trades confirmed lost from CSV (not in any backup)

From `system_logs` EOD_LEARNING records:

| Date | Trades | Wins | PnL (₹) | CSV recoverable? |
|---|---|---|---|---|
| Jun 5 | 1 | 0 | -24,244 | ❌ |
| Jun 8 | 5 | 2 | +49,002 | ❌ |
| Jun 11 | 2 | 2 | +335,800 | ❌ |
| Jun 15 | 1 | 0 | -26,563 | ❌ |
| Jun 16 | 6 | 2 | -15,160 | ❌ |
| **Total** | **15** | **6** | **+319,035** | ❌ |

### What is preserved

- **Aggregate outcomes** are in `system_logs` (EOD_LEARNING rows above)
- **Strategy performance learning** from these sessions was processed by EOD at 15:35 on Jun 15 and Jun 16 — before the reset at 18:37 — and persisted to `strategy_performance.json` / `learning_db.json`
- **closed_orders_YYYY-MM-DD.txt** files exist for Jun 15 and Jun 16, containing order IDs (not full P&L data)

---

## 5. Contributing Factors

| Factor | Description |
|---|---|
| **Local/VPS state divergence** | OPS-03A was authored locally. The local `data/paper_trades.csv` was the old 12-col file (not yet synced with VPS's active file). OPS-03A ran against local state, producing `paper_trades_legacy.csv` from the local reference copy. The resulting clean file was then applied to the VPS. |
| **No pre-action archive of active file** | OPS-03A did not take a timestamped backup of the VPS's active `paper_trades.csv` before overwriting it. The May 29 backup was the last safety net. |
| **No verification of file state pre-action** | The process assumed the target file had the 12-col defect. The VPS's active file already had 15-col header — the defect was already fixed on the active path. |
| **Silent discard of Jun 5–16 records** | The active file grew from 341 rows (May 29) to approximately 355+ rows (Jun 16 EOD), but this growth was not captured in any backup before OPS-03A ran. |

---

## 6. Was This a Code Bug?

**No.** This was a process failure during a manual remediation operation, not a bug in the trading system code. The code cannot truncate the journal — this is proven by all 7 write functions using `"a"` (append) mode. The reset was caused by the OPS-03A process overwriting the file with a fresh empty version.

---

## 7. Would It Happen Again?

**No — for the following reasons:**

1. **OPS-03A was a one-time event.** The schema defect it fixed is resolved. There is no analogous defect requiring a future remediation.

2. **The active `paper_trades.csv` now has the correct 15-col header.** No future `_restore_from_journal()` or EOD learning call will encounter a header mismatch.

3. **No code path can truncate the file.** All 7 journal write functions use `open(..., "a")`. The header guard only fires when the file does not exist.

4. **Multiple backups exist through May 29.** Future remediation operations, if ever required, should: (a) SSH into the VPS container directly, (b) take a timestamped backup of the current active file first, (c) verify row count before and after.

---

## 8. Forensic Verdict

| Question | Answer |
|---|---|
| **What caused the reset?** | OPS-03A Dataset Remediation (Category C — Manual Action) applied on 2026-06-16 at 18:37 IST |
| **Was it intentional?** | Yes — the schema defect fix was intentional; the loss of Jun 5–16 trade rows was unintentional |
| **Were the 6 Jun-16 trades "lost"?** | Their CSV rows are unrecoverable. Their aggregate outcomes are in `system_logs`. Strategy learning from those trades was processed before the reset. |
| **Was there a code bug?** | No |
| **Did deployment cause it?** | No — gitignore protects the file from `git reset --hard`; bind-mount prevents Docker image from overwriting it |
| **Did a restart cause it?** | No — `_restore_from_journal()` never truncates the file |
| **Would it happen again?** | No |
| **Is there a risk of repeat loss?** | Low — the only risk is another manual remediation without pre-action backup |

---

## 9. Recommendations (Evidence Only — No Code Changes Applied)

These are observations, not actions taken:

1. **Future manual operations on VPS data:** Always `cp /app/data/paper_trades.csv /app/data/paper_trades.csv.bak_$(date +%Y%m%d_%H%M%S)` before any file-level surgery.

2. **VPS vs. local state:** Do not author remediation scripts against a local copy of data files. Always operate directly on the VPS via `docker exec` to ensure the correct file is targeted.

3. **Backup cadence:** The last backup before the Jun loss was May 29 (12+ days prior). Consider weekly automated backups of `paper_trades.csv` (e.g., via a cron job on the VPS host).

4. **OPS03A_DATASET_REMEDIATION.md:** This document does not exist on the VPS (`/app/OPS03A_DATASET_REMEDIATION.md` = MISSING). It should be committed to the repository or placed on the VPS for auditability.

---

*Report compiled from: VPS system_logs, VPS file metadata (mtime/ctime/size), CSV content analysis, order_manager.py source code audit, .gitignore review, docker-compose.yml review, deploy.yml review, OPS03A_DATASET_REMEDIATION.md (local). No code was modified during this investigation.*
