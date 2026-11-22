# Source Registry

`scripts/build_source_registry.py` deterministically extracts the three-column `sites.docx` table without network access. It preserves all raw occurrences and emits canonical records under `config/sources/`.

IDs are UUIDv5 using the DNS namespace and `source_type|canonical_key`. URL normalization lowercases scheme/host for comparison, removes fragments, and preserves query strings; X handles retain `@` and compare case-insensitively. Records start disabled with validation and collection not started. HTTP URLs and the `news.usni.org` classification are marked for review.

Expected output is 64 raw occurrences and 62 canonical sources (17 news, 9 think tanks, 36 X accounts), including two duplicate X groups. The builder performs no HTTP, DNS, API, crawl, ingestion, or OpenCTI mutation.
