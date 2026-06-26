"""
Root conftest: override DATABASE to SQLite so tests run without a Postgres server.
The .env may point to Postgres (prod/dev); pytest always uses an in-memory SQLite db.
"""
import django
from django.conf import settings


def pytest_configure(config):
    settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    # Disable the channel layer in tests (Redis not running).
    settings.CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }
