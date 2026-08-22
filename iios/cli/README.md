# iios.cli

> **Status:** PLACEHOLDER -- Foundation certified. Wave 4 pending.

## Purpose
CLI and Telegram bot -- all 13 IIOS operator commands: /health /pnl /perf /safe /resume /status /learn /diag /mode /strategies /positions /signals /help

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | CLI |
| Wave | 4 |
| Owner | Platform |
| Architecture Reference | IIOS-ARC-001 13 Telegram commands |
| Foundation | IIOS-FCR-001 |

## Responsibilities
Defined in **IIOS-ARC-001 13 Telegram commands**.

## Dependencies

- `iios.core`
- `iios.monitoring`
- `iios.security`
- `iios.infrastructure`

## Planned Submodules

- `iios.cli.telegram_bot`
- `iios.cli.command_handler`
- `iios.cli.status_command`
- `iios.cli.health_command`
- `iios.cli.pnl_command`
- `iios.cli.perf_command`
- `iios.cli.safe_command`
- `iios.cli.resume_command`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
