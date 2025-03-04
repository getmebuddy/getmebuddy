# In matching/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'matches', views.MatchViewSet, basename='match')
router.register(r'preferences', views.MatchPreferenceViewSet, basename='match-preference')

urlpatterns = [
    path('', include(router.urls)),
]