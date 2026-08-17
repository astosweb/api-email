# Mail Infrastructure

## Architecture

```
NestJS API
     ↓
Redis / BullMQ (email-send queue)
     ↓
Email Worker (nodemailer)
     ↓
Postfix (host, port 25)
     ↓
OpenDKIM (milter, port 8891)
     ↓
Internet
```

SMTP delivery is **never** implemented inside NestJS. The worker hands off to Postfix.

## Postfix Security

- `smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination`
- `mynetworks` limited to localhost and Docker private ranges
- No open relay — verified by `setup.py verify` and `setup.py doctor`

## DKIM

- Selector: `apiemail`
- Keys: `/etc/opendkim/keys/<domain>/`
- Private key permissions: 600
- Keys are **never** committed to Git or printed in logs

DNS record format:

```
Name:  apiemail._domainkey.example.com
Type:  TXT
Value: v=DKIM1; k=rsa; p=...
```

## SPF

Single SPF record (do not create duplicates):

```
v=spf1 ip4:<PUBLIC_IP> mx -all
```

## DMARC

Initial monitoring policy:

```
v=DMARC1; p=none; rua=mailto:admin@example.com; pct=100
```

## TLS

SMTP TLS via Postfix (`smtpd_tls_security_level = may`).
HTTPS via Let's Encrypt + Nginx for API and Web.

## Monitoring

- Postfix queue: `postqueue -p`
- Deferred queue warnings in monitor script
- Mail logs: `/var/log/mail.log`

## Port 25

DigitalOcean may block port 25 on new accounts. Request unblock via support ticket.
The installer warns but does not fail if port 25 is unavailable.

## PTR / rDNS

Must be configured in DigitalOcean control panel:

```
<PUBLIC_IP> → smtp.example.com
```

Cannot be set from inside the Droplet.
