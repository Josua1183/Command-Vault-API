# apps/common/models.py
from django.db import models
from django.conf import settings

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('sent', 'Gesendet'),
        ('failed', 'Fehlgeschlagen'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='email_logs'
    )
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} an {self.email} ({self.status})"
