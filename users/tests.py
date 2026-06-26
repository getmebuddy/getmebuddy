import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def registered_user(db):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        full_name='Test User',
        is_buddy=False,
        verification_status='none',
    )


@pytest.fixture
def auth_client(client, registered_user):
    resp = client.post('/api/auth/login', {'email': 'test@example.com', 'password': 'testpass123'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client, resp.data


# --- Registration ---

@pytest.mark.django_db
def test_register_returns_tokens_and_user(client):
    resp = client.post('/api/auth/register', {
        'email': 'new@example.com', 'password': 'securepass1', 'full_name': 'New User', 'is_buddy': False,
    }, format='json')
    assert resp.status_code == 201
    assert 'access' in resp.data
    assert 'refresh' in resp.data
    assert resp.data['user']['email'] == 'new@example.com'
    assert resp.data['user']['full_name'] == 'New User'
    assert resp.data['user']['is_buddy'] is False
    assert resp.data['user']['verification_status'] == 'none'


@pytest.mark.django_db
def test_register_buddy_sets_pending(client):
    resp = client.post('/api/auth/register', {
        'email': 'buddy@example.com', 'password': 'pass12345', 'full_name': 'Buddy Bob', 'is_buddy': True,
    }, format='json')
    assert resp.status_code == 201
    assert resp.data['user']['verification_status'] == 'pending'


@pytest.mark.django_db
def test_register_duplicate_email(client, registered_user):
    resp = client.post('/api/auth/register', {
        'email': 'test@example.com', 'password': 'anotherpass', 'full_name': 'Dupe', 'is_buddy': False,
    }, format='json')
    assert resp.status_code == 400


# --- Login ---

@pytest.mark.django_db
def test_login_returns_tokens_and_user(client, registered_user):
    resp = client.post('/api/auth/login', {'email': 'test@example.com', 'password': 'testpass123'}, format='json')
    assert resp.status_code == 200
    assert 'access' in resp.data
    assert 'refresh' in resp.data
    assert resp.data['user']['email'] == 'test@example.com'


@pytest.mark.django_db
def test_login_wrong_password(client, registered_user):
    resp = client.post('/api/auth/login', {'email': 'test@example.com', 'password': 'wrong'}, format='json')
    assert resp.status_code == 401


# --- Token refresh ---

@pytest.mark.django_db
def test_token_refresh(client, registered_user):
    login = client.post('/api/auth/login', {'email': 'test@example.com', 'password': 'testpass123'}, format='json')
    resp = client.post('/api/auth/refresh', {'refresh': login.data['refresh']}, format='json')
    assert resp.status_code == 200
    assert 'access' in resp.data


# --- Logout ---

@pytest.mark.django_db
def test_logout_blacklists_refresh(client, registered_user):
    login = client.post('/api/auth/login', {'email': 'test@example.com', 'password': 'testpass123'}, format='json')
    access = login.data['access']
    refresh = login.data['refresh']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    resp = client.post('/api/auth/logout', {'refresh': refresh}, format='json')
    assert resp.status_code == 204
    resp2 = client.post('/api/auth/refresh', {'refresh': refresh}, format='json')
    assert resp2.status_code == 401


# --- /api/users/me ---

@pytest.mark.django_db
def test_me_returns_user(auth_client):
    client, _ = auth_client
    resp = client.get('/api/users/me')
    assert resp.status_code == 200
    assert resp.data['email'] == 'test@example.com'


@pytest.mark.django_db
def test_me_patch_updates_full_name(auth_client):
    client, _ = auth_client
    resp = client.patch('/api/users/me', {'full_name': 'Updated Name'}, format='json')
    assert resp.status_code == 200
    assert resp.data['full_name'] == 'Updated Name'


@pytest.mark.django_db
def test_me_requires_auth(client):
    resp = client.get('/api/users/me')
    assert resp.status_code == 401


# --- Push token ---

@pytest.mark.django_db
def test_push_token_stored(auth_client):
    client, _ = auth_client
    resp = client.post('/api/users/me/push-token', {'token': 'ExponentPushToken[abc123]', 'platform': 'ios'}, format='json')
    assert resp.status_code == 200
    user = User.objects.get(email='test@example.com')
    assert user.push_token == 'ExponentPushToken[abc123]'


# --- Block / Unblock ---

@pytest.mark.django_db
def test_block_and_list_blocked(db, client):
    user1 = User.objects.create_user(email='u1@x.com', password='pass', full_name='U1')
    user2 = User.objects.create_user(email='u2@x.com', password='pass', full_name='U2')
    login = client.post('/api/auth/login', {'email': 'u1@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    resp = client.post(f'/api/users/{user2.pk}/block')
    assert resp.status_code == 204

    resp2 = client.get('/api/users/me/blocked')
    assert resp2.status_code == 200
    assert user2.pk in resp2.data


@pytest.mark.django_db
def test_unblock(db, client):
    user1 = User.objects.create_user(email='u1@x.com', password='pass', full_name='U1')
    user2 = User.objects.create_user(email='u2@x.com', password='pass', full_name='U2')
    login = client.post('/api/auth/login', {'email': 'u1@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    client.post(f'/api/users/{user2.pk}/block')
    resp = client.delete(f'/api/users/{user2.pk}/block')
    assert resp.status_code == 204

    resp2 = client.get('/api/users/me/blocked')
    assert user2.pk not in resp2.data


# --- Delete account ---

@pytest.mark.django_db
def test_delete_account(auth_client):
    client, _ = auth_client
    resp = client.delete('/api/users/me')
    assert resp.status_code == 204
    assert not User.objects.filter(email='test@example.com').exists()


# --- Verification upload ---

@pytest.mark.django_db
def test_verification_requires_auth(client):
    resp = client.post('/api/verification')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_verification_missing_files_returns_400(auth_client):
    client, _ = auth_client
    resp = client.post('/api/verification', {}, format='multipart')
    assert resp.status_code == 400
    assert 'id_document' in resp.data.get('detail', '') or 'required' in resp.data.get('detail', '')


@pytest.mark.django_db
def test_verification_upload_sets_pending(auth_client, tmp_path):
    client, _ = auth_client
    id_file = tmp_path / 'id.jpg'
    selfie_file = tmp_path / 'selfie.jpg'
    id_file.write_bytes(b'fake-id-image-data')
    selfie_file.write_bytes(b'fake-selfie-data')

    with id_file.open('rb') as idf, selfie_file.open('rb') as sf:
        resp = client.post(
            '/api/verification',
            {'id_document': idf, 'selfie': sf},
            format='multipart',
        )

    assert resp.status_code == 200
    assert resp.data['status'] == 'pending'
    user = User.objects.get(email='test@example.com')
    assert user.verification_status == 'pending'
