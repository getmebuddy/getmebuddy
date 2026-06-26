"""Unit tests for the Expo push notification helper (users/push.py)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from users.push import send_push, notify_booking_confirmed, notify_new_message


# ---------------------------------------------------------------------------
# send_push — unit tests (no network)
# ---------------------------------------------------------------------------

def test_send_push_skips_invalid_token():
    """Non-Expo tokens must be ignored without any HTTP call."""
    with patch('users.push.urllib.request.urlopen') as mock_open:
        send_push('not-a-valid-token', 'Title', 'Body')
        mock_open.assert_not_called()


def test_send_push_skips_empty_token():
    with patch('users.push.urllib.request.urlopen') as mock_open:
        send_push('', 'Title', 'Body')
        mock_open.assert_not_called()


def test_send_push_calls_expo_api():
    """Valid Expo token triggers a POST to the Expo push endpoint."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps({'data': [{'status': 'ok'}]}).encode()

    with patch('users.push.urllib.request.urlopen', return_value=mock_resp) as mock_open:
        send_push('ExponentPushToken[abc123]', 'Hello', 'World', {'key': 'val'})
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        body = json.loads(req.data)
        assert body['to'] == 'ExponentPushToken[abc123]'
        assert body['title'] == 'Hello'
        assert body['body'] == 'World'
        assert body['data'] == {'key': 'val'}


def test_send_push_swallows_network_error():
    """Network failures must not propagate — fire and forget."""
    with patch('users.push.urllib.request.urlopen', side_effect=OSError('timeout')):
        send_push('ExponentPushToken[abc]', 'T', 'B')  # must not raise


# ---------------------------------------------------------------------------
# notify_booking_confirmed
# ---------------------------------------------------------------------------

def test_notify_booking_confirmed_sends_push():
    booking = MagicMock()
    booking.user.push_token = 'ExponentPushToken[xyz]'
    booking.activity.title = 'Morning Run'
    booking.pk = 99

    with patch('users.push.send_push') as mock_send:
        notify_booking_confirmed(booking)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        # send_push called with positional: (token, title, body, data=...)
        token = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get('to_token')
        body = call_kwargs.args[2] if len(call_kwargs.args) > 2 else call_kwargs.kwargs.get('body', '')
        assert token == 'ExponentPushToken[xyz]'
        assert 'Morning Run' in body


def test_notify_booking_confirmed_skips_missing_token():
    booking = MagicMock()
    booking.user.push_token = ''
    booking.activity.title = 'Run'
    booking.pk = 1

    with patch('users.push.send_push') as mock_send:
        notify_booking_confirmed(booking)
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# notify_new_message
# ---------------------------------------------------------------------------

def test_notify_new_message_sends_to_other_participants():
    sender = MagicMock()
    sender.pk = 1
    sender.full_name = 'Alice'
    sender.email = 'alice@x.com'

    recipient = MagicMock()
    recipient.pk = 2
    recipient.push_token = 'ExponentPushToken[rec]'

    message = MagicMock()
    message.sender = sender
    message.content = 'Hey there!'
    message.conversation.pk = 10
    message.conversation.participants.exclude.return_value = [recipient]

    with patch('users.push.send_push') as mock_send:
        notify_new_message(message)
        mock_send.assert_called_once()
        ca = mock_send.call_args
        token = ca.args[0] if ca.args else ca.kwargs.get('to_token', '')
        title = ca.args[1] if len(ca.args) > 1 else ca.kwargs.get('title', '')
        body = ca.args[2] if len(ca.args) > 2 else ca.kwargs.get('body', '')
        assert token == 'ExponentPushToken[rec]'
        assert 'Alice' in title
        assert 'Hey there!' in body


def test_notify_new_message_skips_recipient_without_token():
    sender = MagicMock()
    sender.pk = 1
    sender.full_name = 'Bob'

    recipient = MagicMock()
    recipient.pk = 2
    recipient.push_token = ''

    message = MagicMock()
    message.sender = sender
    message.content = 'hi'
    message.conversation.pk = 5
    message.conversation.participants.exclude.return_value = [recipient]

    with patch('users.push.send_push') as mock_send:
        notify_new_message(message)
        mock_send.assert_not_called()
