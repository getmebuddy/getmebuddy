"""Smoke tests: verify the Django project is wired up and importable.

These intentionally avoid touching the database so they run fast and remain
stable regardless of migration state. They exist so the test suite has at least
one real, collectible test (pytest is configured with python_files=test_*.py).
"""

from django.apps import apps
from django.contrib.auth import get_user_model


def test_apps_are_loaded():
    """All installed apps import and populate without error."""
    assert apps.apps_ready
    assert apps.get_app_configs()


def test_custom_user_model_resolves():
    """The custom AUTH_USER_MODEL is importable."""
    user_model = get_user_model()
    assert user_model is not None
    assert user_model._meta.app_label == "users"
