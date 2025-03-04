from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Match(models.Model):
    """Record of a match between two users"""
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_ACCEPTED, _('Accepted')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_EXPIRED, _('Expired')),
    ]
    
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_matches',
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_matches',
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    matched_at = models.DateTimeField(_('matched at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    expiration_date = models.DateTimeField(_('expiration date'), blank=True, null=True)
    interests_similarity_score = models.FloatField(_('interests similarity score'), default=0.0)
    distance_score = models.FloatField(_('distance score'), default=0.0)
    availability_score = models.FloatField(_('availability score'), default=0.0)
    total_match_score = models.FloatField(_('total match score'), default=0.0)
    
    class Meta:
        unique_together = ('initiator', 'responder')
        verbose_name_plural = 'matches'
    
    def __str__(self):
        return f"Match between {self.initiator.email} and {self.responder.email} ({self.status})"


class MatchPreference(models.Model):
    """User preferences for matching algorithm"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_preferences',
    )
    min_age = models.PositiveIntegerField(_('minimum age'), default=18)
    max_age = models.PositiveIntegerField(_('maximum age'), default=100)
    preferred_genders = models.JSONField(_('preferred genders'), default=list)
    interest_importance = models.FloatField(
        _('interest importance weight'),
        default=0.5,
        help_text=_('Weight from 0 to 1, where 1 is most important'),
    )
    distance_importance = models.FloatField(
        _('distance importance weight'),
        default=0.3,
        help_text=_('Weight from 0 to 1, where 1 is most important'),
    )
    availability_importance = models.FloatField(
        _('availability importance weight'),
        default=0.2,
        help_text=_('Weight from 0 to 1, where 1 is most important'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    def __str__(self):
        return f"Match preferences for {self.user.email}"
