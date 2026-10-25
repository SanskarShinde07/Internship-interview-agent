"""Transactional email via Resend (docs/BLUEPRINT.md §21 follow-up).
Only used for password-reset links - there is no other outbound email in
this app. A missing API key is treated as "email sending is disabled" (not
an error) so local development works without a Resend account: the reset
link still gets generated and logged, just never delivered.
"""

import logging

import resend

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        # warning, not info: this is the only way to see the link in local
        # dev without a Resend account, and Python's default logging config
        # suppresses INFO.
        logger.warning("RESEND_API_KEY not set - skipping email; reset link: %s", reset_link)
        return

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to_email],
                "subject": "Reset your InterVue AI password",
                "html": (
                    "<p>Someone requested a password reset for this InterVue AI account. "
                    "If that was you, click the link below - it expires in "
                    f"{settings.password_reset_token_expire_minutes} minutes.</p>"
                    f'<p><a href="{reset_link}">{reset_link}</a></p>'
                    "<p>If you didn't request this, you can safely ignore this email.</p>"
                ),
            }
        )
    except Exception:
        # Never let an email-provider outage break the forgot-password
        # flow's response to the candidate; the reset link is already
        # generated and valid, it just won't have reached them this way.
        logger.exception("Failed to send password reset email to %s", to_email)
