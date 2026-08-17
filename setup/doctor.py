"""Diagnostic doctor command."""

from __future__ import annotations

import shutil
import socket

from setup import dkim, postfix
from setup.application import get_compose_file
from setup.utils import SetupContext, log_error, log_warn, run_cmd


def run_doctor(ctx: SetupContext) -> int:
    issues = 0

    # Disk
    usage = shutil.disk_usage('/')
    pct = (usage.used / usage.total) * 100
    if pct > 80:
        log_warn(f'Disk usage is {pct:.0f}% — consider expanding storage or cleaning logs')
        issues += 1

    # SMTP port 25
    try:
        with socket.create_connection(('localhost', 25), timeout=3) as s:
            s.send(b'EHLO doctor\r\n')
            s.recv(1024)
    except OSError:
        log_error('SMTP port 25 unavailable — check Postfix and DigitalOcean port 25 policy')
        log_error('  Fix: sudo systemctl restart postfix; request port 25 unblock from DigitalOcean')
        issues += 1

    # PTR
    if ctx.public_ip:
        try:
            hostname = socket.gethostbyaddr(ctx.public_ip)[0]
            if ctx.smtp_hostname not in hostname:
                log_warn(f'PTR record ({hostname}) does not match SMTP hostname ({ctx.smtp_hostname})')
                log_warn('  Fix: Set rDNS in DigitalOcean control panel → Droplet → Networking')
                issues += 1
        except socket.herror:
            log_warn(f'No PTR record for {ctx.public_ip}')
            log_warn('  Fix: Configure reverse DNS in DigitalOcean control panel')

    # DKIM
    if run_cmd(['systemctl', 'is-active', 'opendkim'], ctx, check=False).returncode != 0:
        log_error('OpenDKIM service is not running')
        log_error('  Fix: sudo systemctl restart opendkim && sudo systemctl status opendkim')
        issues += 1

    # Open relay check
    if not postfix.verify_no_open_relay(ctx):
        log_error('Postfix may allow open relay — CRITICAL security issue')
        log_error('  Fix: Ensure smtpd_relay_restrictions includes reject_unauth_destination')
        issues += 1

    # Postfix queue
    result = run_cmd(['postqueue', '-p'], ctx, check=False, capture=True)
    if 'Request' in result.stdout:
        import re
        match = re.search(r'(\d+) Request', result.stdout)
        if match and int(match.group(1)) > 50:
            log_warn(f'Postfix queue has {match.group(1)} deferred messages')
            log_warn('  Fix: Check mail logs: sudo tail -f /var/log/mail.log')

    # Docker containers
    compose = get_compose_file(ctx)
    for svc in ('api', 'worker', 'web', 'postgres', 'redis'):
        result = run_cmd([
            'docker', 'compose', '-f', str(compose), 'ps', svc,
        ], ctx, check=False, capture=True)
        if 'running' not in result.stdout.lower() and 'Up' not in result.stdout:
            log_error(f'Container {svc} is not running')
            log_error(f'  Fix: sudo python3 setup.py update')
            issues += 1

    # DNS records reminder
    record = dkim.get_dkim_dns_record(ctx)
    if not record:
        log_warn('DKIM DNS record not available — keys may not be generated yet')
        log_warn('  Fix: sudo python3 setup.py install (dkim step)')

    if issues:
        print(f'\n{issues} issue(s) found. See recommendations above.')
        return 1
    print('\nNo critical issues found.')
    return 0
