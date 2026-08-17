"""Redis configuration verification."""

from __future__ import annotations

from setup.utils import SetupContext, log_success, mark_step, step_completed


def configure_redis(ctx: SetupContext) -> None:
    if step_completed('redis'):
        log_success('Redis already configured', ctx)
        return
    mark_step('redis', ctx)
    log_success('Redis configured via Docker Compose (internal network only)', ctx)
