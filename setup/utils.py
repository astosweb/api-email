"""Shared utilities for the installer."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from setup import __version__

APP_NAME = 'api-email'
STATE_DIR = Path('/var/lib/yourapp/setup')
INSTALL_DIR = Path('/opt/api-email')
REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_DIR = INSTALL_DIR / 'infrastructure'

SENSITIVE_PATTERNS = re.compile(
    r'(password|secret|token|key|private|credential)',
    re.IGNORECASE,
)


@dataclass
class SetupContext:
    dry_run: bool = False
    verbose: bool = False
    no_color: bool = False
    non_interactive: bool = False
    config_file: Path | None = None
    domain: str = ''
    api_domain: str = ''
    web_domain: str = ''
    smtp_hostname: str = ''
    admin_email: str = ''
    install_monitoring: bool = True
    configure_backups: bool = True
    digitalocean_token: str = ''
    timezone: str = 'UTC'
    public_ip: str = ''
    ssh_port: int = 22
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    service: str = 'api'
    lines: int = 100


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    CYAN = '\033[36m'
    DIM = '\033[2m'


def supports_color(ctx: SetupContext) -> bool:
    if ctx.no_color or not sys.stdout.isatty():
        return False
    return True


def colorize(text: str, color: str, ctx: SetupContext) -> str:
    if not supports_color(ctx):
        return text
    return f'{color}{text}{Colors.RESET}'


def log_info(msg: str, ctx: SetupContext | None = None) -> None:
    print(msg)


def log_success(msg: str, ctx: SetupContext | None = None) -> None:
    prefix = colorize('✓', Colors.GREEN, ctx) if ctx else '✓'
    print(f'{prefix} {msg}')


def log_warn(msg: str, ctx: SetupContext | None = None) -> None:
    prefix = colorize('!', Colors.YELLOW, ctx) if ctx else '!'
    print(f'{prefix} {msg}')


def log_error(msg: str, ctx: SetupContext | None = None) -> None:
    prefix = colorize('✗', Colors.RED, ctx) if ctx else '✗'
    print(f'{prefix} {msg}', file=sys.stderr)


def log_step(step: int, total: int, label: str, ctx: SetupContext) -> None:
    num = colorize(f'[{step}/{total}]', Colors.CYAN, ctx)
    print(f'{num} {label}')


def mask_secret(key: str, value: str) -> str:
    if SENSITIVE_PATTERNS.search(key):
        return '***REDACTED***'
    return value


def run_cmd(
    cmd: list[str] | str,
    ctx: SetupContext,
    *,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = cmd

    display = ' '.join(shlex.quote(c) for c in cmd_list)
    if ctx.verbose:
        log_info(f'  $ {display}', ctx)

    if ctx.dry_run:
        log_info(f'  [dry-run] Would run: {display}', ctx)
        return subprocess.CompletedProcess(cmd_list, 0, stdout='', stderr='')

    result = subprocess.run(
        cmd_list,
        check=False,
        capture_output=capture,
        text=True,
        env={**os.environ, **(env or {})},
        cwd=str(cwd) if cwd else None,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ''
        raise RuntimeError(f'Command failed ({result.returncode}): {display}\n{stderr}')
    return result


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def read_state() -> dict[str, Any]:
    state_file = STATE_DIR / 'state.json'
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except json.JSONDecodeError:
        return {}


def write_state(data: dict[str, Any], ctx: SetupContext) -> None:
    if ctx.dry_run:
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    existing = read_state()
    existing.update(data)
    existing['updated_at'] = datetime.now(timezone.utc).isoformat()
    existing['version'] = __version__
    (STATE_DIR / 'state.json').write_text(json.dumps(existing, indent=2))
    os.chmod(STATE_DIR / 'state.json', 0o600)


def mark_step(step: str, ctx: SetupContext, *, success: bool = True) -> None:
    state = read_state()
    steps = state.get('completed_steps', [])
    if success and step not in steps:
        steps.append(step)
    write_state(
        {
            'completed_steps': steps,
            'last_step': step,
            'last_success': success,
        },
        ctx,
    )


def step_completed(step: str) -> bool:
    return step in read_state().get('completed_steps', [])


def generate_secret(length: int = 48) -> str:
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def ensure_root() -> None:
    if os.geteuid() != 0:
        raise SystemExit('This command must be run as root (sudo python3 setup.py)')


def print_banner(ctx: SetupContext) -> None:
    banner = '''
╔════════════════════════════════════════════╗
║       API EMAIL PLATFORM INSTALLER         ║
╚════════════════════════════════════════════╝
'''
    print(colorize(banner, Colors.BOLD, ctx))


def print_complete(ctx: SetupContext) -> None:
    print('\n' + '═' * 46)
    print(colorize('\nINSTALLATION COMPLETE\n', Colors.BOLD + Colors.GREEN, ctx))
    print(f'API:       https://{ctx.api_domain}')
    print(f'Dashboard: https://{ctx.web_domain}')
    print(f'SMTP:      {ctx.smtp_hostname}')
    print('\nRun:\n\n  sudo python3 setup.py verify\n')
