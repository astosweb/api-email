"""TLS certificate management."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from setup.utils import SetupContext, log_success, log_warn, mark_step, run_cmd, step_completed


def configure_smtp_tls(ctx: SetupContext) -> None:
    cert_path = Path(f'/etc/letsencrypt/live/{ctx.smtp_hostname}/fullchain.pem')
    if cert_path.exists():
        log_success('TLS certificate already exists', ctx)
        return

    if step_completed('tls'):
        log_success('TLS configuration recorded', ctx)
        return

    log_warn(
        f'Let\'s Encrypt cert for {ctx.smtp_hostname} not yet issued — '
        'will be obtained after DNS is configured',
        ctx,
    )
    mark_step('tls', ctx)


def obtain_certificates(ctx: SetupContext) -> None:
    """Obtain Let's Encrypt certificates for API, web, and SMTP domains."""
    domains = [ctx.api_domain, ctx.web_domain]
    for domain in domains:
        cert = Path(f'/etc/letsencrypt/live/{domain}/fullchain.pem')
        if cert.exists():
            log_success(f'Certificate exists for {domain}', ctx)
            continue
        run_cmd([
            'certbot', 'certonly', '--nginx', '--non-interactive',
            '--agree-tos', '-m', ctx.admin_email,
            '-d', domain,
        ], ctx, check=False)

    mark_step('tls', ctx)


def verify_certificate(domain: str) -> dict:
    cert_path = Path(f'/etc/letsencrypt/live/{domain}/fullchain.pem')
    if not cert_path.exists():
        return {'valid': False, 'reason': 'certificate not found'}
    try:
        result = run_cmd(
            ['openssl', 'x509', '-in', str(cert_path), '-noout', '-enddate'],
            SetupContext(dry_run=False),
            capture=True,
            check=False,
        )
        return {'valid': result.returncode == 0, 'enddate': result.stdout.strip()}
    except Exception as e:
        return {'valid': False, 'reason': str(e)}
