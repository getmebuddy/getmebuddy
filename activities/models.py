from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Activity(models.Model):
    STATUS_OPEN = 'open'
    STATUS_FULL = 'full'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_OPEN, _('Open')),
        (STATUS_FULL, _('Full')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_COMPLETED, _('Completed')),
    ]

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosted_activities',
    )
    title = models.CharField(_('title'), max_length=255)
    category = models.CharField(_('category'), max_length=100, blank=True, default='')
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2, default=0)
    latitude = models.FloatField(_('latitude'))
    longitude = models.FloatField(_('longitude'))
    scheduled_at = models.DateTimeField(_('scheduled at'))
    status = models.CharField(
        _('status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.title} ({self.status})"
