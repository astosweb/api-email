# Deployment Guide

## Prerequisites

- Fresh Ubuntu 24.04 LTS DigitalOcean Droplet (x86_64)
- Minimum 2GB RAM, 20GB disk
- Domain with DNS access
- SSH key-based access configured

## Installation

```bash
git clone https://github.com/astosweb/api-email.git /opt/api-email-src
cd /opt/api-email-src
sudo python3 setup.py
```

### Non-interactive

Create a config file from the example:

```bash
cp production.env.example production.env
# Edit domains and admin email
sudo python3 setup.py --non-interactive --config production.env
```

### Dry run

Preview all actions without modifying the system:

```bash
sudo python3 setup.py --dry-run
```

## What Gets Installed

1. System packages (Postfix, OpenDKIM, UFW, Fail2Ban, Certbot)
2. Docker + Docker Compose
3. Firewall (SSH, 80, 443, 25, 587 only)
4. Mail infrastructure (Postfix + DKIM, no open relay)
5. Application stack (API, Worker, Web, PostgreSQL, Redis, Nginx)
6. TLS certificates (after DNS is configured)
7. Monitoring cron job

## Post-Install

1. Configure DNS records printed by the installer
2. Set PTR/rDNS in DigitalOcean control panel
3. Request SMTP port 25 unblock if needed
4. Run verification:

```bash
sudo python3 setup.py verify
```

## Updates

```bash
cd /opt/api-email-src
git pull
sudo python3 setup.py update
```

## Troubleshooting

```bash
sudo python3 setup.py doctor
sudo python3 setup.py logs --service api
sudo python3 setup.py status
```

See [DIGITALOCEAN.md](./DIGITALOCEAN.md) for provider-specific steps.
