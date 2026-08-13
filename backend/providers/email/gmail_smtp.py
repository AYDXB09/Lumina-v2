"""
Gmail SMTP email provider — interim sender used while no Resend account/
verified domain exists yet. Sends via smtp.gmail.com using a Google
App Password (not the account's real password — generated at
myaccount.google.com/apppasswords, revocable independently).

Swap back to ResendEmailProvider in providers/email/__init__.py once
a Resend account + verified domain are set up — same EmailProvider
interface, no call-site changes needed.
"""

import aiosmtplib
from email.message import EmailMessage as MimeEmailMessage

from providers.email.base import EmailProvider, EmailMessage
from config import config


class GmailSMTPProvider(EmailProvider):

    def __init__(self):
        if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
            raise RuntimeError(
                "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set to use GmailSMTPProvider"
            )

    async def send(self, message: EmailMessage) -> str:
        msg = MimeEmailMessage()
        msg["From"] = f"{message.from_name} <{config.GMAIL_ADDRESS}>"
        msg["To"] = message.to
        msg["Subject"] = message.subject
        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        msg.set_content(message.text or "This email requires an HTML-capable client to view.")
        msg.add_alternative(message.html, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=config.GMAIL_ADDRESS,
            password=config.GMAIL_APP_PASSWORD,
        )
        # Gmail's SMTP response has no provider-side message ID to hand back —
        # unlike Resend's API, this is raw SMTP. Return the Message-Id header instead.
        return msg.get("Message-Id", "sent")
