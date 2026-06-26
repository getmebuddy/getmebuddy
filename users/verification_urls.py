from django.urls import path
from .verification_views import VerificationView

urlpatterns = [
    path('', VerificationView.as_view(), name='verification-submit'),
]
