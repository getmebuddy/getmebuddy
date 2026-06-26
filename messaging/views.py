from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from users.push import notify_new_message


class ConversationListView(APIView):
    """GET /api/chats/ — inbox for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        convs = (
            Conversation.objects
            .filter(participants=request.user, is_active=True)
            .prefetch_related('participants', 'messages')
            .order_by('-updated_at')
        )
        return Response(ConversationSerializer(convs, many=True, context={'request': request}).data)


class MessageListCreateView(APIView):
    """
    GET  /api/chats/{id}/messages  — ordered message history
    POST /api/chats/{id}/messages  — send a message; also broadcasts via Channels
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_conversation(self, pk, user):
        conv = get_object_or_404(Conversation, pk=pk, is_active=True)
        if not conv.participants.filter(pk=user.pk).exists():
            return None
        return conv

    def get(self, request, pk):
        conv = self._get_conversation(pk, request.user)
        if conv is None:
            return Response({'detail': 'Not found or not a participant.'}, status=status.HTTP_404_NOT_FOUND)
        msgs = conv.messages.select_related('sender').order_by('created_at')
        return Response(MessageSerializer(msgs, many=True).data)

    def post(self, request, pk):
        conv = self._get_conversation(pk, request.user)
        if conv is None:
            return Response({'detail': 'Not found or not a participant.'}, status=status.HTTP_404_NOT_FOUND)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': 'content is required.'}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(conversation=conv, sender=request.user, content=content)

        # Broadcast to any connected WebSocket clients in this conversation group.
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conv.pk}',
                    {
                        'type': 'chat_message',
                        'message': content,
                        'sender_id': request.user.pk,
                        'sender_name': request.user.full_name or request.user.email,
                        'message_id': msg.pk,
                        'timestamp': msg.created_at.isoformat(),
                    }
                )
        except Exception:
            # Channel layer may not be running in dev/test — REST still works.
            pass

        try:
            notify_new_message(msg)
        except Exception:
            pass

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
