FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS base
WORKDIR /app
COPY apps/collector/wheelhouse /wheelhouse
COPY apps/collector/requirements.exact.txt requirements.exact.txt
FROM base AS runtime-deps
RUN pip install --no-index --find-links=/wheelhouse --no-cache-dir -r requirements.exact.txt
FROM runtime-deps AS test
ENV DATABASE_URL=postgresql://offline_test:offline_test@127.0.0.1:1/collector_test
COPY apps/collector/test-wheelhouse /test-wheelhouse
RUN pip install --no-index --find-links=/test-wheelhouse --no-cache-dir pytest==8.4.1 iniconfig==2.1.0 packaging==25.0 pluggy==1.6.0 pygments==2.19.2
COPY apps/api/main.py apps/api/ops.py apps/api/collector.py apps/api/health.py apps/api/content.py apps/api/translate_worker.py apps/api/content_intelligence.py apps/api/content_validator.py apps/api/net_guard.py apps/api/image_verify.py apps/api/document_verify.py apps/api/article_extract.py apps/api/classify_v2.py apps/api/clustering.py apps/api/enrichment_worker.py apps/api/ai_gateway.py apps/api/classify_v3.py apps/api/clustering_v2.py apps/api/redesign_schema.py apps/api/experience.py apps/api/social.py apps/api/media_pipeline.py apps/api/media_api.py apps/api/media_backfill.py apps/api/media_pilot.py apps/api/x_translate_worker.py apps/api/x_translation_validator.py apps/api/local_ai.py apps/api/local_translation.py apps/api/retrieval.py apps/api/assistant.py apps/api/model_identity.py apps/api/model_approvals.json apps/api/translation_tg.py apps/api/assistant_extractive.py apps/api/assistant_relevance.py apps/api/assistant_v13.py apps/api/translation_qc.py apps/api/translation_v2.py apps/api/translation_v21.py apps/api/translation_v22.py apps/api/translation_worker_v2.py apps/api/lab_ops.py ./
COPY apps/api/repair_stuck_run.py ./repair_stuck_run.py
COPY apps/api/iran_monitor_collector ./iran_monitor_collector
COPY config/sources/rss-execution-readiness.json config/sources/source-registry.json config/sources/collection-capabilities.json config/sources/classification-taxonomy-v1.json config/sources/classification-taxonomy-v2.json config/sources/classification-taxonomy-v3.json config/sources/x-free-readiness.json config/sources/feed-sitemap-discovery.json ./sources/
COPY tests/monitoring ./tests/monitoring
RUN python -m compileall -q /app && PYTHONPATH=/app pytest -q tests/monitoring && touch /test-stage-passed
FROM runtime-deps AS runtime-final
ARG GIT_REVISION=unknown
ARG BUILD_TIMESTAMP_UTC=unknown
LABEL org.opencontainers.image.title="Defence Monitor news collector" org.opencontainers.image.version="1.2.0" org.opencontainers.image.revision="$GIT_REVISION" org.opencontainers.image.created="$BUILD_TIMESTAMP_UTC" org.opencontainers.image.source="local://defence-monitor"
COPY apps/api/main.py apps/api/ops.py apps/api/collector.py apps/api/health.py apps/api/content.py apps/api/translate_worker.py apps/api/content_intelligence.py apps/api/content_validator.py apps/api/net_guard.py apps/api/image_verify.py apps/api/document_verify.py apps/api/article_extract.py apps/api/classify_v2.py apps/api/clustering.py apps/api/enrichment_worker.py apps/api/ai_gateway.py apps/api/classify_v3.py apps/api/clustering_v2.py apps/api/redesign_schema.py apps/api/experience.py apps/api/social.py apps/api/media_pipeline.py apps/api/media_api.py apps/api/media_backfill.py apps/api/media_pilot.py apps/api/x_translate_worker.py apps/api/x_translation_validator.py apps/api/local_ai.py apps/api/local_translation.py apps/api/retrieval.py apps/api/assistant.py apps/api/model_identity.py apps/api/model_approvals.json apps/api/translation_tg.py apps/api/assistant_extractive.py apps/api/assistant_relevance.py apps/api/assistant_v13.py apps/api/translation_qc.py apps/api/translation_v2.py apps/api/translation_v21.py apps/api/translation_v22.py apps/api/translation_worker_v2.py apps/api/lab_ops.py ./
COPY apps/api/iran_monitor_collector ./iran_monitor_collector
COPY apps/api/web ./web
COPY config/sources/rss-execution-readiness.json config/sources/source-registry.json config/sources/collection-capabilities.json config/sources/classification-taxonomy-v1.json config/sources/classification-taxonomy-v2.json config/sources/classification-taxonomy-v3.json config/sources/x-free-readiness.json config/sources/feed-sitemap-discovery.json ./sources/
RUN printf '{"git_revision":"%s","build_timestamp_utc":"%s","collector_version":"1.2.0","serializer_version":"1","schema_version":"8c-r1"}\n' "$GIT_REVISION" "$BUILD_TIMESTAMP_UTC" > BUILD_INFO.json && mkdir -p /state && chown 65532:65532 /state
COPY --from=test /test-stage-passed /test-stage-passed
EXPOSE 3000
