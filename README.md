# API Email

Production-grade developer email API and self-hosted email infrastructure.

## Quick Start (Production)

On a fresh **Ubuntu 24.04** DigitalOcean Droplet:

```bash
git clone https://github.com/astosweb/api-email.git
cd api-email
sudo python3 setup.py
```

Non-interactive:

```bash
sudo python3 setup.py --non-interactive --config production.env.example
```

## Commands

```bash
sudo python3 setup.py              # Full install
sudo python3 setup.py verify       # Health checks
sudo python3 setup.py doctor       # Diagnostics
sudo python3 setup.py status       # Service status
sudo python3 setup.py update       # Safe update
sudo python3 setup.py backup       # Backup DB + config
sudo python3 setup.py logs --service api
sudo python3 setup.py --dry-run    # Preview changes
```

## Architecture

```
NestJS API → Redis/BullMQ → Email Worker → Postfix → Internet
     ↓              ↓
 PostgreSQL    Web Dashboard
```

## Local Development

```bash
pnpm install
docker compose -f docker-compose.dev.yml up -d
cp .env.example .env
pnpm generate && pnpm db:push
pnpm dev
```

- API: http://localhost:4000
- Web: http://localhost:3000
- MailHog: http://localhost:8025

## Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [PRODUCTION.md](./PRODUCTION.md)
- [MAIL-INFRASTRUCTURE.md](./MAIL-INFRASTRUCTURE.md)
- [DIGITALOCEAN.md](./DIGITALOCEAN.md)
- [BACKUP-RECOVERY.md](./BACKUP-RECOVERY.md)
- [SECURITY.md](./SECURITY.md)

## API

```bash
curl -X POST https://api.example.com/v1/emails \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "from": "hello@example.com",
    "to": "user@example.com",
    "subject": "Hello",
    "text": "Welcome!"
  }'
```
