"""Email provider factory."""

from functools import lru_cache
from providers.email.base import EmailProvider


@lru_cache(maxsize=1)
def get_email_provider() -> EmailProvider:
    # Resend is the only backend for now (AWS SES excluded — production access issues)
    from providers.email.resend_email import ResendEmailProvider
    return ResendEmailProvider()
