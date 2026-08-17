"""System detection and preparation."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

from setup.utils import (
    SetupContext,
    command_exists,
    log_success,
    log_warn,
    mark_step,
    run_cmd,
    step_completed,
)

SUPPORTED_OS = ('ubuntu', 'debian')
SUPPORTED_UBUNTU = ('24.04',)
MIN_RAM_GB = 2
MIN_DISK_GB = 20

REQUIRED_PACKAGES = [
    'curl', 'wget', 'git', 'ca-certificates', 'gnupg', 'lsb-release',
    'ufw', 'fail2ban', 'postfix', 'opendkim', 'opendkim-tools',
    'certbot', 'python3-certbot-nginx', 'jq', 'dnsutils',
    'logrotate', 'unattended-upgrades', 'apt-transport-https',
]


def detect_system() -> dict:
    return {
        'os': platform.system().lower(),
        'distro': _read_os_release('ID', 'unknown'),
        'version': _read_os_release('VERSION_ID', 'unknown'),
        'arch': platform.machine(),
        'hostname': platform.node(),
    }


def _read_os_release(key: str, default: str) -> str:
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            if line.startswith(f'{key}='):
                return line.split('=', 1)[1].strip().strip('"')
    except OSError:
        pass
    return default


def check_requirements(ctx: SetupContext) -> None:
    info = detect_system()
    if info['os'] != 'linux':
        raise RuntimeError(f'Unsupported OS: {info["os"]}. Requires Linux.')
    if info['distro'] not in SUPPORTED_OS:
        raise RuntimeError(f'Unsupported distro: {info["distro"]}. Requires Ubuntu 24.04.')
    if info['distro'] == 'ubuntu' and info['version'] not in SUPPORTED_UBUNTU:
        raise RuntimeError(
            f'Unsupported Ubuntu version: {info["version"]}. Requires Ubuntu 24.04 LTS.'
        )
    if info['arch'] not in ('x86_64', 'amd64'):
        raise RuntimeError(f'Unsupported architecture: {info["arch"]}. Requires x86_64.')

    mem_kb = _read_mem_total_kb()
    if mem_kb and mem_kb < MIN_RAM_GB * 1024 * 1024:
        mem_gb = mem_kb / (1024 * 1024)
        log_warn(f'Low memory: {mem_gb:.1f}GB (recommended {MIN_RAM_GB}GB+)', ctx)

    disk_gb = _free_disk_gb('/')
    if disk_gb and disk_gb < MIN_DISK_GB:
        raise RuntimeError(f'Insufficient disk space: {disk_gb}GB free (need {MIN_DISK_GB}GB+)')

    if not ctx.public_ip:
        log_warn('Could not detect public IP automatically', ctx)

    run_cmd(['ping', '-c', '1', '-W', '3', '8.8.8.8'], ctx, check=False)


def _read_mem_total_kb() -> int | None:
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemTotal:'):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _free_disk_gb(path: str) -> int | None:
    try:
        usage = shutil.disk_usage(path)
        return usage.free // (1024 ** 3)
    except OSError:
        return None


def prepare_system(ctx: SetupContext) -> None:
    if step_completed('system_prepare') and _packages_installed():
        log_success('System packages already installed', ctx)
        return

    run_cmd(['apt-get', 'update', '-qq'], ctx)
    run_cmd(
        ['apt-get', 'install', '-y', '-qq'] + REQUIRED_PACKAGES,
        ctx,
        env={'DEBIAN_FRONTEND': 'noninteractive'},
    )

    if ctx.timezone and ctx.timezone != 'UTC':
        run_cmd(['timedatectl', 'set-timezone', ctx.timezone], ctx, check=False)

    _configure_limits(ctx)
    _configure_unattended_upgrades(ctx)
    mark_step('system_prepare', ctx)
    log_success('System prepared', ctx)


def _packages_installed() -> bool:
    return all(command_exists(cmd) for cmd in ('curl', 'ufw', 'postfix'))


def _configure_limits(ctx: SetupContext) -> None:
    limits = Path('/etc/security/limits.d/99-api-email.conf')
    content = '* soft nofile 65536\n* hard nofile 65536\n'
    if ctx.dry_run:
        return
    if not limits.exists() or limits.read_text() != content:
        limits.write_text(content)


def _configure_unattended_upgrades(ctx: SetupContext) -> None:
    cfg = Path('/etc/apt/apt.conf.d/20auto-upgrades')
    content = 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n'
    if ctx.dry_run:
        return
    if not cfg.exists():
        cfg.write_text(content)
