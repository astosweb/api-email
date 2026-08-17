"""Hostname configuration."""

from __future__ import annotations

from setup.utils import SetupContext, log_success, mark_step, run_cmd, step_completed


def configure_hostname(ctx: SetupContext) -> None:
    if step_completed('hostname'):
        log_success(f'Hostname already set to {ctx.smtp_hostname}', ctx)
        return

    run_cmd(['hostnamectl', 'set-hostname', ctx.smtp_hostname], ctx, check=False)
    mark_step('hostname', ctx)
    log_success(f'Hostname set to {ctx.smtp_hostname}', ctx)
