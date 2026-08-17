# DigitalOcean Guide

## Droplet Requirements

- **Image:** Ubuntu 24.04 LTS
- **Size:** Minimum 2GB RAM / 1 vCPU (4GB recommended for production)
- **Region:** Choose closest to your users
- **Authentication:** SSH keys only (recommended)

## Network

### Firewall (UFW)

Configured automatically by `setup.py`:

| Port | Service |
|------|---------|
| 22 (or detected SSH port) | SSH |
| 80 | HTTP (Certbot + redirect) |
| 443 | HTTPS |
| 25 | SMTP |
| 587 | Submission |

PostgreSQL (5432) and Redis (6379) are **never** exposed publicly.

### Reserved IP

Recommended for production SMTP. Assign in DigitalOcean → Networking → Reserved IPs.

Update DNS A records to point to the reserved IP.

## SMTP Port 25

New DigitalOcean accounts often have port 25 blocked.

1. Open a support ticket requesting SMTP port unblock
2. Explain legitimate transactional email use case
3. Verify after unblock: `nc -zv smtp.example.com 25`

## Reverse DNS (PTR)

1. DigitalOcean Control Panel → Droplet → Networking
2. Set PTR record: `<IP>` → `smtp.example.com`
3. Verify: `dig -x <IP> +short`

The installer prints required PTR but cannot configure it via API from inside the Droplet.

## DNS Records

Configure in DigitalOcean DNS or your DNS provider:

```
api.example.com     A     <PUBLIC_IP>
app.example.com     A     <PUBLIC_IP>
smtp.example.com    A     <PUBLIC_IP>
example.com         MX    10 smtp.example.com
example.com         TXT   v=spf1 ip4:<PUBLIC_IP> mx -all
_dmarc.example.com  TXT   v=DMARC1; p=none; rua=mailto:admin@example.com
apiemail._domainkey.example.com TXT v=DKIM1; k=rsa; p=...
```

### Optional: DigitalOcean API

If `DIGITALOCEAN_TOKEN` is set, future versions can automate DNS record creation.
Currently the installer prints exact records for manual configuration.

## IPv6

Not required. The installer uses IPv4 by default for Postfix (`inet_protocols = ipv4`).

## Rebuilding a Destroyed Droplet

```bash
# 1. Create new Ubuntu 24.04 Droplet
# 2. Clone and install
git clone https://github.com/astosweb/api-email.git
cd api-email
sudo python3 setup.py --non-interactive --config production.env

# 3. Restore backup
sudo python3 setup.py restore --backup-path /path/to/backup

# 4. Verify
sudo python3 setup.py verify
```

See [BACKUP-RECOVERY.md](./BACKUP-RECOVERY.md).
