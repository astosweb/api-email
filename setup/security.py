"""Security hardening: SSH and Fail2Ban."""

from __future__ import annotations

from pathlib import Path

from setup.utils import SetupContext, log_success, log_warn, mark_step, run_cmd, step_completed


def configure_fail2ban(ctx: SetupContext) -> None:
    if step_completed('fail2ban'):
        log_success('Fail2Ban already configured', ctx)
        return

    jail_local = Path('/etc/fail2ban/jail.local')
    content = """[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[postfix]
enabled = true
filter = postfix
port = smtp,ssubmission
logpath = /var/log/mail.log
maxretry = 5
"""
    if not ctx.dry_run:
        jail_local.write_text(content)
    run_cmd(['systemctl', 'enable', 'fail2ban'], ctx, check=False)
    run_cmd(['systemctl', 'restart', 'fail2ban'], ctx, check=False)
    mark_step('fail2ban', ctx)
    log_success('Fail2Ban configured', ctx)


def harden_ssh(ctx: SetupContext) -> None:
    """Harden SSH without locking out key-based access."""
    sshd_config = Path('/etc/ssh/sshd_config')
    if not sshd_config.exists():
        log_warn('sshd_config not found, skipping SSH hardening', ctx)
        return

    if step_completed('ssh_harden'):
        log_success('SSH already hardened', ctx)
        return

    has_authorized_keys = _has_authorized_keys()
    if not has_authorized_keys:
        log_warn(
            'No authorized_keys found — skipping password auth disable to prevent lockout',
            ctx,
        )
        _apply_ssh_setting('PermitRootLogin', 'prohibit-password')
    else:
        _apply_ssh_setting('PermitRootLogin', 'prohibit-password')
        _apply_ssh_setting('PasswordAuthentication', 'no')
        _apply_ssh_setting('PubkeyAuthentication', 'yes')

    _apply_ssh_setting('MaxAuthTries', '3')
    _apply_ssh_setting('X11Forwarding', 'no')
    _apply_ssh_setting('AllowAgentForwarding', 'no')

    run_cmd(['systemctl', 'reload', 'sshd'], ctx, check=False)
    mark_step('ssh_harden', ctx)
    log_success('SSH hardened (key-based access preserved)', ctx)


def _has_authorized_keys() -> bool:
    for path in (
        Path('/root/.ssh/authorized_keys'),
        Path('/home/ubuntu/.ssh/authorized_keys'),
    ):
        if path.exists() and path.stat().st_size > 0:
            return True
    return False


def _apply_ssh_setting(key: str, value: str) -> None:
    path = Path('/etc/ssh/sshd_config')
    lines = path.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f'{key} '):
            new_lines.append(f'{key} {value}')
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f'{key} {value}')
    path.write_text('\n'.join(new_lines) + '\n')


def configure_security(ctx: SetupContext) -> None:
    configure_fail2ban(ctx)
    harden_ssh(ctx)
