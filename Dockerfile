# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engram ./engram
COPY data ./data
COPY website ./website
COPY main.py .

ENV ENGRAM_STORE=local \
    ENGRAM_PUBLIC_MODE=true \
    ENGRAM_SEED_ON_BOOT=true \
    ENGRAM_PUBLIC_INGEST_LIMIT=30 \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn engram.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
