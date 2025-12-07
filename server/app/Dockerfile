FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app.py /app/

RUN pip install --no-cache-dir fastapi==0.115.6 \
    uvicorn[standard]==0.32.1 \
    influxdb-client==1.49.0

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
