"""Production health verification."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from setup.application import get_compose_file
from setup import postfix, tls
from setup.utils import SetupContext, command_exists, log_error, log_success, run_cmd


def verify_installation(ctx: SetupContext) -> int:
    failures = 0
    print('\nSystem')
    failures += _check('Ubuntu 24.04', _check_ubuntu(), True)
    failures += _check('x86_64', _check_arch(), True)
    failures += _check('Disk space', _check_disk(), True)
    failures += _check('Memory', _check_memory(), False)

    print('\nSecurity')
    failures += _check('Firewall', _check_ufw(), True)
    failures += _check('SSH', _check_ssh(), True)
    failures += _check('Fail2Ban', _check_fail2ban(), False)

    print('\nDocker')
    failures += _check('Docker', command_exists('docker'), True)
    failures += _check('Docker Compose', _check_compose(), True)

    print('\nApplication')
    failures += _check('API', _check_api_health(ctx), True)
    failures += _check('Worker', _check_container('worker', ctx), True)
    failures += _check('Web', _check_container('web', ctx), True)

    print('\nInfrastructure')
    failures += _check('PostgreSQL', _check_container('postgres', ctx), True)
    failures += _check('Redis', _check_container('redis', ctx), True)

    print('\nMail')
    failures += _check('Postfix', _check_postfix(), True)
    failures += _check('DKIM', _check_opendkim(), True)
    failures += _check('No open relay', postfix.verify_no_open_relay(ctx), True)
    failures += _check('TLS', _check_tls(ctx), False)
    failures += _check('SMTP port', _check_smtp_port(), False)

    print('\n' + '═' * 46)
    if failures:
        log_error(f'{failures} critical check(s) failed')
        return 1
    log_success('All critical checks passed')
    return 0


def _check(label: str, ok: bool, critical: bool) -> int:
    status = '✓' if ok else ('✗' if critical else '!')
    print(f'  {status} {label}')
    return 0 if ok or not critical else 1


def _check_ubuntu() -> bool:
    try:
        with open('/etc/os-release') as f:
            content = f.read()
        return 'ubuntu' in content.lower() and '24.04' in content
    except OSError:
        return False


def _check_arch() -> bool:
    import platform
    return platform.machine() in ('x86_64', 'amd64')


def _check_disk() -> bool:
    import shutil
    try:
        return shutil.disk_usage('/').free > 5 * 1024 ** 3
    except OSError:
        return False


def _check_memory() -> bool:
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    return int(line.split()[1]) > 1024 * 1024
    except (OSError, ValueError):
        pass
    return False


def _check_ufw() -> bool:
    if not command_exists('ufw'):
        return False
    result = run_cmd(['ufw', 'status'], SetupContext(dry_run=False), check=False, capture=True)
    return 'Status: active' in result.stdout


def _check_ssh() -> bool:
    return run_cmd(['systemctl', 'is-active', 'ssh'], SetupContext(dry_run=False), check=False).returncode == 0


def _check_fail2ban() -> bool:
    return run_cmd(['systemctl', 'is-active', 'fail2ban'], SetupContext(dry_run=False), check=False).returncode == 0


def _check_compose() -> bool:
    return run_cmd(['docker', 'compose', 'version'], SetupContext(dry_run=False), check=False).returncode == 0


def _check_container(name: str, ctx: SetupContext) -> bool:
    compose = get_compose_file(ctx)
    env_file = ctx.repo_root / '.env.production'
    result = run_cmd([
        'docker', 'compose', '--env-file', str(env_file),
        '-f', str(compose), 'ps', '--format', 'json', name,
    ], ctx, check=False, capture=True)
    if result.returncode != 0:
        return False
    try:
        for line in result.stdout.strip().splitlines():
            if line:
                data = json.loads(line)
                return data.get('State') == 'running'
    except json.JSONDecodeError:
        pass
    return 'running' in result.stdout.lower()


def _check_api_health(ctx: SetupContext) -> bool:
    try:
        req = urllib.request.Request('http://localhost:4000/health/live')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return _check_container('api', ctx)


def _check_postfix() -> bool:
    return run_cmd(['systemctl', 'is-active', 'postfix'], SetupContext(dry_run=False), check=False).returncode == 0


def _check_opendkim() -> bool:
    return run_cmd(['systemctl', 'is-active', 'opendkim'], SetupContext(dry_run=False), check=False).returncode == 0


def _check_tls(ctx: SetupContext) -> bool:
    cert = tls.verify_certificate(ctx.api_domain)
    return cert.get('valid', False)


def _check_smtp_port() -> bool:
    import socket
    try:
        with socket.create_connection(('localhost', 25), timeout=3):
            return True
    except OSError:
        return False
