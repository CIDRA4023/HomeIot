FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT=/app

WORKDIR /app

COPY pyproject.toml uv.lock /app/

RUN pip install --no-cache-dir uv==0.9.16 \
    && uv sync --frozen

COPY src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "homeiot_mqtt_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
