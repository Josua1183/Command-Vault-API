import secrets
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


def generate_otp_code(length=6):
    return ''.join(secrets.choice('0123456789') for _ in range(length))


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Die E-Mail-Adresse muss angegeben werden.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser muss is_staff=True haben.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser muss is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Interests(models.TextChoices):
        SEARCHINGFORJOBS = 'searching_for_jobs', 'Suche nach Jobs'
        SEARCHINGFORHELP = 'searching_for_help', 'Suche nach Hilfe'
        ALL = 'all', 'Alle'

    email = models.EmailField('E-Mail-Adresse', unique=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class EmailVerificationCode(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='verification_code'
    )
    code = models.CharField(max_length=6, default=generate_otp_code)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)

    def is_valid(self) -> bool:
        """Code ist 15 Minuten gültig und erlaubt maximal 5 Fehlversuche."""
        is_not_expired = timezone.now() <= self.created_at + timedelta(minutes=15)
        has_attempts_left = self.attempts < 5
        return is_not_expired and has_attempts_left

    def __str__(self):
        return f"Code {self.code} für {self.user.email}"
