import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking, StripeCustomer
from .serializers import BookingSerializer, BookingCreateSerializer


def _get_stripe_customer(user):
    """Return (or create) the Stripe Customer for this user."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        sc = user.stripe_customer
        return sc.stripe_customer_id
    except StripeCustomer.DoesNotExist:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name or user.email,
            metadata={'user_id': str(user.pk)},
        )
        StripeCustomer.objects.create(user=user, stripe_customer_id=customer.id)
        return customer.id


class CreatePaymentIntentView(APIView):
    """POST /api/payments/create-intent"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        amount = request.data.get('amount')
        currency = request.data.get('currency', 'usd')
        activity_id = request.data.get('activity_id')
        metadata = request.data.get('metadata', {})

        if not amount:
            return Response({'detail': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer_id = _get_stripe_customer(request.user)

            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount),
                currency=currency,
                customer=customer_id,
                metadata={**metadata, 'user_id': str(request.user.pk), 'activity_id': str(activity_id or '')},
                automatic_payment_methods={'enabled': True},
            )

            ephemeral_key = stripe.EphemeralKey.create(
                customer=customer_id,
                stripe_version='2023-10-16',
            )

            return Response({
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'ephemeral_key': ephemeral_key.secret,
                'customer': customer_id,
            })
        except stripe.error.StripeError as e:
            return Response({'detail': str(e.user_message or e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    POST /api/payments/webhook
    CSRF-exempt — Stripe calls this directly. Signature is verified instead.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'detail': 'Malformed payload.'}, status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'payment_intent.succeeded':
            pi_id = event['data']['object']['id']
            Booking.objects.filter(payment_intent_id=pi_id).update(status=Booking.STATUS_CONFIRMED)

        elif event['type'] == 'payment_intent.payment_failed':
            pi_id = event['data']['object']['id']
            Booking.objects.filter(payment_intent_id=pi_id).update(status=Booking.STATUS_CANCELLED)

        return Response({'received': True})


class BookingListCreateView(APIView):
    """
    GET  /api/bookings  — current user's bookings
    POST /api/bookings  — create a booking
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.select_related('activity', 'activity__host').filter(user=request.user)
        return Response(BookingSerializer(bookings, many=True).data)

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
