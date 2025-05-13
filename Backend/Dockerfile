# Dockerfile for Brikli FastAPI Backend (Production-Ready for Supabase/Porter)

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

# 4. Install Poetry (optional, fallback to pip if poetry files not present)
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

# 5. Set Working Directory
WORKDIR /app

# 6. Install Application Dependencies
COPY pyproject.toml poetry.lock* ./
# Install all defined dependencies from pyproject.toml
RUN if [ -f "pyproject.toml" ]; then \
      /opt/poetry/bin/poetry install --no-root --no-interaction; \
    else \
      echo 'No poetry files found, falling back to pip.'; \
      pip install --upgrade pip && pip install -r requirements.txt; \
    fi

# 7. Copy Application Code
COPY . /app/Backend

# 8. Expose Port
EXPOSE 8000

# 9. Healthcheck (Optional, commented out for curl-less images)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:8000/api/health || exit 1

# 10. Run the Application (use uvicorn directly for minimal image and fast startup)
CMD ["uvicorn", "Backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"] 