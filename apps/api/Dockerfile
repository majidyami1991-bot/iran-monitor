FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/main.py ./main.py
COPY apps/api/ops.py ./ops.py
COPY apps/api/collector.py ./collector.py
COPY apps/api/health.py ./health.py
COPY config/sources/rss-execution-readiness.json ./rss-execution-readiness.json
COPY config/sources/source-registry.json ./source-registry.json
COPY config/sources/collection-capabilities.json ./collection-capabilities.json
COPY config/sources/classification-taxonomy-v1.json ./classification-taxonomy-v1.json
COPY tests/monitoring ./tests/monitoring
RUN mkdir -p /state && chown 65532:65532 /state
COPY apps/api/db_init.py ./db_init.py
COPY apps/api/import_db.py ./import_db.py
EXPOSE 3000

COPY apps/api/web ./web
