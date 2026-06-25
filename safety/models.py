from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class BlockedUser(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocking',
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.email} blocked {self.blocked.email}"


class Report(models.Model):
    STATUS_RECEIVED = 'received'
    STATUS_REVIEWING = 'reviewing'
    STATUS_RESOLVED = 'resolved'
    STATUS_DISMISSED = 'dismissed'
    STATUS_CHOICES = [
        (STATUS_RECEIVED, _('Received')),
        (STATUS_REVIEWING, _('Reviewing')),
        (STATUS_RESOLVED, _('Resolved')),
        (STATUS_DISMISSED, _('Dismissed')),
    ]

    TARGET_USER = 'user'
    TARGET_ACTIVITY = 'activity'
    TARGET_MESSAGE = 'message'
    TARGET_CHOICES = [
        (TARGET_USER, _('User')),
        (TARGET_ACTIVITY, _('Activity')),
        (TARGET_MESSAGE, _('Message')),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='filed_reports',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_against',
    )
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default=TARGET_USER)
    target_id = models.CharField(max_length=255, blank=True, default='')
    reason = models.CharField(max_length=255)
    details = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.email} ({self.status})"
