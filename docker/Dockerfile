FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set up working directory
WORKDIR $PYSETUP_PATH

# Copy poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry without installing the project itself
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main --no-interaction --no-ansi

# Copy project files
COPY . .

# Set up entry point
RUN chmod +x /opt/pysetup/docker/entrypoint.sh
ENTRYPOINT ["/opt/pysetup/docker/entrypoint.sh"]

# Default command to run the Django server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "getmebuddy.wsgi:application"]
