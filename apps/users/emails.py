from django.conf import settings
from apps.common.services.mail import MailService


def send_verification_email(user, code: str):
    MailService.send_mail(
        to_email=user.email,
        subject=f"Du hast dich bei Command-Vault registriert",
        template_name="emails/users/verify.html",
        context={"code": code},
        user=user
    )


def send_password_reset_email(user, reset_token: str):
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://sidequest.de')
    MailService.send_mail(
        to_email=user.email,
        subject="Passwort zurücksetzen",
        template_name="emails/users/password_reset.html",
        context={"reset_url": f"{frontend_url}/reset?token={reset_token}"},
        user=user
    )

