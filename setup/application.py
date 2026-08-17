"""Application deployment via Docker Compose."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from setup.config import generate_production_env
from setup.utils import (
    SetupContext,
    INSTALL_DIR,
    log_success,
    mark_step,
    run_cmd,
    step_completed,
)


def deploy_application(ctx: SetupContext) -> None:
    env_path = ctx.repo_root / '.env.production'
    secrets = generate_production_env(ctx, env_path)

    if not ctx.dry_run:
        lines = [f'{k}={v}\n' for k, v in secrets.items()]
        env_path.write_text(''.join(lines))
        os.chmod(env_path, 0o600)

    _sync_repo_to_install_dir(ctx)
    _render_nginx_config(ctx)
    _deploy_compose(ctx)
    mark_step('application', ctx)
    log_success('Application deployed', ctx)


def _sync_repo_to_install_dir(ctx: SetupContext) -> None:
    if ctx.dry_run:
        return
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    for item in ['docker-compose.production.yml', 'infrastructure', 'apps', 'packages', 'package.json', 'pnpm-workspace.yaml']:
        src = ctx.repo_root / item
        dest = INSTALL_DIR / item
        if src.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        elif src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    env_src = ctx.repo_root / '.env.production'
    if env_src.exists():
        shutil.copy2(env_src, INSTALL_DIR / '.env.production')
        os.chmod(INSTALL_DIR / '.env.production', 0o600)


def _render_nginx_config(ctx: SetupContext) -> None:
    template = ctx.repo_root / 'infrastructure' / 'nginx' / 'conf.d' / 'api.conf.template'
    if not template.exists():
        return
    content = template.read_text()
    content = content.replace('{{API_DOMAIN}}', ctx.api_domain)
    content = content.replace('{{WEB_DOMAIN}}', ctx.web_domain)
    dest = INSTALL_DIR / 'infrastructure' / 'nginx' / 'conf.d' / 'api.conf'
    if not ctx.dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)


def _deploy_compose(ctx: SetupContext) -> None:
    compose = INSTALL_DIR / 'docker-compose.production.yml'
    run_cmd([
        'docker', 'compose', '--env-file', str(INSTALL_DIR / '.env.production'),
        '-f', str(compose), 'build',
    ], ctx, cwd=INSTALL_DIR)

    run_cmd([
        'docker', 'compose', '--env-file', str(INSTALL_DIR / '.env.production'),
        '-f', str(compose), 'up', '-d',
    ], ctx, cwd=INSTALL_DIR)


def get_compose_file(ctx: SetupContext) -> Path:
    installed = INSTALL_DIR / 'docker-compose.production.yml'
    if installed.exists():
        return installed
    return ctx.repo_root / 'docker-compose.production.yml'
