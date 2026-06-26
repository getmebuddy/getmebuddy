import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Activity

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='host@x.com', password='pass', full_name='Host User')


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email='other@x.com', password='pass', full_name='Other User')


@pytest.fixture
def auth_client(client, user):
    resp = client.post('/api/auth/login', {'email': 'host@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def activity(db, user):
    return Activity.objects.create(
        host=user,
        title='Morning Hike',
        category='outdoors',
        price=10.00,
        latitude=37.7749,
        longitude=-122.4194,
        scheduled_at=timezone.now(),
        status='open',
    )


# --- List ---

@pytest.mark.django_db
def test_list_activities(auth_client, activity):
    resp = auth_client.get('/api/activities/')
    assert resp.status_code == 200
    assert len(resp.data) >= 1
    assert resp.data[0]['title'] == 'Morning Hike'


@pytest.mark.django_db
def test_list_requires_auth(client, activity):
    resp = client.get('/api/activities/')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_list_filter_by_category(auth_client, activity, db, user):
    Activity.objects.create(
        host=user, title='Yoga', category='wellness', price=0,
        latitude=37.0, longitude=-122.0, scheduled_at=timezone.now(),
    )
    resp = auth_client.get('/api/activities/?category=outdoors')
    assert resp.status_code == 200
    assert all(a['category'] == 'outdoors' for a in resp.data)


# --- Bbox viewport filter ---

@pytest.mark.django_db
def test_bbox_returns_activity_inside_bounds(auth_client, activity):
    # Activity is at 37.7749, -122.4194 (San Francisco)
    resp = auth_client.get('/api/activities/?bbox=-123,37,-122,38')
    assert resp.status_code == 200
    assert any(a['id'] == activity.id for a in resp.data)


@pytest.mark.django_db
def test_bbox_excludes_activity_outside_bounds(auth_client, activity):
    # Bbox is New York area — SF activity should not appear
    resp = auth_client.get('/api/activities/?bbox=-74.1,40.6,-73.9,40.8')
    assert resp.status_code == 200
    assert not any(a['id'] == activity.id for a in resp.data)


@pytest.mark.django_db
def test_malformed_bbox_returns_all(auth_client, activity):
    resp = auth_client.get('/api/activities/?bbox=bad')
    assert resp.status_code == 200  # doesn't crash, returns unfiltered


# --- Create ---

@pytest.mark.django_db
def test_create_activity(auth_client):
    payload = {
        'title': 'Evening Run',
        'category': 'fitness',
        'price': 0,
        'latitude': 37.8,
        'longitude': -122.4,
        'scheduled_at': '2026-07-01T18:00:00Z',
        'status': 'open',
    }
    resp = auth_client.post('/api/activities/', payload, format='json')
    assert resp.status_code == 201
    assert resp.data['title'] == 'Evening Run'
    assert resp.data['host_id'] is not None


@pytest.mark.django_db
def test_create_sets_host_to_current_user(auth_client, user):
    payload = {
        'title': 'Book Club',
        'category': 'social',
        'price': 5,
        'latitude': 37.5,
        'longitude': -122.0,
        'scheduled_at': '2026-08-01T10:00:00Z',
    }
    resp = auth_client.post('/api/activities/', payload, format='json')
    assert resp.status_code == 201
    assert resp.data['host_id'] == user.pk


# --- Get by ID ---

@pytest.mark.django_db
def test_get_activity_by_id(auth_client, activity):
    resp = auth_client.get(f'/api/activities/{activity.pk}')
    assert resp.status_code == 200
    assert resp.data['id'] == activity.pk
    assert resp.data['title'] == 'Morning Hike'


@pytest.mark.django_db
def test_get_nonexistent_activity(auth_client):
    resp = auth_client.get('/api/activities/99999')
    assert resp.status_code == 404


# --- Response shape matches client contract ---

@pytest.mark.django_db
def test_activity_shape(auth_client, activity):
    resp = auth_client.get(f'/api/activities/{activity.pk}')
    data = resp.data
    for field in ('id', 'host_id', 'title', 'category', 'price', 'latitude', 'longitude', 'scheduled_at', 'status'):
        assert field in data, f"Missing field: {field}"


# --- Host-only mutations ---

@pytest.mark.django_db
def test_non_host_cannot_delete(client, db, activity):
    other = User.objects.create_user(email='stranger@x.com', password='pass', full_name='Stranger')
    login = client.post('/api/auth/login', {'email': 'stranger@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    resp = client.delete(f'/api/activities/{activity.pk}')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_host_can_delete(auth_client, activity):
    resp = auth_client.delete(f'/api/activities/{activity.pk}')
    assert resp.status_code == 204
    assert not Activity.objects.filter(pk=activity.pk).exists()
