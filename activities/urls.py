from django.urls import path
from .views import ActivityListCreateView, ActivityDetailView

urlpatterns = [
    path('', ActivityListCreateView.as_view(), name='activity-list-create'),
    path('<int:pk>', ActivityDetailView.as_view(), name='activity-detail'),
]
