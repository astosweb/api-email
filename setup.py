#!/usr/bin/env python3
"""API Email production installer.

Usage:
    sudo python3 setup.py [command] [options]

Commands:
    install     Run full installation (default)
    verify      Verify production health
    doctor      Diagnose problems
    update      Update application safely
    backup      Backup database and configuration
    restore     Restore from backup
    status      Show service status
    logs        View service logs
    rollback    Rollback to previous version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from setup import __version__
from setup.utils import (
    SetupContext,
    ensure_root,
    print_banner,
    print_complete,
    log_step,
    log_success,
    log_error,
    colorize,
    Colors,
)
from setup.config import load_config
from setup.system import check_requirements, prepare_system
from setup.security import configure_security
from setup.docker import install_docker
from setup.firewall import configure_firewall
from setup.hostname import configure_hostname
from setup.mail import configure_mail
from setup.database import configure_database, run_migrations
from setup.redis import configure_redis
from setup.application import deploy_application, get_compose_file
from setup.monitoring import configure_monitoring
from setup.tls import obtain_certificates
from setup.verification import verify_installation
from setup.doctor import run_doctor
from setup.backup import run_backup, run_restore, BACKUP_DIR
from setup.utils import run_cmd, write_state


INSTALL_STEPS = [
    ('Detecting system', lambda ctx: check_requirements(ctx)),
    ('Preparing Ubuntu', prepare_system),
    ('Configuring security', configure_security),
    ('Installing Docker', install_docker),
    ('Configuring firewall', configure_firewall),
    ('Setting hostname', configure_hostname),
    ('Configuring PostgreSQL', configure_database),
    ('Configuring Redis', configure_redis),
    ('Configuring Postfix', configure_mail),
    ('Deploying application', deploy_application),
    ('Running migrations', run_migrations),
    ('Configuring monitoring', configure_monitoring),
    ('Obtaining TLS certificates', obtain_certificates),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='API Email production installer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('command', nargs='?', default='install',
                        choices=['install', 'verify', 'doctor', 'update', 'backup',
                                 'restore', 'status', 'logs', 'rollback'])
    parser.add_argument('--non-interactive', action='store_true')
    parser.add_argument('--config', type=Path, dest='config_file')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--no-color', action='store_true')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--backup-path', type=Path, help='Path for restore')
    parser.add_argument('--service', default='api', help='Service for logs command')
    parser.add_argument('--lines', type=int, default=100, help='Log lines to show')
    return parser


def run_install(ctx: SetupContext) -> int:
    print_banner(ctx)
    ctx = load_config(ctx)
    total = len(INSTALL_STEPS)

    for i, (label, fn) in enumerate(INSTALL_STEPS, 1):
        log_step(i, total, label, ctx)
        try:
            fn(ctx)
            log_success(label, ctx)
        except Exception as e:
            log_error(f'{label} failed: {e}', ctx)
            write_state({'last_failed_step': label}, ctx)
            return 1

    write_state({'installation_complete': True}, ctx)
    print_complete(ctx)
    return 0


def run_update(ctx: SetupContext) -> int:
    print_banner(ctx)
    ctx = load_config(ctx)
    log_step(1, 4, 'Pulling latest code', ctx)
    run_cmd(['git', 'pull', '--ff-only'], ctx, cwd=ctx.repo_root, check=False)
    log_step(2, 4, 'Building images', ctx)
    deploy_application(ctx)
    log_step(3, 4, 'Running migrations', ctx)
    run_migrations(ctx)
    log_step(4, 4, 'Verifying health', ctx)
    return verify_installation(ctx)


def run_status(ctx: SetupContext) -> int:
    compose = get_compose_file(ctx)
    services = ['api', 'worker', 'web', 'postgres', 'redis']
    print('\nService Status\n')
    for svc in services:
        result = run_cmd([
            'docker', 'compose', '-f', str(compose), 'ps', '--format',
            '{{.Name}} {{.Status}}', svc,
        ], ctx, check=False, capture=True)
        status = result.stdout.strip() or 'not found'
        icon = '✓' if 'running' in status.lower() or 'Up' in status else '✗'
        print(f'  {svc:<12} {icon} {status}')

    for svc, cmd in [('Postfix', 'postfix'), ('OpenDKIM', 'opendkim')]:
        result = run_cmd(['systemctl', 'is-active', cmd], ctx, check=False, capture=True)
        icon = '✓' if result.stdout.strip() == 'active' else '✗'
        print(f'  {svc:<12} {icon} {result.stdout.strip()}')
    return 0


def run_logs(ctx: SetupContext) -> int:
    compose = get_compose_file(ctx)
    if ctx.service in ('postfix', 'mail'):
        run_cmd(['tail', '-n', str(ctx.lines), '/var/log/mail.log'], ctx, check=False)
    else:
        run_cmd([
            'docker', 'compose', '-f', str(compose),
            'logs', '--tail', str(ctx.lines), ctx.service,
        ], ctx, check=False)
    return 0


def run_rollback(ctx: SetupContext) -> int:
    tag_file = Path('/var/lib/yourapp/setup/previous_image_tag')
    if not tag_file.exists():
        log_error('No previous version recorded for rollback')
        log_error('Rollback requires a tagged previous deployment. Run update first.')
        return 1
    log_error('Rollback: redeploy previous Docker images manually or restore from backup')
    log_error(f'  Backup location: {BACKUP_DIR}')
    return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    ctx = SetupContext(
        dry_run=args.dry_run,
        verbose=args.verbose,
        no_color=args.no_color,
        non_interactive=args.non_interactive,
        config_file=args.config_file,
    )
    ctx.service = args.service
    ctx.lines = args.lines

    needs_root = args.command != 'verify'
    if needs_root:
        ensure_root()

    commands = {
        'install': run_install,
        'verify': lambda c: verify_installation(c),
        'doctor': lambda c: run_doctor(load_config(c)),
        'update': run_update,
        'backup': lambda c: run_backup(c) or 0,
        'restore': lambda c: run_restore(c, args.backup_path or BACKUP_DIR),
        'status': run_status,
        'logs': run_logs,
        'rollback': run_rollback,
    }

    return commands[args.command](ctx)


if __name__ == '__main__':
    sys.exit(main())
