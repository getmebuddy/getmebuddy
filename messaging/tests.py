import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(email='a@x.com', password='pass', full_name='Alice')


@pytest.fixture
def user_b(db):
    return User.objects.create_user(email='b@x.com', password='pass', full_name='Bob')


@pytest.fixture
def auth_client_a(client, user_a):
    resp = client.post('/api/auth/login', {'email': 'a@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def conversation(db, user_a, user_b):
    conv = Conversation.objects.create()
    conv.participants.set([user_a, user_b])
    return conv


@pytest.fixture
def message(db, conversation, user_b):
    return Message.objects.create(conversation=conversation, sender=user_b, content='Hey Alice!')


# ── Conversation list ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_chats_returns_conversations(auth_client_a, conversation, user_b):
    resp = auth_client_a.get('/api/chats/')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['id'] == conversation.pk


@pytest.mark.django_db
def test_list_chats_shape(auth_client_a, conversation, message):
    resp = auth_client_a.get('/api/chats/')
    conv = resp.data[0]
    for field in ('id', 'name', 'hostId', 'message', 'time', 'avatar', 'unread'):
        assert field in conv, f"Missing field: {field}"


@pytest.mark.django_db
def test_list_chats_shows_other_participant_name(auth_client_a, conversation, user_b):
    resp = auth_client_a.get('/api/chats/')
    assert resp.data[0]['name'] == user_b.full_name


@pytest.mark.django_db
def test_list_chats_shows_last_message(auth_client_a, conversation, message):
    resp = auth_client_a.get('/api/chats/')
    assert resp.data[0]['message'] == 'Hey Alice!'


@pytest.mark.django_db
def test_list_chats_unread_count(auth_client_a, conversation, message):
    # message is from user_b (not Alice), and is_read=False → unread count 1
    resp = auth_client_a.get('/api/chats/')
    assert resp.data[0]['unread'] == 1


@pytest.mark.django_db
def test_list_chats_requires_auth(client, conversation):
    resp = client.get('/api/chats/')
    assert resp.status_code == 401


# ── Message list ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_messages(auth_client_a, conversation, message):
    resp = auth_client_a.get(f'/api/chats/{conversation.pk}/messages')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['content'] == 'Hey Alice!'


@pytest.mark.django_db
def test_list_messages_shape(auth_client_a, conversation, message):
    resp = auth_client_a.get(f'/api/chats/{conversation.pk}/messages')
    msg = resp.data[0]
    for field in ('id', 'chat_id', 'sender_id', 'content', 'created_at'):
        assert field in msg, f"Missing field: {field}"


@pytest.mark.django_db
def test_list_messages_non_participant_denied(client, db, conversation):
    outsider = User.objects.create_user(email='c@x.com', password='pass', full_name='Carol')
    resp_login = client.post('/api/auth/login', {'email': 'c@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp_login.data['access']}")
    resp = client.get(f'/api/chats/{conversation.pk}/messages')
    assert resp.status_code == 404


# ── Send message ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_send_message(auth_client_a, conversation):
    with patch('messaging.views.get_channel_layer', return_value=None):
        resp = auth_client_a.post(
            f'/api/chats/{conversation.pk}/messages',
            {'content': 'Hello Bob!'},
            format='json',
        )
    assert resp.status_code == 201
    assert resp.data['content'] == 'Hello Bob!'
    assert Message.objects.filter(conversation=conversation, content='Hello Bob!').exists()


@pytest.mark.django_db
def test_send_message_normalised_shape(auth_client_a, conversation, user_a):
    with patch('messaging.views.get_channel_layer', return_value=None):
        resp = auth_client_a.post(
            f'/api/chats/{conversation.pk}/messages',
            {'content': 'Hi'},
            format='json',
        )
    assert resp.data['sender_id'] == user_a.pk
    assert resp.data['chat_id'] == conversation.pk


@pytest.mark.django_db
def test_send_empty_content_rejected(auth_client_a, conversation):
    with patch('messaging.views.get_channel_layer', return_value=None):
        resp = auth_client_a.post(
            f'/api/chats/{conversation.pk}/messages',
            {'content': ''},
            format='json',
        )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_send_message_non_participant_denied(client, db, conversation):
    outsider = User.objects.create_user(email='d@x.com', password='pass', full_name='Dave')
    resp_login = client.post('/api/auth/login', {'email': 'd@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp_login.data['access']}")
    with patch('messaging.views.get_channel_layer', return_value=None):
        resp = client.post(
            f'/api/chats/{conversation.pk}/messages',
            {'content': 'Intruding!'},
            format='json',
        )
    assert resp.status_code == 404


# ── JWT middleware unit test ───────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_jwt_middleware_valid_token(user_a):
    from rest_framework_simplejwt.tokens import AccessToken
    from messaging.middleware import JWTAuthMiddleware
    from urllib.parse import urlencode

    token = str(AccessToken.for_user(user_a))
    qs = urlencode({'token': token}).encode()

    scope = {'type': 'websocket', 'query_string': qs}
    received_scope = {}

    async def fake_app(s, receive, send):
        received_scope.update(s)

    middleware = JWTAuthMiddleware(fake_app)
    await middleware(scope, None, None)

    assert received_scope['user'].pk == user_a.pk


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_jwt_middleware_invalid_token():
    from messaging.middleware import JWTAuthMiddleware
    from django.contrib.auth.models import AnonymousUser

    scope = {'type': 'websocket', 'query_string': b'token=bad_token'}
    received_scope = {}

    async def fake_app(s, receive, send):
        received_scope.update(s)

    middleware = JWTAuthMiddleware(fake_app)
    await middleware(scope, None, None)

    assert isinstance(received_scope['user'], AnonymousUser)
