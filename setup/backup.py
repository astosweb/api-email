"""Backup and restore operations."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from setup.application import get_compose_file
from setup.utils import SetupContext, INSTALL_DIR, log_success, log_info, run_cmd


BACKUP_DIR = Path('/var/backups/api-email')


def run_backup(ctx: SetupContext) -> None:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    dest = BACKUP_DIR / timestamp
    if not ctx.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    compose = get_compose_file(ctx)
    env_file = INSTALL_DIR / '.env.production'
    if not env_file.exists():
        env_file = ctx.repo_root / '.env.production'

    # PostgreSQL dump
    run_cmd([
        'docker', 'compose', '--env-file', str(env_file),
        '-f', str(compose), 'exec', '-T', 'postgres',
        'pg_dump', '-U', 'apiemail', 'apiemail',
    ], ctx, capture=True)

    if not ctx.dry_run:
        result = run_cmd([
            'docker', 'compose', '--env-file', str(env_file),
            '-f', str(compose), 'exec', '-T', 'postgres',
            'pg_dump', '-U', 'apiemail', 'apiemail',
        ], ctx, capture=True)
        (dest / 'postgres.sql').write_text(result.stdout)

    # Config and DKIM keys
    for src in [
        INSTALL_DIR / '.env.production',
        INSTALL_DIR / 'infrastructure',
        Path('/etc/opendkim/keys'),
    ]:
        if src.exists() and not ctx.dry_run:
            if src.is_dir():
                shutil.copytree(src, dest / src.name, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest / src.name)

    log_success(f'Backup saved to {dest}', ctx)


def run_restore(ctx: SetupContext, backup_path: Path) -> None:
    if not backup_path.exists():
        raise RuntimeError(f'Backup not found: {backup_path}')

    pg_dump = backup_path / 'postgres.sql'
    if pg_dump.exists():
        compose = get_compose_file(ctx)
        env_file = INSTALL_DIR / '.env.production'
        run_cmd([
            'docker', 'compose', '--env-file', str(env_file),
            '-f', str(compose), 'exec', '-T', 'postgres',
            'psql', '-U', 'apiemail', 'apiemail',
        ], ctx)

    log_success(f'Restore initiated from {backup_path}', ctx)
    log_info('Review BACKUP-RECOVERY.md for complete restore procedure', ctx)
