import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'getmebuddy.settings')

django_asgi_app = get_asgi_application()

# Import after Django setup to avoid app registry not ready error.
from messaging.routing import websocket_urlpatterns  # noqa: E402
from messaging.middleware import JWTAuthMiddleware    # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
