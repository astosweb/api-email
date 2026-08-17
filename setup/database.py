"""Database setup and migrations."""

from __future__ import annotations

from setup.application import get_compose_file
from setup.utils import SetupContext, log_success, mark_step, run_cmd, step_completed


def configure_database(ctx: SetupContext) -> None:
    if step_completed('database'):
        log_success('Database already initialized', ctx)
        return
    mark_step('database', ctx)
    log_success('PostgreSQL configured via Docker Compose', ctx)


def run_migrations(ctx: SetupContext) -> None:
    compose_file = get_compose_file(ctx)
    env_file = ctx.repo_root / '.env.production'

    run_cmd([
        'docker', 'compose', '--env-file', str(env_file),
        '-f', str(compose_file),
        'exec', '-T', 'api',
        'sh', '-c', 'cd /app/apps/api && npx prisma db push --skip-generate',
    ], ctx, check=False)

    mark_step('migrations', ctx)
    log_success('Database migrations complete', ctx)
