# Security

## Network

- UFW denies all incoming except SSH, 80, 443, 25, 587
- PostgreSQL and Redis on internal Docker network only
- Docker socket not exposed

## Authentication

- API: Bearer token (SHA-256 hashed API keys)
- Internal dashboard: `INTERNAL_API_TOKEN`
- Redis: password required
- PostgreSQL: strong generated password

## Secrets

- Generated automatically on install
- Stored in `.env.production` (chmod 600)
- Never committed to Git
- Never printed to terminal or logs
- DKIM private keys: mode 600, owned by opendkim

## Mail Security

- **No open relay** — Postfix rejects unauthorized destinations
- DKIM signing on all outbound mail
- SPF and DMARC DNS records provided
- TLS for SMTP and HTTPS

## SSH

- Root password login disabled (when authorized_keys present)
- Password auth disabled only after key verification
- MaxAuthTries: 3
- Fail2Ban on SSH and Postfix

## Application

- Helmet.js security headers
- Input validation (class-validator)
- Idempotency keys prevent duplicate sends
- Structured logging without secrets

## Audit Checklist

Run before going live:

```bash
sudo python3 setup.py verify
sudo python3 setup.py doctor
```

Manual checks:

- [ ] No `.env.production` in Git
- [ ] PostgreSQL not reachable from internet
- [ ] Redis not reachable from internet
- [ ] Postfix relay test passes
- [ ] PTR record matches SMTP hostname
- [ ] DKIM DNS record published
- [ ] SPF single record only
- [ ] TLS certificates valid

## Reporting Issues

Do not commit security findings to public issues with exploit details.
Contact the repository maintainers directly.
