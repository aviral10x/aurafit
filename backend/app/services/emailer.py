from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings


def email_delivery_configured() -> bool:
    return bool(settings.smtp_host and (not settings.smtp_username or settings.smtp_password))


def _send_message(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls(context=context)
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def send_otp_email(email: str, code: str) -> str:
    """Send an OTP email when SMTP is configured; otherwise log for local dev."""
    if not email_delivery_configured():
        if settings.auth_require_email_delivery or not settings.auth_dev_return_otp:
            raise RuntimeError("SMTP is not configured. Add Resend/SMTP credentials before disabling dev OTP.")
        print(f"[DEV OTP] AuraFit login code for {email}: {code}")
        return "dev_console"

    message = EmailMessage()
    message["Subject"] = "Your AuraFit login code"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "Your AuraFit login code is:",
                "",
                code,
                "",
                f"This code expires in {settings.auth_otp_ttl_minutes} minutes.",
                "If you did not request this, you can ignore this email.",
            ]
        )
    )

    _send_message(message)
    return "email"


def send_result_email(email: str, profile_name: str, result_url: str) -> str:
    """Send the completed result link; logs locally when SMTP is not configured."""
    if not email_delivery_configured():
        print(f"[DEV EMAIL] AuraFit result for {email} ({profile_name}): {result_url}")
        return "dev_console"

    message = EmailMessage()
    message["Subject"] = "Your AuraFit style analysis is ready"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Your AuraFit result for {profile_name} is ready:",
                "",
                result_url,
                "",
                "Open this link anytime from your saved AuraFit ID.",
            ]
        )
    )

    _send_message(message)
    return "email"
