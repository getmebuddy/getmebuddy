from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Orbit client auth contract
    path('api/auth/', include('users.auth_urls')),
    path('api/auth/refresh', TokenRefreshView.as_view(), name='token-refresh'),

    # User profile + push-token
    path('api/users/', include('users.urls')),

    path('api/activities/', include('activities.urls')),

    path('api/payments/', include('monetization.payment_urls')),
    path('api/bookings', include('monetization.booking_urls')),

    # Messaging REST (Epic 4)
    # path('api/chats/', include('messaging.urls')),

    # Verification (Epic 5)
    # path('api/verification', include('users.verification_urls')),

    # Safety: reports + block
    path('api/reports', include('safety.urls')),

    # Legacy / internal
    path('api/profiles/', include('profiles.urls')),
    path('api/matching/', include('matching.urls')),
    path('api/engagement/', include('engagement.urls')),
    path('api/monetization/', include('monetization.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
