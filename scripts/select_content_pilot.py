"""Deterministic selection of the 20-item content enrichment pilot.

Reproducible: run twice against the same database state and it picks the same
items in the same order. Sort keys are the item's own stable fields
(item_id, published_at) — never randomness, never wall-clock time. Writes a
manifest containing only identifiers, reasons and a baseline hash of the
*currently stored* title/summary (so a later run can detect whether the
underlying row changed) — never the article body, which may carry republish
restrictions and must not enter Git.

    python scripts/select_content_pilot.py > data/runtime/collector/content-pilot/manifest.json
"""
import hashlib, json, os, sys
from datetime import datetime, timezone

import psycopg

DSN = os.environ.get('DATABASE_URL', 'postgresql://iran_monitor@127.0.0.1:5432/iran_monitor')
TARGET_COUNT = 20
MIN_SOURCES = 5
MIN_WITH_TEXT = 5
MIN_WITH_IMAGE = 5
MIN_WITH_DOCUMENT = 2


def fetch_candidates(conn):
    """One row per item with the signals selection needs, newest first,
    item_id as the tiebreaker so ordering never depends on anything but the
    stored data."""
    return conn.execute('''
        SELECT n.item_id, n.source_id, n.title, n.canonical_url, n.published_at,
               COALESCE(n.summary_text, n.summary) summary,
               COALESCE(c.extraction_status = 'available', false) has_text,
               EXISTS(SELECT 1 FROM news_item_media m WHERE m.item_id = n.item_id
                      AND m.kind='image' AND m.relevance IN ('article_image','article_media')) has_image_candidate,
               EXISTS(SELECT 1 FROM news_item_media m WHERE m.item_id = n.item_id AND m.kind='document') has_document,
               s.display_name
        FROM news_items n
        JOIN sources s USING(source_id)
        LEFT JOIN news_item_content c USING(item_id)
        ORDER BY n.published_at DESC NULLS LAST, n.item_id
    ''').fetchall()


def content_hash(title, summary):
    return hashlib.sha256(((title or '') + '\n' + (summary or '')).encode('utf-8')).hexdigest()


def select(rows):
    """Greedy deterministic pass: walk newest-first, take an item if it adds
    value toward an unmet quota (source diversity, text, image, document,
    negative cases), stop once every quota is met and 20 are picked. The walk
    order is fixed by the SQL ORDER BY, so this is fully reproducible."""
    chosen = []
    seen_sources = set()
    seen_urls = set()
    have_text = have_image = have_document = have_no_text = have_no_media = 0
    have_title_words = {}

    def add(row, reason):
        chosen.append({'item_id': row[0], 'source_id': row[1], 'canonical_url': row[3],
                        'selection_reason': reason, 'source_name': row[9],
                        'baseline_content_sha256': content_hash(row[2], row[5])})
        seen_sources.add(row[1])
        seen_urls.add(row[3])

    # Pass 1: fill the document quota first — it's the scarcest signal.
    for row in rows:
        if have_document >= MIN_WITH_DOCUMENT:
            break
        if row[3] in seen_urls or not row[8]:
            continue
        add(row, 'has_document_link')
        have_document += 1
        if row[6]:
            have_text += 1
        if row[7]:
            have_image += 1

    # Pass 2: fill image and text quotas, favoring source diversity.
    for row in rows:
        if len(chosen) >= TARGET_COUNT:
            break
        if row[3] in seen_urls:
            continue
        needs_text = have_text < MIN_WITH_TEXT and row[6]
        needs_image = have_image < MIN_WITH_IMAGE and row[7]
        needs_source = row[1] not in seen_sources
        if needs_text or needs_image or needs_source:
            add(row, 'has_text' if needs_text else ('has_image_candidate' if needs_image else 'new_source_for_diversity'))
            if row[6]:
                have_text += 1
            if row[7]:
                have_image += 1

    # Pass 3: at least two negative cases — no text and/or no media — to
    # exercise the honest "unavailable" states.
    for row in rows:
        if have_no_text >= 2 and have_no_media >= 2:
            break
        if row[3] in seen_urls or len(chosen) >= TARGET_COUNT:
            break
        if not row[6] and have_no_text < 2:
            add(row, 'negative_case_no_extracted_text')
            have_no_text += 1
        elif not row[7] and have_no_media < 2:
            add(row, 'negative_case_no_image_candidate')
            have_no_media += 1

    # Pass 4: pad to 20 with the next newest unused items, still deterministic.
    for row in rows:
        if len(chosen) >= TARGET_COUNT:
            break
        if row[3] in seen_urls:
            continue
        add(row, 'fill_to_target_count')

    # Look for a same-day, same-topic pair among what's chosen, for the
    # clustering smoke test — record it, don't force extra picks for it.
    cluster_hint = []
    by_day = {}
    for c in chosen:
        row = next(r for r in rows if r[0] == c['item_id'])
        day = row[4].date().isoformat() if row[4] else None
        by_day.setdefault(day, []).append((c['item_id'], row[2]))
    for day, items in by_day.items():
        if len(items) < 2:
            continue
        words = [set(t.lower().split()) for _, t in items]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                overlap = words[i] & words[j] - {'the', 'a', 'to', 'in', 'of', 'on', 'and', 'for'}
                if len(overlap) >= 2:
                    cluster_hint.append({'items': [items[i][0], items[j][0]], 'shared_words': sorted(overlap)})

    return chosen, cluster_hint


def main():
    with psycopg.connect(DSN) as conn:
        rows = fetch_candidates(conn)
        chosen, cluster_hint = select(rows)

    sources = {c['source_id'] for c in chosen}
    manifest = {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'target_count': TARGET_COUNT,
        'item_count': len(chosen),
        'source_count': len(sources),
        'items': chosen,
        'candidate_event_pairs': cluster_hint,
        'note': 'Identifiers and reasons only. No article body is stored here; '
                'full text is subject to each source\'s republish policy and never enters Git.',
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if len(chosen) != TARGET_COUNT:
        print(f'WARNING: selected {len(chosen)} of {TARGET_COUNT}', file=sys.stderr)
    if len(sources) < MIN_SOURCES:
        print(f'WARNING: only {len(sources)} distinct sources, need {MIN_SOURCES}', file=sys.stderr)


if __name__ == '__main__':
    main()
