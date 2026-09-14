# enterprise_ai_platform.cli

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

- `enterprise_ai_platform.core`
- `enterprise_ai_platform.monitoring`
- `enterprise_ai_platform.security`
- `enterprise_ai_platform.infrastructure`

## Planned Submodules

- `enterprise_ai_platform.cli.telegram_bot`
- `enterprise_ai_platform.cli.command_handler`
- `enterprise_ai_platform.cli.status_command`
- `enterprise_ai_platform.cli.health_command`
- `enterprise_ai_platform.cli.pnl_command`
- `enterprise_ai_platform.cli.perf_command`
- `enterprise_ai_platform.cli.safe_command`
- `enterprise_ai_platform.cli.resume_command`

## Future Roadmap
See [`future_work.md`](future_work.md).

---
_IIOS-FCR-001 Foundation Certified_
