#!/bin/sh

# Wait for the database to be ready
echo "Waiting for database..."
python -c 'import time, psycopg2, os, dj_database_url; dbconfig = dj_database_url.config(os.environ.get("DATABASE_URL", "postgres://postgres:postgres@db:5432/getmebuddy")); dbconfig.pop("NAME"); dbconfig["database"] = "postgres"; connected=False; while not connected: try: psycopg2.connect(**dbconfig); connected=True; print("Database is ready!"); except Exception as e: print(f"Waiting for database... {e}"); time.sleep(1);'

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if it doesn't exist..."
python -c 'import os, django; django.setup(); from django.contrib.auth import get_user_model; User = get_user_model(); admin_email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com"); admin_password = os.environ.get("DJANGO_ADMIN_PASSWORD", "admin"); User.objects.filter(email=admin_email).exists() or User.objects.create_superuser(admin_email, admin_password)'

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the passed command
exec "$@"
