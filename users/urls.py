from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .auth_views import MeView, PushTokenView
from safety.views import BlockedUserView, BlockedListView

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('me', MeView.as_view(), name='users-me'),
    path('me/push-token', PushTokenView.as_view(), name='users-push-token'),
    path('me/blocked', BlockedListView.as_view(), name='users-blocked-list'),
    path('<int:pk>/block', BlockedUserView.as_view(), name='users-block'),
    path('', include(router.urls)),
]
