from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RegisterView, UserViewSet

router = DefaultRouter()
router.register(r"", UserViewSet)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("", include(router.urls)),
]
