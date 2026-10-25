from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from datetime import timedelta
from .models import User, EmailVerificationCode, generate_otp_code
from .emails import (
    send_password_reset_email,
    send_verification_email,
)

def send_password_reset_for_user(*, user: User) -> str:
    """Erstellt ein Passwort-Reset-Token und versendet die entsprechende E-Mail."""
    token = default_token_generator.make_token(user)
    send_password_reset_email(user=user, reset_token=token)
    return token


def send_user_verification_code(*, user: User) -> str:
    """Erstellt oder aktualisiert den Verifizierungscode für den User und sendet die E-Mail."""
    verification, created = EmailVerificationCode.objects.get_or_create(user=user)

    if not created:
        verification.code = generate_otp_code()
        verification.attempts = 0
        verification.created_at = timezone.now()

    verification.save()

    send_verification_email(user=user, code=verification.code)
    return verification.code

def resend_verification_code(*, email: str) -> None:
    """Sendet einen neuen OTP-Code, falls der User existiert und unbestätigt ist."""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return

    if user.is_verified:
        return

    verification, created = EmailVerificationCode.objects.get_or_create(user=user)

    if not created:
        cooldown = timedelta(seconds=60)
        if timezone.now() < verification.created_at + cooldown:
            return

        verification.code = generate_otp_code()
        verification.attempts = 0
        verification.created_at = timezone.now()
        verification.save()

    send_verification_email(user=user, code=verification.code)