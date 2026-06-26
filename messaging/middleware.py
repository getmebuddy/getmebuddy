"""
JWT authentication middleware for Django Channels WebSocket connections.

Reads the access token from the `?token=` query parameter, validates it
with SimpleJWT, and injects the authenticated user into scope['user'].
This is needed because mobile clients can't set custom headers on WebSocket
upgrades — the query param is the standard workaround for that constraint.
"""
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


@database_sync_to_async
def _get_user_from_token(token_str):
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return User.objects.get(pk=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """ASGI middleware that validates ?token= on WebSocket connections."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            qs = parse_qs(scope.get('query_string', b'').decode())
            token_str = qs.get('token', [None])[0]
            scope['user'] = await _get_user_from_token(token_str) if token_str else AnonymousUser()
        return await self.app(scope, receive, send)
