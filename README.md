# GetMeBuddy - Social Buddy Matching Platform

GetMeBuddy is a social platform that helps users find buddies for various activities based on shared interests, location, and availability.

## Features

- **User Authentication**: Secure registration and login with email, social logins (Google, Apple, Facebook)
- **Profile Management**: Detailed user profiles with interests, availability, and preferences
- **Matching Algorithm**: Smart buddy matching based on interests, location, and schedule compatibility
- **Real-time Messaging**: WebSocket-powered chat system for matched buddies
- **Engagement Features**: Gamification elements to increase user retention
- **Safety Measures**: Reporting system and content moderation
- **Premium Features**: Monetization options through subscriptions or one-time payments

## Tech Stack

- **Backend**: Django/Python
- **Database**: PostgreSQL
- **API**: Django REST Framework
- **Authentication**: JWT + Firebase Auth
- **Real-time Communication**: Django Channels with WebSockets
- **Dependency Management**: Poetry
- **Containerization**: Docker

## Project Structure

The project follows a modular structure with separate Django apps for different features:

- `users`: User authentication and management
- `profiles`: User profile data and preferences
- `matching`: Buddy matching algorithm
- `messaging`: Real-time chat system
- `engagement`: Gamification and user retention features
- `safety`: Content moderation and reporting
- `monetization`: Premium features and payment processing

## Development

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis (for WebSockets)

### Quick Start

1. Clone the repository
2. Install dependencies with Poetry: `poetry install`
3. Set up environment variables (copy `.env.template` to `.env` and update values)
4. Run migrations: `python manage.py migrate`
5. Create a superuser: `python manage.py createsuperuser`
6. Start the development server: `python manage.py runserver`

For detailed setup instructions, see the [Setup Guide](SETUP.md).

### API Documentation

API endpoints are documented using Django REST Framework's built-in documentation. After starting the server, visit:

```
http://localhost:8000/api/schema/swagger-ui/
```

## Testing

Run tests with pytest:

```bash
pytest
```

For test coverage:

```bash
pytest --cov=.
```

## Deployment

The project includes Docker configuration for easy deployment:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

## License

[MIT License](LICENSE)

## Contact

For any questions or suggestions, please reach out to [your-email@example.com](mailto:your-email@example.com).