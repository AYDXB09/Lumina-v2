"""
Resend email provider — https://resend.com
Used for transactional email: parent consent, reports, notifications.
"""

import resend
from providers.email.base import EmailProvider, EmailMessage
from config import config


class ResendEmailProvider(EmailProvider):

    def __init__(self):
        resend.api_key = config.RESEND_API_KEY

    async def send(self, message: EmailMessage) -> str:
        params: resend.Emails.SendParams = {
            "from": f"{message.from_name} <{message.from_email}>",
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
        }
        if message.text:
            params["text"] = message.text
        if message.reply_to:
            params["reply_to"] = message.reply_to

        result = resend.Emails.send(params)
        return result["id"]
