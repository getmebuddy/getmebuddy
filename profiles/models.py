from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Interest(models.Model):
    """Model for user interests/hobbies categories"""
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True, null=True)
    
    def __str__(self):
        return self.name


class InterestChoice(models.Model):
    """Specific interest choices within a category"""
    interest = models.ForeignKey(
        Interest,
        on_delete=models.CASCADE,
        related_name='choices',
    )
    name = models.CharField(_('name'), max_length=100)
    
    def __str__(self):
        return f"{self.interest.name}: {self.name}"


class UserProfile(models.Model):
    """Extended profile information for users"""
    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'
    GENDER_OTHER = 'other'
    GENDER_PREFER_NOT_TO_SAY = 'prefer_not_to_say'
    
    GENDER_CHOICES = [
        (GENDER_MALE, _('Male')),
        (GENDER_FEMALE, _('Female')),
        (GENDER_OTHER, _('Other')),
        (GENDER_PREFER_NOT_TO_SAY, _('Prefer not to say')),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    bio = models.TextField(_('bio'), blank=True, null=True)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=GENDER_CHOICES,
        default=GENDER_PREFER_NOT_TO_SAY,
    )
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pictures/',
        blank=True,
        null=True,
    )
    location = models.CharField(_('location'), max_length=255, blank=True, null=True)
    latitude = models.FloatField(_('latitude'), blank=True, null=True)
    longitude = models.FloatField(_('longitude'), blank=True, null=True)
    interests = models.ManyToManyField(
        InterestChoice,
        related_name='users',
        blank=True,
    )
    max_distance_preference = models.PositiveIntegerField(
        _('maximum distance preference (km)'), 
        default=50
    )
    is_profile_complete = models.BooleanField(_('profile complete'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.email}"


class Availability(models.Model):
    """User availability preferences for buddy matching"""
    DAY_CHOICES = [
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday')),
    ]
    
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    day_of_week = models.IntegerField(_('day of week'), choices=DAY_CHOICES)
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    
    class Meta:
        unique_together = ('profile', 'day_of_week', 'start_time', 'end_time')
        verbose_name_plural = 'availabilities'
    
    def __str__(self):
        return f"{self.profile.user.email} - {self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"

