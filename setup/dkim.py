"""DKIM key generation and OpenDKIM configuration."""

from __future__ import annotations

import os
from pathlib import Path

from setup.utils import (
    SetupContext,
    INSTALL_DIR,
    REPO_ROOT,
    log_success,
    mark_step,
    run_cmd,
    step_completed,
)

DKIM_SELECTOR = 'apiemail'
KEYS_DIR = Path('/etc/opendkim/keys')
INFRA_DKIM = REPO_ROOT / 'infrastructure' / 'opendkim'


def configure_dkim(ctx: SetupContext) -> None:
    private_key = KEYS_DIR / ctx.domain / f'{DKIM_SELECTOR}.private'
    if step_completed('dkim') and private_key.exists():
        log_success('DKIM already configured', ctx)
        _ensure_opendkim_running(ctx)
        return

    if not ctx.dry_run:
        (KEYS_DIR / ctx.domain).mkdir(parents=True, exist_ok=True, mode=0o750)

    if not private_key.exists():
        run_cmd([
            'opendkim-genkey',
            '-b', '2048',
            '-d', ctx.domain,
            '-s', DKIM_SELECTOR,
            '-D', str(KEYS_DIR / ctx.domain),
        ], ctx)
        pub_key = KEYS_DIR / ctx.domain / f'{DKIM_SELECTOR}.txt'
        if pub_key.exists() and not ctx.dry_run:
            os.chmod(private_key, 0o600)
            os.chmod(KEYS_DIR / ctx.domain, 0o750)

    template = INFRA_DKIM / 'opendkim.conf.template'
    content = template.read_text()
    content = content.replace('{{DKIM_PRIVATE_KEY}}', str(private_key))
    content = content.replace('{{DKIM_SELECTOR}}', DKIM_SELECTOR)
    content = content.replace('{{DOMAIN}}', ctx.domain)

    if not ctx.dry_run:
        Path('/etc/opendkim.conf').write_text(content)
        tables_dir = Path('/etc/opendkim/KeyTable')
        signing_table = Path('/etc/opendkim/SigningTable')
        tables_dir.write_text(f'{DKIM_SELECTOR}._domainkey.{ctx.domain} {ctx.domain}:{DKIM_SELECTOR}:{private_key}\n')
        signing_table.write_text(f'*@{ctx.domain} {DKIM_SELECTOR}._domainkey.{ctx.domain}\n')
        Path('/etc/opendkim/TrustedHosts').write_text('127.0.0.1\nlocalhost\n')

    _ensure_opendkim_running(ctx)
    mark_step('dkim', ctx)
    log_success('DKIM configured', ctx)


def _ensure_opendkim_running(ctx: SetupContext) -> None:
    run_cmd(['systemctl', 'enable', 'opendkim'], ctx, check=False)
    run_cmd(['systemctl', 'restart', 'opendkim'], ctx, check=False)


def get_dkim_dns_record(ctx: SetupContext) -> dict[str, str] | None:
    txt_file = KEYS_DIR / ctx.domain / f'{DKIM_SELECTOR}.txt'
    if not txt_file.exists():
        return None
    raw = txt_file.read_text()
    # Parse p= value from DNS record file
    import re
    match = re.search(r'p=([A-Za-z0-9+/=]+)', raw.replace('\n', '').replace('"', ''))
    if not match:
        return None
    return {
        'name': f'{DKIM_SELECTOR}._domainkey.{ctx.domain}',
        'value': f'v=DKIM1; k=rsa; p={match.group(1)}',
    }
