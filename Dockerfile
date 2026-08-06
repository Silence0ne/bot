FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY pyproject.toml README.md ./

RUN mkdir -p app alembic

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./

RUN chmod +x docker-entrypoint.sh

RUN pip install .

RUN useradd \
    --create-home \
    --shell /bin/bash \
    --uid 1000 \
    appuser \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["./docker-entrypoint.sh"]
