"""Mail infrastructure orchestration."""

from __future__ import annotations

from setup.utils import SetupContext, log_info, log_warn
from setup import postfix, dkim, tls


def configure_mail(ctx: SetupContext) -> None:
    postfix.configure_postfix(ctx)
    dkim.configure_dkim(ctx)
    tls.configure_smtp_tls(ctx)
    _print_dns_records(ctx)


def _print_dns_records(ctx: SetupContext) -> None:
    from setup import dkim as dkim_mod

    dkim_record = dkim_mod.get_dkim_dns_record(ctx)
    spf = f'v=spf1 ip4:{ctx.public_ip} mx -all' if ctx.public_ip else f'v=spf1 mx -all'
    dmarc = f'v=DMARC1; p=none; rua=mailto:{ctx.admin_email}; pct=100'

    print('\n' + '─' * 46)
    print('REQUIRED DNS RECORDS')
    print('─' * 46)

    for label, name, rtype, value in [
        ('A (API)', ctx.api_domain, 'A', ctx.public_ip),
        ('A (Web)', ctx.web_domain, 'A', ctx.public_ip),
        ('A (SMTP)', ctx.smtp_hostname, 'A', ctx.public_ip),
        ('MX', ctx.domain, 'MX', f'10 {ctx.smtp_hostname}'),
        ('SPF', ctx.domain, 'TXT', spf),
        ('DMARC', f'_dmarc.{ctx.domain}', 'TXT', dmarc),
    ]:
        print(f'\n{label}')
        print(f'  Name:  {name}')
        print(f'  Type:  {rtype}')
        print(f'  Value: {value}')

    if dkim_record:
        print('\nDKIM')
        print(f'  Name:  {dkim_record["name"]}')
        print('  Type:  TXT')
        print(f'  Value: {dkim_record["value"]}')

    print('\nPTR / rDNS (configure in DigitalOcean control panel):')
    print(f'  {ctx.public_ip} → {ctx.smtp_hostname}')
    log_warn('Port 25 may be blocked by default on new DigitalOcean accounts', ctx)
    log_warn('Request SMTP port unblock via DigitalOcean support if needed', ctx)
