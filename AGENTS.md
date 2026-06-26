# GetMeBuddy: Agent Instructions

GetMeBuddy is a **social buddy matching platform** with modular Django architecture. This document helps AI agents be immediately productive.

## Quick Reference

### Build & Test Commands

```bash
# Install dependencies
poetry install

# Run development server
python manage.py runserver

# Run tests with coverage
pytest --cov=.

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Code formatting (black + isort)
black .
isort .

# Linting
flake8

# Docker deployment
docker-compose -f docker/docker-compose.yml up -d
```

## Project Architecture

### App Structure (7 modular Django apps)

| App | Purpose | Key Files |
|-----|---------|-----------|
| **users** | User authentication, JWT, Firebase integration | models.py, services.py (FirebaseAuthService), signals.py |
| **profiles** | User profile data, interests, preferences | models.py, serializers.py, signals.py |
| **matching** | Buddy matching algorithm with scoring | models.py, services.py (MatchingService), serializers.py |
| **messaging** | Real-time WebSocket chat (Django Channels + Redis) | consumers.py (ChatConsumer), models.py, routing.py |
| **engagement** | Gamification and retention features | models.py, views.py, admin.py |
| **safety** | Content moderation and user reporting | models.py, views.py |
| **monetization** | Premium features and payment processing | models.py, views.py |

### Configuration

- **Database**: PostgreSQL in production, SQLite in development (via `dj_database_url`)
- **Storage**: AWS S3 (auto-enabled if AWS credentials present), local storage fallback
- **Real-time**: Redis + Django Channels for WebSockets
- **Auth**: Custom User model (email as unique identifier) + Firebase OAuth integration
- **API**: Django REST Framework with SimpleJWT
- **Environment**: `.env` file with sensible development defaults (see README)

## Key Conventions

### 1. Model Patterns

**Custom User Model** (`users/models.py`)
- Uses email as unique identifier, not username
- Includes OAuth fields: `firebase_uid`, `signup_method` (email/google/apple/facebook)
- Related via OneToOne: `UserProfile` (extended user data), `MatchPreference` (matching config)

**Standard Metadata**
- All models include `created_at`, `updated_at` timestamps
- Status tracking uses choice fields (e.g., `gender` in Profile, `match_status` in Match)

**Denormalization for Performance**
- Match model stores computed scores: `interest_score`, `distance_score`, `availability_score` (not computed dynamically)
- Enables efficient ranking without recalculating on every query

**Relationships**
- `ManyToMany` patterns: Users ↔ Interests (via `InterestChoice` intermediary)
- OneToOne patterns: User → UserProfile, User → MatchPreference, Conversation ↔ User pairs

### 2. API/ViewSet Patterns

**Standard Structure** (all apps follow this)
```python
# In views.py: ViewSet extends ModelViewSet or ReadOnlyModelViewSet
class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users see only their own data
        return super().get_queryset().filter(pk=self.request.user.pk)
    
    @action(detail=False, methods=['post'])
    def custom_action(self, request):
        # Non-standard endpoints via @action
        pass

# In urls.py: DefaultRouter auto-generates endpoints
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = router.urls
```

**Permissions & Filtering**
- Default: `IsAuthenticated` on all endpoints (set in REST_FRAMEWORK settings)
- Filtering/Search: Enabled globally via `DEFAULT_FILTER_BACKENDS` + `DEFAULT_PAGINATION_CLASS` (PAGE_SIZE: 10)
- Serializers use inheritance and nesting (e.g., `InterestChoiceSerializer` embedded in `InterestSerializer`)

### 3. Service Layer Pattern

**Isolation of Business Logic** (see `users/services.py`, `matching/services.py`)
```python
# Services are stateless utilities that encapsulate complex logic
class MatchingService:
    @staticmethod
    def calculate_match_score(user1, user2, weights=None):
        # Returns dict: {interest_score, distance_score, availability_score, total}
        pass

class FirebaseAuthService:
    # Lazy singleton: checks firebase_admin._apps to avoid re-init
    # Returns structured dicts for view consumption
    pass
```

- Extracted from views for testability and reusability
- Called from views/serializers/signals
- Handle edge cases gracefully (missing data defaults to 0)

### 4. Signal-Driven Creation

**Automatic Object Creation on Signal** (`users/signals.py`, `profiles/signals.py`)
```python
from django.db.models.signals import post_save

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        MatchPreference.objects.create(user=instance, max_distance_km=50)
```

- When a User is created, UserProfile and MatchPreference auto-create
- Profile signals set default interests
- Reduces boilerplate in views

### 5. Real-Time/WebSocket Pattern (Channels)

**ChatConsumer** (`messaging/consumers.py`)
- Extends `AsyncWebsocketConsumer`
- **Connect**: Validates auth (rejects anonymous), adds to channel group `chat_{conversation_id}`
- **Receive**: Type-based routing (message/read/typing types call different handlers)
- **Database ops**: Wrapped with `@database_sync_to_async` to avoid blocking async loop
- **Typing indicators**: Sent as ephemeral events (no DB persistence)
- **Cleanup**: `disconnect()` properly discards from group

**Routing** (`messaging/routing.py`)
```python
websocket_urlpatterns = [
    path("ws/conversations/<int:conversation_id>/", ChatConsumer.as_asgi()),
]
```

### 6. Testing

**Framework**: pytest-django + pytest-cov
- Config in `pyproject.toml`: `DJANGO_SETTINGS_MODULE`, test paths scan all apps
- Tests exist in each app but are mostly scaffolding (MVP phase)
- Fixtures available: `faker` library for test data generation

**Pattern** (when tests are added):
```python
import pytest
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_user_creation():
    User = get_user_model()
    user = User.objects.create_user(email="test@test.com", password="pwd")
    assert user.email == "test@test.com"
```

## Common Pitfalls & Gotchas

| Pitfall | Explanation | Solution |
|---------|-------------|----------|
| **Custom User Model** | Email is unique, not username | Use `User.objects.get(email=...)`, not `.get(username=...)` |
| **Firebase Integration** | Requires valid Firebase credentials in `.env` | Set via `FIREBASE_*` env vars; local dev can work without (graceful degradation) |
| **Permission Scope** | Views enforce user-level filtering via `get_queryset()` | Always filter by current user in `get_queryset()`; don't rely only on permission classes |
| **Channels + Async** | Database calls block event loop | Always use `@database_sync_to_async` for DB operations in consumers |
| **Scoring Denormalization** | Match scores are stored, not computed | Update stored scores when preference weights change; don't compute dynamically in queries |
| **Signal Auto-Creation** | UserProfile auto-creates on User creation | Don't manually create UserProfile or MatchPreference in views; rely on signals |
| **CORS Configuration** | Frontend domains must be whitelisted | Add frontend URLs to `CORS_ALLOWED_ORIGINS` in settings.py |

## File Structure & Key Locations

```
getmebuddy/
  manage.py                 # Django management
  pyproject.toml           # Dependencies, pytest config
  README.md                # Project overview
  getmebuddy/
    settings.py            # Global configuration (apps, middleware, DB, auth)
    urls.py                # Root URL router
    asgi.py                # ASGI config (Channels)
  users/
    models.py              # Custom User, FirebaseAuth models
    services.py            # FirebaseAuthService
    signals.py             # Auto-create UserProfile/MatchPreference
    serializers.py         # JWT token serializers
  matching/
    models.py              # Match, MatchPreference, Interest models
    services.py            # MatchingService (scoring algorithm)
    serializers.py         # Match, MatchPreference serializers
  messaging/
    models.py              # Conversation, Message models
    consumers.py           # ChatConsumer (WebSocket logic)
    routing.py             # Channels routing config
  profiles/
    models.py              # UserProfile, InterestChoice models
    signals.py             # Auto-set default interests
    serializers.py         # Profile serializers
  docker/
    docker-compose.yml     # PostgreSQL, Redis, nginx
    Dockerfile             # Django app container
    nginx/nginx.conf       # Reverse proxy config
```

## Development Workflow

### Creating a New Feature
1. **Model**: Add to app's `models.py` (follow timestamp/choice field conventions)
2. **Serializer**: Create in `serializers.py` (use inheritance, nest related data)
3. **ViewSet**: Add to `views.py` with `@action` decorators for custom endpoints
4. **URLs**: Register in `urls.py` via DefaultRouter
5. **Tests**: Add to app's `tests.py`
6. **Signals**: If auto-creation needed, add to `signals.py`

### Modifying Existing Models
1. **Local**: `python manage.py makemigrations` → `python manage.py migrate`
2. **Production**: Follow Django migration best practices (avoid data loss)

### Running Code Locally
- Ensure `.env` exists with: `DATABASE_URL`, `SECRET_KEY`, `DEBUG=True`, `REDIS_URL` (optional)
- `poetry install` → `python manage.py migrate` → `python manage.py runserver`
- Admin panel: `http://localhost:8000/admin` (after superuser creation)
- API docs: `http://localhost:8000/api/schema/swagger-ui/` (DRF auto-generated)

## Related Documentation

- **Project Overview**: See [README.md](README.md) for feature list and tech stack
- **Setup Instructions**: Refer to SETUP.md for detailed environment configuration
- **API Documentation**: Available at `/api/schema/swagger-ui/` after running dev server
- **Docker Deployment**: Configuration in [docker/docker-compose.yml](docker/docker-compose.yml)

## Notes for AI Agents

- **Tests are scaffolding**: The infrastructure exists but test files are mostly empty—when adding tests, use the pytest-django patterns above
- **MVP mindset**: Some admin customization is minimal; code prioritizes shipping over perfection
- **Modular by design**: Each app is independent—changes to one app rarely affect others; leverage this for focused work
- **Environment-driven config**: The same codebase runs locally and in production via `.env`; always respect environment variables
- **Scoring transparency**: The Match model stores three separate scores (interest, distance, availability) for algorithm visibility; maintain this pattern if extending matching
