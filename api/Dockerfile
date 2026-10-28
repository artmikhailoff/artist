FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g \
  && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY api/app /app/app
COPY seed/manifest.json /seed/manifest.json
RUN mkdir -p /seed/images /seed/videos

ENV ARTIST_DATA_DIR=/data \
    ARTIST_SEED_DIR=/seed \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
