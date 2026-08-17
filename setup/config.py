"""Configuration loading and validation."""

from __future__ import annotations

import os
import socket
import urllib.request
from pathlib import Path

from setup.utils import SetupContext, log_warn, generate_secret


def load_config_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def detect_public_ip() -> str:
    for url in (
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://checkip.amazonaws.com',
    ):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.read().decode().strip()
        except Exception:
            continue
    return ''


def detect_ssh_port() -> int:
    try:
        with open('/etc/ssh/sshd_config') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Port ') and not line.startswith('#'):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 22


def prompt(ctx: SetupContext, question: str, default: str = '') -> str:
    if ctx.non_interactive:
        return default or os.environ.get(question.upper().replace(' ', '_').replace('?', ''), default)
    suffix = f' [{default}]' if default else ''
    answer = input(f'{question}{suffix}: ').strip()
    return answer or default


def prompt_yes_no(ctx: SetupContext, question: str, default: bool = True) -> bool:
    if ctx.non_interactive:
        env_key = question.upper().replace(' ', '_').replace('?', '')
        val = os.environ.get(env_key, 'Y' if default else 'N')
        return val.lower() in ('y', 'yes', 'true', '1')
    default_str = 'Y/n' if default else 'y/N'
    answer = input(f'{question} [{default_str}]: ').strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes')


def apply_env_overrides(ctx: SetupContext) -> None:
    env = os.environ
    ctx.domain = env.get('DOMAIN', ctx.domain)
    ctx.api_domain = env.get('API_DOMAIN', ctx.api_domain)
    ctx.web_domain = env.get('WEB_DOMAIN', ctx.web_domain)
    ctx.smtp_hostname = env.get('SMTP_HOSTNAME', ctx.smtp_hostname)
    ctx.admin_email = env.get('ADMIN_EMAIL', ctx.admin_email)
    ctx.digitalocean_token = env.get('DIGITALOCEAN_TOKEN', ctx.digitalocean_token)
    ctx.timezone = env.get('TIMEZONE', ctx.timezone)
    if env.get('INSTALL_MONITORING'):
        ctx.install_monitoring = env['INSTALL_MONITORING'].lower() in ('1', 'true', 'yes')
    if env.get('CONFIGURE_BACKUPS'):
        ctx.configure_backups = env['CONFIGURE_BACKUPS'].lower() in ('1', 'true', 'yes')


def load_config(ctx: SetupContext) -> SetupContext:
    if ctx.config_file and ctx.config_file.exists():
        file_vals = load_config_file(ctx.config_file)
        for key, val in file_vals.items():
            os.environ.setdefault(key, val)

    apply_env_overrides(ctx)
    ctx.public_ip = detect_public_ip()
    ctx.ssh_port = detect_ssh_port()

    if not ctx.domain:
        ctx.domain = prompt(ctx, 'Production domain', 'example.com')
    if not ctx.api_domain:
        ctx.api_domain = prompt(ctx, 'API domain', f'api.{ctx.domain}')
    if not ctx.web_domain:
        ctx.web_domain = prompt(ctx, 'Web domain', f'app.{ctx.domain}')
    if not ctx.smtp_hostname:
        ctx.smtp_hostname = prompt(ctx, 'SMTP hostname', f'smtp.{ctx.domain}')
    if not ctx.admin_email:
        ctx.admin_email = prompt(ctx, 'Admin email', f'admin@{ctx.domain}')

    if not ctx.non_interactive:
        ctx.install_monitoring = prompt_yes_no(ctx, 'Install monitoring?', ctx.install_monitoring)
        ctx.configure_backups = prompt_yes_no(ctx, 'Configure automatic backups?', ctx.configure_backups)

    _validate_domains(ctx)
    return ctx


def _validate_domains(ctx: SetupContext) -> None:
    for label, value in [
        ('domain', ctx.domain),
        ('api_domain', ctx.api_domain),
        ('web_domain', ctx.web_domain),
        ('smtp_hostname', ctx.smtp_hostname),
        ('admin_email', ctx.admin_email),
    ]:
        if not value or ' ' in value:
            raise ValueError(f'Invalid {label}: {value!r}')

    if '@' not in ctx.admin_email:
        raise ValueError(f'Invalid admin email: {ctx.admin_email}')


def generate_production_env(ctx: SetupContext, env_path: Path) -> dict[str, str]:
    """Generate .env.production secrets. Returns dict but never prints secrets."""
    existing: dict[str, str] = {}
    if env_path.exists():
        existing = load_config_file(env_path)

    def get_or_create(key: str, factory=generate_secret) -> str:
        return existing.get(key) or factory()

    secrets = {
        'DOMAIN': ctx.domain,
        'API_DOMAIN': ctx.api_domain,
        'WEB_DOMAIN': ctx.web_domain,
        'SMTP_HOSTNAME': ctx.smtp_hostname,
        'ADMIN_EMAIL': ctx.admin_email,
        'POSTGRES_USER': existing.get('POSTGRES_USER', 'apiemail'),
        'POSTGRES_PASSWORD': get_or_create('POSTGRES_PASSWORD'),
        'POSTGRES_DB': existing.get('POSTGRES_DB', 'apiemail'),
        'REDIS_PASSWORD': get_or_create('REDIS_PASSWORD'),
        'JWT_SECRET': get_or_create('JWT_SECRET'),
        'API_KEY_SECRET': get_or_create('API_KEY_SECRET'),
        'WEBHOOK_SECRET': get_or_create('WEBHOOK_SECRET'),
        'ENCRYPTION_KEY': get_or_create('ENCRYPTION_KEY', lambda: generate_secret(64)),
        'INTERNAL_API_TOKEN': get_or_create('INTERNAL_API_TOKEN'),
        'DATABASE_URL': '',
        'API_PUBLIC_URL': f'https://{ctx.api_domain}',
        'WEB_PUBLIC_URL': f'https://{ctx.web_domain}',
        'SMTP_HOST': 'host.docker.internal',
        'SMTP_PORT': '25',
        'CORS_ORIGIN': f'https://{ctx.web_domain}',
        'WORKER_REPLICAS': existing.get('WORKER_REPLICAS', '1'),
    }
    secrets['DATABASE_URL'] = (
        f"postgresql://{secrets['POSTGRES_USER']}:{secrets['POSTGRES_PASSWORD']}"
        f"@postgres:5432/{secrets['POSTGRES_DB']}"
    )
    return secrets
