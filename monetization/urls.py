from django.urls import path
from .views import CreatePaymentIntentView, StripeWebhookView, BookingListCreateView

# Kept for the legacy path('api/monetization/', include('monetization.urls')) route
urlpatterns = []
