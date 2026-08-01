FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1\
    PYTHONUNBUFFERED=1\
    PIP_NO_CACHE_DIR=1\
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Copy project files
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Install Python dependencies
RUN pip install .[dev] 2>&1 | grep -i "successfully installed" || pip install .

# Remove build dependencies to reduce image size
RUN apt-get purge -y --auto-remove build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "app"]
