"""Optional monitoring setup."""

from __future__ import annotations

from pathlib import Path

from setup.utils import SetupContext, log_success, log_warn, mark_step, run_cmd, step_completed


def configure_monitoring(ctx: SetupContext) -> None:
    if not ctx.install_monitoring:
        log_warn('Monitoring skipped by configuration', ctx)
        return

    if step_completed('monitoring'):
        log_success('Monitoring already configured', ctx)
        return

    script = Path('/opt/api-email/scripts/monitor.sh')
    content = """#!/usr/bin/env bash
set -euo pipefail
DISK=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
MEM=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
QUEUE=$(postqueue -p 2>/dev/null | tail -1 | grep -oP '\\d+(?= Request)' || echo 0)
echo "disk_usage=${DISK}% memory_usage=${MEM}% postfix_queue=${QUEUE}"
[ "$DISK" -lt 90 ] || echo "WARNING: disk usage above 90%"
[ "$QUEUE" -lt 100 ] || echo "WARNING: postfix queue depth above 100"
"""
    if not ctx.dry_run:
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(content)
        script.chmod(0o755)

    cron_line = '*/5 * * * * root /opt/api-email/scripts/monitor.sh >> /var/log/api-email-monitor.log 2>&1'
    cron_file = Path('/etc/cron.d/api-email-monitor')
    if not ctx.dry_run:
        cron_file.write_text(cron_line + '\n')

    mark_step('monitoring', ctx)
    log_success('Monitoring configured', ctx)
