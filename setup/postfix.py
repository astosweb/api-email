"""Postfix configuration."""

from __future__ import annotations

from pathlib import Path

from setup.utils import (
    SetupContext,
    INFRA_DIR,
    INSTALL_DIR,
    REPO_ROOT,
    log_success,
    mark_step,
    run_cmd,
    step_completed,
)

POSTFIX_MAIN = Path('/etc/postfix/main.cf')
INFRA_POSTFIX = REPO_ROOT / 'infrastructure' / 'postfix'


def configure_postfix(ctx: SetupContext) -> None:
    if step_completed('postfix') and POSTFIX_MAIN.exists():
        log_success('Postfix already configured', ctx)
        run_cmd(['systemctl', 'restart', 'postfix'], ctx, check=False)
        return

    template = INFRA_POSTFIX / 'main.cf.template'
    if not template.exists():
        raise RuntimeError(f'Postfix template not found: {template}')

    tls_cert = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
    tls_key = '/etc/ssl/private/ssl-cert-snakeoil.key'
    letsencrypt_cert = Path(f'/etc/letsencrypt/live/{ctx.smtp_hostname}/fullchain.pem')
    if letsencrypt_cert.exists():
        tls_cert = str(letsencrypt_cert)
        tls_key = str(letsencrypt_cert.parent / 'privkey.pem')

    content = template.read_text()
    content = content.replace('{{SMTP_HOSTNAME}}', ctx.smtp_hostname)
    content = content.replace('{{DOMAIN}}', ctx.domain)
    content = content.replace('{{TLS_CERT}}', tls_cert)
    content = content.replace('{{TLS_KEY}}', tls_key)

    infra_dest = INSTALL_DIR / 'infrastructure' / 'postfix'
    if not ctx.dry_run:
        infra_dest.mkdir(parents=True, exist_ok=True)
        (infra_dest / 'main.cf').write_text(content)
        POSTFIX_MAIN.write_text(content)

    run_cmd(['postfix', 'check'], ctx, check=False)
    run_cmd(['systemctl', 'enable', 'postfix'], ctx, check=False)
    run_cmd(['systemctl', 'restart', 'postfix'], ctx, check=False)
    mark_step('postfix', ctx)
    log_success('Postfix configured (no open relay)', ctx)


def verify_no_open_relay(ctx: SetupContext) -> bool:
    """Verify Postfix rejects unauthorized relay."""
    from setup.utils import command_exists
    if not command_exists('postconf'):
        return False
    result = run_cmd(
        ['postconf', '-h', 'smtpd_relay_restrictions'],
        ctx,
        check=False,
        capture=True,
    )
    restrictions = result.stdout.strip()
    return 'reject_unauth_destination' in restrictions
