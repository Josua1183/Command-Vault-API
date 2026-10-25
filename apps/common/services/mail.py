# apps/common/services/mail.py
import re
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from apps.common.models import EmailLog

logger = logging.getLogger(__name__)


class MailService:
    @staticmethod
    def send_mail(
        to_email: str,
        subject: str,
        template_name: str,
        context: dict | None = None,
        user=None
    ) -> bool:
        """
        Universelle Render- und Versand-Engine für alle Apps.
        """
        # 1. Defaults mit übergebenem Context mergen
        ctx = {
            'project_name': 'Sidequest',
            'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
            'user': user,
            **(context or {})
        }

        # 2. Template rendern & HTML bereinigen
        try:
            html_body = render_to_string(template_name, ctx)
            plain_body = strip_tags(html_body)
        except Exception as e:
            logger.error(f"Fehler beim Rendern des E-Mail-Templates '{template_name}': {e}")
            return False

        # 3. Tokens für das Logging zensieren
        safe_content = re.sub(r'token=[^&\s"\'>]+', 'token=[REDACTED]', html_body)

        # 4. E-Mail vorbereiten
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sidequest.de')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_body, "text/html")

        # 5. Senden & Loggen (mit Fehlerbehandlung)
        try:
            msg.send(fail_silently=False)
            EmailLog.objects.create(
                email=to_email,
                subject=subject,
                content=safe_content,
                user=user,
                status='sent'
            )
            return True
        except Exception as e:
            logger.error(f"E-Mail an '{to_email}' konnte nicht gesendet werden. Fehler: {e}")
            EmailLog.objects.create(
                email=to_email,
                subject=subject,
                content=safe_content,
                user=user,
                status='failed',
                error_message=str(e)
            )
            return False
