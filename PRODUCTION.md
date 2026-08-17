# Production Operations

## Service Layout

| Service | Access | Port |
|---------|--------|------|
| API | https://api.example.com | 443 (via Nginx) |
| Web | https://app.example.com | 443 (via Nginx) |
| PostgreSQL | Internal Docker network only | — |
| Redis | Internal Docker network only | — |
| Postfix | Host (SMTP) | 25 |
| OpenDKIM | localhost:8891 | — |

## Environment

Production secrets live in `/opt/api-email/.env.production` (mode 600).
Installation state: `/var/lib/yourapp/setup/state.json`.

## Health Checks

- API: `GET /health`, `/health/live`, `/health/ready`
- Docker healthchecks on all containers
- Postfix: `postqueue -p`, `/var/log/mail.log`

## Scaling Workers

Edit `.env.production`:

```
WORKER_REPLICAS=2
```

Then:

```bash
sudo python3 setup.py update
```

## Log Rotation

Application logs via Docker. Mail logs rotated by system logrotate.
Monitor script: `/opt/api-email/scripts/monitor.sh` (every 5 min).

## Migrations

Migrations run automatically during install/update via Prisma `db push`.
Never run destructive migration commands in production without backup.

## Rollback

1. Restore from backup: `sudo python3 setup.py restore --backup-path /var/backups/api-email/TIMESTAMP`
2. Or redeploy previous Docker images manually

See [BACKUP-RECOVERY.md](./BACKUP-RECOVERY.md).
