FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT=/app

WORKDIR /app

COPY pyproject.toml /app/

RUN pip install --no-cache-dir uv==0.9.16 \
    && uv sync

COPY app.py /app/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
