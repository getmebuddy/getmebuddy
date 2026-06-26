import json
import time
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from activities.models import Activity
from .models import Booking, StripeCustomer

User = get_user_model()


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='buyer@x.com', password='pass', full_name='Buyer')


@pytest.fixture
def host_user(db):
    return User.objects.create_user(email='host@x.com', password='pass', full_name='Host')


@pytest.fixture
def auth_client(client, user):
    resp = client.post('/api/auth/login', {'email': 'buyer@x.com', 'password': 'pass'}, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


@pytest.fixture
def activity(db, host_user):
    return Activity.objects.create(
        host=host_user, title='Yoga', category='wellness',
        price=20.00, latitude=37.7, longitude=-122.4,
        scheduled_at=timezone.now(), status='open',
    )


# ── Stripe mock helpers ─────────────────────────────────────────────────────

def make_stripe_mock():
    """Return a mock stripe module with the objects the views call."""
    m = MagicMock()

    # stripe.Customer.create
    m.Customer.create.return_value = MagicMock(id='cus_test123')
    # stripe.PaymentIntent.create
    m.PaymentIntent.create.return_value = MagicMock(
        id='pi_test456',
        client_secret='pi_test456_secret_abc',
    )
    # stripe.EphemeralKey.create
    m.EphemeralKey.create.return_value = MagicMock(secret='ek_test789')
    # stripe.error
    m.error = __import__('stripe').error

    return m


# ── Payment intent ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_payment_intent_returns_secrets(auth_client, user):
    with patch('monetization.views.stripe', make_stripe_mock()):
        resp = auth_client.post('/api/payments/create-intent', {
            'amount': 2000, 'currency': 'usd', 'activity_id': None,
        }, format='json')
    assert resp.status_code == 200
    assert 'client_secret' in resp.data
    assert 'payment_intent_id' in resp.data
    assert 'ephemeral_key' in resp.data
    assert 'customer' in resp.data


@pytest.mark.django_db
def test_create_payment_intent_requires_amount(auth_client):
    with patch('monetization.views.stripe', make_stripe_mock()):
        resp = auth_client.post('/api/payments/create-intent', {'currency': 'usd'}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_payment_intent_requires_auth(client):
    resp = client.post('/api/payments/create-intent', {'amount': 1000}, format='json')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_stripe_customer_created_on_first_intent(auth_client, user):
    with patch('monetization.views.stripe', make_stripe_mock()):
        auth_client.post('/api/payments/create-intent', {'amount': 1000}, format='json')
    assert StripeCustomer.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_stripe_customer_reused_on_second_intent(auth_client, user, db):
    StripeCustomer.objects.create(user=user, stripe_customer_id='cus_existing')
    mock = make_stripe_mock()
    with patch('monetization.views.stripe', mock):
        auth_client.post('/api/payments/create-intent', {'amount': 1000}, format='json')
    # Customer.create should NOT be called since one already exists
    mock.Customer.create.assert_not_called()


# ── Bookings ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_booking(auth_client, activity):
    resp = auth_client.post('/api/bookings', {
        'activity_id': activity.pk,
        'payment_intent_id': 'pi_test456',
        'status': 'confirmed',
    }, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'confirmed'
    assert resp.data['activity']['id'] == activity.pk


@pytest.mark.django_db
def test_create_booking_bad_activity(auth_client):
    resp = auth_client.post('/api/bookings', {
        'activity_id': 99999,
        'payment_intent_id': 'pi_x',
        'status': 'confirmed',
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_bookings(auth_client, user, activity):
    Booking.objects.create(user=user, activity=activity, payment_intent_id='pi_abc', status='confirmed')
    resp = auth_client.get('/api/bookings')
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]['payment_intent_id'] == 'pi_abc'


@pytest.mark.django_db
def test_list_bookings_only_own(auth_client, user, host_user, activity):
    Booking.objects.create(user=user, activity=activity, payment_intent_id='pi_mine', status='confirmed')
    Booking.objects.create(user=host_user, activity=activity, payment_intent_id='pi_theirs', status='confirmed')
    resp = auth_client.get('/api/bookings')
    assert all(b['payment_intent_id'] == 'pi_mine' for b in resp.data)


# ── Stripe webhook ────────────────────────────────────────────────────────────

def _build_webhook_event(event_type, pi_id, secret):
    """Build a minimal signed Stripe webhook payload."""
    import stripe as real_stripe
    payload = json.dumps({
        'type': event_type,
        'data': {'object': {'id': pi_id}},
    })
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    import hmac, hashlib
    sig = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    stripe_sig = f"t={timestamp},v1={sig}"
    return payload, stripe_sig


@pytest.mark.django_db
def test_webhook_payment_succeeded_updates_booking(client, user, activity):
    booking = Booking.objects.create(
        user=user, activity=activity,
        payment_intent_id='pi_webhook1', status='pending',
    )
    secret = 'whsec_testsecret'
    payload, sig = _build_webhook_event('payment_intent.succeeded', 'pi_webhook1', secret)

    mock = make_stripe_mock()
    import stripe as real_stripe
    mock.Webhook.construct_event.return_value = {
        'type': 'payment_intent.succeeded',
        'data': {'object': {'id': 'pi_webhook1'}},
    }
    with patch('monetization.views.stripe', mock):
        with patch('monetization.views.settings') as mock_settings:
            mock_settings.STRIPE_SECRET_KEY = 'sk_test_x'
            mock_settings.STRIPE_WEBHOOK_SECRET = secret
            resp = client.post(
                '/api/payments/webhook',
                data=payload,
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE=sig,
            )
    assert resp.status_code == 200
    booking.refresh_from_db()
    assert booking.status == 'confirmed'


@pytest.mark.django_db
def test_webhook_invalid_signature_rejected(client):
    resp = client.post(
        '/api/payments/webhook',
        data='{}',
        content_type='application/json',
        HTTP_STRIPE_SIGNATURE='t=bad,v1=bad',
    )
    assert resp.status_code == 400
