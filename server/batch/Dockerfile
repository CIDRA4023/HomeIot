FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app/
COPY src/ /app/src/

RUN pip install --no-cache-dir uv==0.9.16 \
    && uv sync

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

CMD ["uv", "run", "python", "-m", "homeiot_batch.run_archive"]
