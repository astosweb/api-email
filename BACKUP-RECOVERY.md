# Backup & Recovery

## Backup

```bash
sudo python3 setup.py backup
```

Backups stored in `/var/backups/api-email/<timestamp>/`:

- `postgres.sql` — PostgreSQL dump
- `.env.production` — application secrets (mode 600)
- `infrastructure/` — Postfix, Nginx, DKIM configs
- `keys/` — DKIM private keys

### Automated Backups

When `CONFIGURE_BACKUPS=true`, a daily cron can be added:

```bash
0 3 * * * root /usr/bin/python3 /opt/api-email/setup.py backup
```

## Restore PostgreSQL

```bash
BACKUP=/var/backups/api-email/20260101-030000
docker compose -f /opt/api-email/docker-compose.production.yml \
  exec -T postgres psql -U apiemail apiemail < $BACKUP/postgres.sql
```

## Restore DKIM Keys

```bash
sudo cp -a $BACKUP/keys/* /etc/opendkim/keys/
sudo chown -R opendkim:opendkim /etc/opendkim/keys
sudo chmod 600 /etc/opendkim/keys/*/*.private
sudo systemctl restart opendkim
```

## Restore Configuration

```bash
sudo cp $BACKUP/.env.production /opt/api-email/.env.production
sudo chmod 600 /opt/api-email/.env.production
sudo cp -a $BACKUP/infrastructure/* /opt/api-email/infrastructure/
```

## Full Droplet Recovery

```
Destroyed Droplet
       ↓
New Ubuntu 24.04 Droplet
       ↓
git clone + sudo python3 setup.py
       ↓
Restore backup (DB + DKIM + config)
       ↓
sudo python3 setup.py verify
       ↓
Production restored
```

## Off-Site Backups

Copy backups to external storage:

```bash
rsync -az /var/backups/api-email/ user@backup-server:/backups/api-email/
```

Never store backups in a public bucket without encryption.
