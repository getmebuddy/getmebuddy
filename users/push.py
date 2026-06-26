"""
Expo Push Notification helper.

Sends notifications via the Expo Push API (no SDK needed — it's a plain
HTTPS POST). Only sends to tokens that start with 'ExponentPushToken['.
Failures are logged but never raised to callers.
"""
import logging
import urllib.request
import json

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = 'https://exp.host/--/api/v2/push/send'


def send_push(to_token: str, title: str, body: str, data: dict = None):
    """Fire-and-forget push to a single Expo push token."""
    if not to_token or not to_token.startswith('ExponentPushToken['):
        return

    payload = json.dumps({
        'to': to_token,
        'title': title,
        'body': body,
        'data': data or {},
        'sound': 'default',
    }).encode('utf-8')

    req = urllib.request.Request(
        EXPO_PUSH_URL,
        data=payload,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if result.get('data', [{}])[0].get('status') != 'ok':
                logger.warning('Expo push not ok: %s', result)
    except Exception as exc:
        logger.warning('Expo push failed for token %s: %s', to_token[:20], exc)


def notify_booking_confirmed(booking):
    """Notify the booker that their booking was confirmed."""
    token = getattr(booking.user, 'push_token', '')
    if token:
        send_push(
            token,
            title='Booking Confirmed!',
            body=f'Your booking for "{booking.activity.title}" is confirmed.',
            data={'booking_id': booking.pk, 'type': 'booking_confirmed'},
        )


def notify_new_message(message):
    """Notify all conversation participants (except the sender) of a new message."""
    sender = message.sender
    for participant in message.conversation.participants.exclude(pk=sender.pk):
        token = getattr(participant, 'push_token', '')
        if token:
            send_push(
                token,
                title=f'New message from {sender.full_name or sender.email}',
                body=message.content[:100],
                data={'conversation_id': message.conversation.pk, 'type': 'new_message'},
            )
