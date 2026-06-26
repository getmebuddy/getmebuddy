from rest_framework import serializers
from .models import Conversation, Message
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    # Normalise FK names to what the client expects.
    chat_id = serializers.IntegerField(source='conversation_id', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'chat_id', 'sender_id', 'content', 'created_at']
        read_only_fields = ['id', 'chat_id', 'sender_id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """
    Shape the server sends to the client for the inbox list.
    The client expects: {id, name, hostId, message, time, avatar, unread}
    """
    name = serializers.SerializerMethodField()
    hostId = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'name', 'hostId', 'message', 'time', 'avatar', 'unread']

    def _other(self, obj):
        """Return the other participant (not the requesting user)."""
        request_user = self.context['request'].user
        return obj.participants.exclude(pk=request_user.pk).first()

    def get_name(self, obj):
        other = self._other(obj)
        return other.full_name or other.email if other else 'Unknown'

    def get_hostId(self, obj):
        other = self._other(obj)
        return other.pk if other else None

    def get_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        return last.content if last else 'Start chatting!'

    def get_time(self, obj):
        last = obj.messages.order_by('-created_at').first()
        return last.created_at.isoformat() if last else obj.created_at.isoformat()

    def get_avatar(self, obj):
        other = self._other(obj)
        return getattr(other, 'avatar_url', '') if other else ''

    def get_unread(self, obj):
        request_user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=request_user).count()
