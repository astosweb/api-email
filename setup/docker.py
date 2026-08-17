"""Docker installation and verification."""

from __future__ import annotations

import re

from setup.utils import SetupContext, command_exists, log_success, mark_step, run_cmd, step_completed


def docker_installed() -> bool:
    return command_exists('docker') and command_exists('docker')


def docker_compose_available() -> bool:
    if command_exists('docker'):
        result = run_cmd(
            ['docker', 'compose', 'version'],
            SetupContext(dry_run=False),
            check=False,
            capture=True,
        )
        return result.returncode == 0
    return False


def get_docker_version() -> str:
    try:
        result = run_cmd(
            ['docker', '--version'],
            SetupContext(dry_run=False),
            check=False,
            capture=True,
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'


def install_docker(ctx: SetupContext) -> None:
    if step_completed('docker') and docker_installed() and docker_compose_available():
        log_success(f'Docker already installed ({get_docker_version()})', ctx)
        run_cmd(['systemctl', 'enable', 'docker'], ctx, check=False)
        run_cmd(['systemctl', 'start', 'docker'], ctx, check=False)
        return

    if docker_installed() and docker_compose_available():
        log_success('Docker already installed', ctx)
        mark_step('docker', ctx)
        return

    run_cmd(['install', '-m', '0755', '-d', '/etc/apt/keyrings'], ctx)
    run_cmd([
        'curl', '-fsSL', 'https://download.docker.com/linux/ubuntu/gpg',
        '-o', '/etc/apt/keyrings/docker.asc',
    ], ctx)
    run_cmd(['chmod', 'a+r', '/etc/apt/keyrings/docker.asc'], ctx)

    arch = 'amd64'
    codename = _get_codename()
    repo_line = (
        f'deb [arch={arch} signed-by=/etc/apt/keyrings/docker.asc] '
        f'https://download.docker.com/linux/ubuntu {codename} stable'
    )
    if not ctx.dry_run:
        with open('/etc/apt/sources.list.d/docker.list', 'w') as f:
            f.write(repo_line + '\n')

    run_cmd(['apt-get', 'update', '-qq'], ctx)
    run_cmd([
        'apt-get', 'install', '-y', '-qq',
        'docker-ce', 'docker-ce-cli', 'containerd.io',
        'docker-buildx-plugin', 'docker-compose-plugin',
    ], ctx)

    run_cmd(['systemctl', 'enable', 'docker'], ctx)
    run_cmd(['systemctl', 'start', 'docker'], ctx)
    mark_step('docker', ctx)
    log_success('Docker installed', ctx)


def _get_codename() -> str:
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('VERSION_CODENAME='):
                    return line.split('=', 1)[1].strip().strip('"')
    except OSError:
        pass
    return 'noble'
