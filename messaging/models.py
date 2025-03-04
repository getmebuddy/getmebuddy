from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    """A conversation between two users"""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    is_active = models.BooleanField(_('is active'), default=True)
    
    def __str__(self):
        return f"Conversation {self.id}"


class Message(models.Model):
    """A message in a conversation"""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    content = models.TextField(_('content'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    is_read = models.BooleanField(_('is read'), default=False)
    read_at = models.DateTimeField(_('read at'), blank=True, null=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} at {self.created_at}"


class Attachment(models.Model):
    """File attachment for a message"""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(_('file'), upload_to='message_attachments/')
    file_name = models.CharField(_('file name'), max_length=255)
    file_size = models.PositiveIntegerField(_('file size'), help_text=_('Size in bytes'))
    content_type = models.CharField(_('content type'), max_length=100)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    def __str__(self):
        return f"Attachment: {self.file_name}"
