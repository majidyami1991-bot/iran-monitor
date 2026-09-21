FROM python:3.12-slim
ARG GIT_REVISION=unknown
ARG BUILD_TIMESTAMP_UTC=unknown
LABEL org.opencontainers.image.title="Iran Monitor news collector" org.opencontainers.image.version="1.2.0" org.opencontainers.image.revision="$GIT_REVISION" org.opencontainers.image.created="$BUILD_TIMESTAMP_UTC" org.opencontainers.image.source="local://Iran-monitor"
WORKDIR /app
COPY runtime/wheelhouse/collector /wheelhouse
COPY runtime/evidence/phase-8c-r2b/requirements.exact.txt ./requirements.exact.txt
RUN pip install --no-index --find-links=/wheelhouse --no-cache-dir -r requirements.exact.txt
COPY apps/api/main.py ./main.py
COPY apps/api/ops.py ./ops.py
COPY apps/api/collector.py ./collector.py
RUN printf '{"git_revision":"%s","build_timestamp_utc":"%s","collector_version":"1.2.0","serializer_version":"1","schema_version":"8c-r1"}\n' "$GIT_REVISION" "$BUILD_TIMESTAMP_UTC" > ./BUILD_INFO.json
COPY apps/api/iran_monitor_collector ./iran_monitor_collector
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
