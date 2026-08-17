"""UFW firewall configuration."""

from __future__ import annotations

from setup.utils import SetupContext, log_success, mark_step, run_cmd, step_completed


def configure_firewall(ctx: SetupContext) -> None:
    if step_completed('firewall'):
        log_success('Firewall already configured', ctx)
        return

    ssh_port = ctx.ssh_port
    run_cmd(['ufw', '--force', 'reset'], ctx, check=False)
    run_cmd(['ufw', 'default', 'deny', 'incoming'], ctx)
    run_cmd(['ufw', 'default', 'allow', 'outgoing'], ctx)
    run_cmd(['ufw', 'allow', f'{ssh_port}/tcp', 'comment', 'SSH'], ctx)
    run_cmd(['ufw', 'allow', '80/tcp', 'comment', 'HTTP'], ctx)
    run_cmd(['ufw', 'allow', '443/tcp', 'comment', 'HTTPS'], ctx)
    run_cmd(['ufw', 'allow', '25/tcp', 'comment', 'SMTP'], ctx)
    run_cmd(['ufw', 'allow', '587/tcp', 'comment', 'Submission'], ctx)
    run_cmd(['ufw', '--force', 'enable'], ctx)
    mark_step('firewall', ctx)
    log_success(f'Firewall configured (SSH port {ssh_port} preserved)', ctx)
