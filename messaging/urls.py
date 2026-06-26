from django.urls import path
from .views import ConversationListView, MessageListCreateView

urlpatterns = [
    path('', ConversationListView.as_view(), name='chat-list'),
    path('<int:pk>/messages', MessageListCreateView.as_view(), name='chat-messages'),
]
