from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager for User model with email as the unique identifier"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email as the unique identifier instead of username
    """
    SIGNUP_EMAIL = 'email'
    SIGNUP_GOOGLE = 'google'
    SIGNUP_APPLE = 'apple'
    SIGNUP_FACEBOOK = 'facebook'
    
    SIGNUP_CHOICES = [
        (SIGNUP_EMAIL, _('Email')),
        (SIGNUP_GOOGLE, _('Google')),
        (SIGNUP_APPLE, _('Apple')),
        (SIGNUP_FACEBOOK, _('Facebook')),
    ]
    
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    signup_method = models.CharField(
        _('signup method'),
        max_length=20,
        choices=SIGNUP_CHOICES,
        default=SIGNUP_EMAIL,
    )
    firebase_uid = models.CharField(
        _('Firebase UID'),
        max_length=128,
        blank=True,
        null=True,
        unique=True,
    )
    phone_number = models.CharField(_('phone number'), max_length=20, blank=True, null=True)
    is_phone_verified = models.BooleanField(_('phone verified'), default=False)
    is_identity_verified = models.BooleanField(_('identity verified'), default=False)
    verification_provider = models.CharField(
        _('verification provider'),
        max_length=50,
        blank=True,
        null=True,
    )
    last_login_ip = models.GenericIPAddressField(_('last login IP'), blank=True, null=True)
    
    # Account status
    is_suspended = models.BooleanField(_('suspended'), default=False)
    suspension_reason = models.CharField(_('suspension reason'), max_length=255, blank=True, null=True)
    suspension_date = models.DateTimeField(_('suspension date'), blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
    
    @property
    def is_verified(self):
        """Check if the user is verified by any method."""
        return self.is_identity_verified