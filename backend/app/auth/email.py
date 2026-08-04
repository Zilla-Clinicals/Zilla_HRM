"""Transactional email. Two providers:

- "console" (default for local dev): logs the link to stdout; no network.
- "resend": sends via the Resend SDK.
"""

import logging

from app.config import settings

logger = logging.getLogger("hrm.email")


def _send(to: str, subject: str, html: str) -> bool:
    """Best-effort send. Returns True on success. Never raises — a mail failure
    must not break the action that triggered it (e.g. creating an invite)."""
    if settings.email_provider == "resend" and settings.resend_api_key:
        try:
            import resend

            resend.api_key = settings.resend_api_key
            resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
            logger.info("[email:resend] sent to %s (%s)", to, subject)
            return True
        except Exception as exc:
            # Common cause without a verified domain: Resend only allows sending
            # to your own account email until you verify a sending domain.
            logger.error("[email:resend] FAILED to %s: %s", to, exc)
            return False

    logger.info("[email:console] To=%s | %s\n%s", to, subject, html)
    print(
        f"\n=== EMAIL (console) ===\nTo: {to}\nSubject: {subject}\n"
        f"{html}\n=======================\n"
    )
    return True


def send_invite_email(to: str, raw_token: str) -> bool:
    link = f"{settings.app_base_url}/accept-invite?token={raw_token}"
    html = (
        f"<p>You've been invited to Zilla Clinicals HRM.</p>"
        f'<p><a href="{link}">Accept your invitation</a> to set a password.</p>'
        f"<p>Or paste this link: {link}</p>"
        f"<p>This link expires in 7 days.</p>"
    )
    return _send(to, "You're invited to Zilla Clinicals HRM", html)


def send_reset_email(to: str, raw_token: str) -> bool:
    link = f"{settings.app_base_url}/reset-password?token={raw_token}"
    html = (
        f"<p>We received a request to reset your Zilla Clinicals HRM password.</p>"
        f'<p><a href="{link}">Reset your password</a>.</p>'
        f"<p>Or paste this link: {link}</p>"
        f"<p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>"
    )
    return _send(to, "Reset your Zilla Clinicals HRM password", html)
