from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Client contract URL — used by the Orbit mobile app.
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    # Legacy URL — kept for backward compat.
    re_path(r'ws/conversations/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
