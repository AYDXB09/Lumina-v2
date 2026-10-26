"""Email provider factory."""

from functools import lru_cache
from providers.email.base import EmailProvider
from config import config


@lru_cache(maxsize=1)
def get_email_provider() -> EmailProvider:
    # Gmail SMTP is interim — used until a Resend account + verified sending
    # domain exist. Prefer it whenever configured; falls back to Resend
    # otherwise. Same EmailProvider interface either way — no call-site changes.
    if config.GMAIL_ADDRESS and config.GMAIL_APP_PASSWORD:
        from providers.email.gmail_smtp import GmailSMTPProvider
        return GmailSMTPProvider()

    from providers.email.resend_email import ResendEmailProvider
    return ResendEmailProvider()
