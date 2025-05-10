# Dockerfile for Brikli FastAPI Backend

# 1. Base Image
FROM python:3.11-slim

# 2. Environment Variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Poetry settings
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    # Path
    PATH="$POETRY_HOME/bin:$PATH" \
    # App settings
    APP_MODULE="Backend.api.app:app" \
    PORT=8000 \
    HOST="0.0.0.0"

# 3. System Dependencies
# build-essential & libpq-dev are for compiling some Python packages (like psycopg2 if not using binary)
# curl is for downloading poetry installer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

# 5. Set Working Directory
WORKDIR /app

# 6. Install Application Dependencies
# Copy only files necessary for dependency installation to leverage Docker cache
COPY pyproject.toml poetry.lock* ./
# Install dependencies, --no-dev for production, --no-root as we are installing an app
RUN poetry install --no-dev --no-root --sync

# 7. Copy Application Code
COPY ./Backend /app/Backend

# 8. Expose Port
EXPOSE ${PORT}

# 9. Healthcheck (Optional but recommended for orchestrators like Kubernetes)
# The health endpoint is /api/health as seen in Backend/api/app.py
# Adjust the interval, timeout, retries as necessary
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:${PORT}/api/health || exit 1
# Commenting out healthcheck as curl might not be available in the slim image without explicit install for runtime.
# If you need healthcheck via curl, add `apt-get install -y curl` to system deps and uncomment.
# Alternatively, use a Python script for healthcheck.

# 10. Run the Application
# Uses Gunicorn with Uvicorn workers, as specified.
# Number of workers (-w 2) is a starting point, adjust based on your instance size.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:${PORT}", "${APP_MODULE}"] 