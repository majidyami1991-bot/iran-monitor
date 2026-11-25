"""Content enrichment queue and worker: extraction -> media validation ->
translation -> classification -> clustering, decoupled from RSS collection so
a failure here can never roll back a collected item (see collector.py, which
this module never imports from or calls into).

    python enrichment_worker.py --manifest config/content-pilot/manifest-v1.json --enqueue
    python enrichment_worker.py --stage extraction
    python enrichment_worker.py --stage media
    python enrichment_worker.py --stage translation
    python enrichment_worker.py --stage classification
    python enrichment_worker.py --stage clustering --manifest config/content-pilot/manifest-v1.json
    python enrichment_worker.py --recover-stale-jobs
"""
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb

import article_extract as ae
import classify_v2 as cv
import clustering as cl
import document_verify as dv
import image_verify as iv
import ai_gateway as gw
import content_intelligence as ci
from content import is_plausible_full_text

DSN = os.environ['DATABASE_URL']
STAGES = ('extraction', 'media', 'translation', 'classification', 'clustering')
MAX_ATTEMPTS = 3
STALE_PROCESSING_MINUTES = 15
BACKOFF_SECONDS = (30, 180, 900)  # per attempt, capped at the last value


def q(sql, args=()):
    with psycopg.connect(DSN, autocommit=True) as c:
        return c.execute(sql, args).fetchall()


def _job_id(item_id, stage):
    return hashlib.sha256(f'{item_id}|{stage}'.encode()).hexdigest()[:32]


def enqueue(item_ids, stages=STAGES):
    """Idempotent: a job already queued or already terminal for this
    item+stage is left untouched (ON CONFLICT DO NOTHING), so enqueueing the
    same manifest twice never duplicates or resets work."""
    rows = [(_job_id(i, s), i, s) for i in item_ids for s in stages]
    with psycopg.connect(DSN, autocommit=True) as c:
        for job_id, item_id, stage in rows:
            c.execute('''INSERT INTO enrichment_jobs(job_id,item_id,stage,status)
                VALUES(%s,%s,%s,'pending') ON CONFLICT(item_id,stage) DO NOTHING''',
                (job_id, item_id, stage))
    return len(rows)


def recover_stale_jobs(worker_id=None):
    """A job stuck in 'processing' past a threshold (the worker that claimed
    it died without finishing) is returned to 'pending' so it is retried
    rather than lost. Never touches a job that is genuinely still within its
    stale window — this is a recovery pass, not a force-reset."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_PROCESSING_MINUTES)
    rows = q('''UPDATE enrichment_jobs SET status='pending', locked_at=NULL, locked_by=NULL, updated_at=now()
        WHERE status='processing' AND locked_at < %s RETURNING job_id''', (cutoff,))
    return len(rows)


def _claim_next(stage, worker_id):
    """Atomically claim exactly one pending, due job for a stage. Prioritizes recent articles
    over historical backfills so breaking news is never starved."""
    with psycopg.connect(DSN) as c:
        with c.transaction():
            row = c.execute('''SELECT j.job_id, j.item_id, j.attempts FROM enrichment_jobs j
                LEFT JOIN news_items n ON n.item_id = j.item_id
                WHERE j.stage=%s AND j.status='pending' AND j.available_at<=now()
                ORDER BY j.attempts ASC,
                         (COALESCE(n.published_at, n.fetched_at) >= now() - interval '7 days') DESC,
                         COALESCE(n.published_at, n.fetched_at) DESC NULLS LAST,
                         j.created_at ASC
                LIMIT 1 FOR UPDATE OF j SKIP LOCKED''', (stage,)).fetchone()
            if not row:
                return None
            job_id, item_id, attempts = row
            c.execute('''UPDATE enrichment_jobs SET status='processing', locked_at=now(), locked_by=%s,
                attempts=attempts+1, updated_at=now() WHERE job_id=%s''', (worker_id, job_id))
            return {'job_id': job_id, 'item_id': item_id, 'attempts': attempts + 1}


def _finish(job_id, *, ok, error=None):
    with psycopg.connect(DSN, autocommit=True) as c:
        if ok:
            c.execute("UPDATE enrichment_jobs SET status='succeeded', last_error=NULL, updated_at=now() WHERE job_id=%s", (job_id,))
            return
        row = c.execute('SELECT attempts, max_attempts FROM enrichment_jobs WHERE job_id=%s', (job_id,)).fetchone()
        attempts, max_attempts = row
        if attempts >= max_attempts:
            c.execute("UPDATE enrichment_jobs SET status='dead_letter', last_error=%s, updated_at=now() WHERE job_id=%s",
                      (error, job_id))
        else:
            delay = BACKOFF_SECONDS[min(attempts - 1, len(BACKOFF_SECONDS) - 1)]
            c.execute('''UPDATE enrichment_jobs SET status='pending', last_error=%s,
                available_at=now()+ (%s || ' seconds')::interval, updated_at=now() WHERE job_id=%s''',
                (error, delay, job_id))


def _fetch_item(item_id):
    rows = q('''SELECT n.item_id,n.title,n.canonical_url,n.published_at,
        COALESCE(n.summary_text,n.summary),
        c.extraction_status,c.original_text,c.display_policy
        FROM news_items n LEFT JOIN news_item_content c USING(item_id) WHERE n.item_id=%s''', (item_id,))
    if not rows:
        return None
    keys = ['item_id', 'title', 'canonical_url', 'published_at', 'summary',
            'extraction_status', 'original_text', 'display_policy']
    return dict(zip(keys, rows[0]))


# --------------------------------------------------------------------------- extraction
def process_extraction(item_id):
    item = _fetch_item(item_id)
    if not item:
        return 'item_not_found'
    if item['extraction_status'] == 'available' and item.get('original_text') and item['original_text'].strip():
        return 'already_have_full_text'  # policy order: existing full text wins; no request made

    result = ae.fetch_article(item['canonical_url'])
    text = '\n'.join(b['text'] for b in result['blocks'])
    if result['status'] != 'available' or not text.strip():
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute('''INSERT INTO news_item_content(item_id,content_version,extraction_method,extraction_status,
                display_policy,content_type,unavailable_reason,source_url)
                VALUES(%s,1,'public_article','unavailable','link_only','unavailable',%s,%s)
                ON CONFLICT(item_id) DO UPDATE SET extraction_status='unavailable',content_type='unavailable',
                unavailable_reason=EXCLUDED.unavailable_reason,updated_at=now()
                WHERE news_item_content.extraction_status IS DISTINCT FROM 'available'
                ''', (item_id, result.get('reason', 'no_text_extracted'), item['canonical_url']))
        raise RuntimeError(f"extraction_unavailable:{result.get('reason', 'empty')}")

    policy = 'full_syndicated' if is_plausible_full_text(text) else 'summary_only'
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute('''INSERT INTO news_item_content(item_id,content_version,extraction_method,extraction_status,
            display_policy,content_type,content_sha256,original_text,text_chars,source_url,copyright_status)
            VALUES(%s,1,'public_article_extraction','available',%s,'public_article',%s,%s,%s,%s,'source_owned_not_relicensed')
            ON CONFLICT(item_id) DO UPDATE SET extraction_status='available',content_type='public_article',
            display_policy=EXCLUDED.display_policy,
            content_sha256=EXCLUDED.content_sha256,original_text=EXCLUDED.original_text,
            text_chars=EXCLUDED.text_chars,source_url=EXCLUDED.source_url,updated_at=now()
            WHERE news_item_content.content_sha256 IS DISTINCT FROM EXCLUDED.content_sha256''',
            (item_id, policy, digest, text, len(text), result.get('final_url', item['canonical_url'])))
        for img in result['images'][:10]:
            media_id = hashlib.sha256(f"{item_id}|{img['url']}".encode()).hexdigest()
            c.execute('''INSERT INTO news_item_media(media_id,item_id,kind,url,alt_text,declared_width,declared_height,
                position,relevance,discovery_method,verification_status)
                VALUES(%s,%s,'image',%s,%s,%s,%s,%s,'article_media','public_article_extraction','unverified')
                ON CONFLICT(media_id) DO NOTHING''',
                (media_id, item_id, img['url'], img.get('alt_text'), img.get('declared_width'),
                 img.get('declared_height'), img.get('order')))
        for doc in result['documents'][:5]:
            media_id = hashlib.sha256(f"{item_id}|{doc['url']}".encode()).hexdigest()
            c.execute('''INSERT INTO news_item_media(media_id,item_id,kind,url,document_title,relevance,
                discovery_method,verification_status)
                VALUES(%s,%s,'document',%s,%s,'linked_document','public_article_extraction','unverified')
                ON CONFLICT(media_id) DO NOTHING''',
                (media_id, item_id, doc['url'], doc.get('title')))
    return f"extracted:{len(text)}_chars,{len(result['images'])}_images,{len(result['documents'])}_documents"


# --------------------------------------------------------------------------- media
def process_media(item_id):
    rows = q('''SELECT media_id,kind,url FROM news_item_media
        WHERE item_id=%s AND verification_status='unverified' ''', (item_id,))
    if not rows:
        return 'no_unverified_media'
    results = []
    for media_id, kind, url in rows:
        if kind == 'image':
            results.append(_verify_one_image(media_id, url))
        elif kind == 'document':
            results.append(_verify_one_document(media_id, url))
    return '; '.join(results) if results else 'nothing_to_verify'


def _verify_one_image(media_id, url):
    import net_guard as ng
    try:
        resp = ng.guarded_get(url, max_bytes=8 * 1024 * 1024)
    except ng.GuardError as exc:
        with psycopg.connect(DSN, autocommit=True) as c:
            c.execute('''UPDATE news_item_media SET verification_status='rejected',
                rejection_reason=%s, verified_at=now() WHERE media_id=%s''', (f'fetch_failed:{exc}', media_id))
        return f'image_rejected:{exc}'
    info = iv.verify_image(resp.body)
    if info is None:
        reason = 'bytes_do_not_match_a_known_image_format'
    elif iv.meets_minimum_size(info) is False:
        reason = f'too_small:{info.width}x{info.height}'
    else:
        reason = None
    digest = hashlib.sha256(resp.body).hexdigest()
    with psycopg.connect(DSN, autocommit=True) as c:
        if reason:
            c.execute('''UPDATE news_item_media SET verification_status='rejected', rejection_reason=%s,
                verified_mime=%s, content_sha256=%s, verified_at=now() WHERE media_id=%s''',
                (reason, info.mime_type if info else None, digest, media_id))
            return f'image_rejected:{reason}'
        c.execute('''UPDATE news_item_media SET verification_status='verified', verified_mime=%s,
            verified_width=%s, verified_height=%s, content_sha256=%s, copyright_status='source_owned_not_relicensed',
            verified_at=now() WHERE media_id=%s''', (info.mime_type, info.width, info.height, digest, media_id))
    return f'image_verified:{info.width}x{info.height}'


def _verify_one_document(media_id, url):
    result = dv.check_document(url, download_for_hash=True)
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute('''UPDATE news_item_media SET security_status=%s, verified_mime=%s, byte_size=%s,
            content_sha256=%s, verification_status=%s, verified_at=now() WHERE media_id=%s''',
            (result.security_status, result.mime_type, result.byte_size, result.content_sha256,
             'verified' if result.security_status in ('downloaded_safe', 'link_only') else 'rejected', media_id))
    return f'document_{result.security_status}:{result.reason}'


# --------------------------------------------------------------------------- translation
_SUMMARY_KIND_FUNCS = {
    'summary': ci.summarize_news,
    'executive_summary': ci.generate_executive_summary,
    'why_it_matters': ci.generate_why_it_matters,
}


def current_translation_status(result):
    """Status for the current (displayable) row. The provider answering is not
    the same as a usable translation: output that fails the independent
    validator is stored as 'needs_review', so 'available' always means
    "validated and displayable" and every count or filter on it is honest.
    The history row keeps the provider's own outcome for audit."""
    validation = result.get('validation') or {}
    if result['status'] in ('available', 'cached') and validation and not validation.get('passed', True):
        return 'needs_review'
    return result['status']


def _persist_translation_field(item_id, field, text, result):
    """Writes the append-only history row first (never overwritten, never
    deleted — the real versioned record), then upserts the fast-read
    "current" pointer row. A human-reviewed row is never touched by either
    write, matching the existing human-in-the-loop guarantee."""
    with psycopg.connect(DSN, autocommit=True) as c:
        locked = c.execute('''SELECT human_reviewed, content_version FROM news_item_translations
            WHERE item_id=%s AND field=%s AND target_language='fa' ''', (item_id, field)).fetchone()
        if locked and locked[0]:
            return 'skipped_human_reviewed'
        new_version = (locked[1] + 1) if locked else 1
        validation = result.get('validation') or {}
        quality_score = validation.get('quality_score')
        quality_flags = validation.get('flags') or []
        if result['status'] not in ('available', 'cached'):
            review_status = 'not_applicable'
        elif validation and not validation.get('passed', True):
            review_status = 'needs_review'
        else:
            review_status = 'pending_review'
        quality_status_legacy = None if not validation else ('ok' if validation.get('passed') else 'suspect')

        c.execute('''INSERT INTO news_item_translation_history(item_id,field,target_language,content_version,
            status,text,provider,model,prompt_version,input_text_sha256,quality_score,quality_flags,latency_ms,error,
            response_model,reported_cost_usd)
            VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (item_id, field, new_version, result['status'], result['text'], result.get('provider'), result.get('model'),
             result.get('prompt_version'), result.get('content_hash'), quality_score, Jsonb(quality_flags),
             result.get('latency_ms'), result.get('error'), result.get('response_model'), result.get('reported_cost_usd')))

        c.execute('''INSERT INTO news_item_translations(item_id,field,target_language,status,text,provider,model,
            content_version,source_chars,latency_ms,error,input_text_sha256,quality_status,
            prompt_version,quality_score,quality_flags,review_status,response_model)
            VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(item_id,field,target_language) DO UPDATE SET status=EXCLUDED.status,text=EXCLUDED.text,
            provider=EXCLUDED.provider,model=EXCLUDED.model,response_model=EXCLUDED.response_model,content_version=EXCLUDED.content_version,
            source_chars=EXCLUDED.source_chars,latency_ms=EXCLUDED.latency_ms,error=EXCLUDED.error,
            input_text_sha256=EXCLUDED.input_text_sha256,quality_status=EXCLUDED.quality_status,
            prompt_version=EXCLUDED.prompt_version,quality_score=EXCLUDED.quality_score,
            quality_flags=EXCLUDED.quality_flags,review_status=EXCLUDED.review_status,
            superseded_at=NULL,updated_at=now()
            WHERE news_item_translations.human_reviewed IS NOT TRUE''',
            (item_id, field, current_translation_status(result), result['text'], result.get('provider'), result.get('model'),
             new_version, len(text or ''), result.get('latency_ms'), result.get('error'),
             result.get('content_hash'), quality_status_legacy,
             result.get('prompt_version'), quality_score, Jsonb(quality_flags), review_status,
             result.get('response_model')))
    return f"{result['status']}"


def _persist_key_points(item_id, source_text, kp_result):
    with psycopg.connect(DSN, autocommit=True) as c:
        prev_version = c.execute('''SELECT COALESCE(max(content_version),0) FROM content_key_points
            WHERE item_id=%s''', (item_id,)).fetchone()[0]
        new_version = prev_version + 1
        if kp_result['status'] not in ('available', 'cached') or not kp_result['points']:
            return f"{kp_result['status']}:0_points"
        c.execute('UPDATE content_key_points SET superseded_at=now() WHERE item_id=%s AND superseded_at IS NULL', (item_id,))
        published = 0
        for point in kp_result['points']:
            if not point.get('evidence_verified'):
                continue  # fabricated-evidence points are never published, only logged in the AI Gateway audit trail
            c.execute('''INSERT INTO content_key_points(item_id,point_index,text_fa,evidence_span,evidence_verified,
                source_field,confidence,provider,model,prompt_version,content_version)
                VALUES(%s,%s,%s,%s,true,'original_text',%s,%s,%s,%s,%s)
                ON CONFLICT(item_id,point_index,content_version) DO NOTHING''',
                (item_id, point['index'], point['text'], point['evidence_span'],
                 point['validation'].get('quality_score'), kp_result.get('provider'), kp_result.get('model'),
                 kp_result.get('prompt_version'), new_version))
            published += 1
    return f"{kp_result['status']}:{published}_of_{len(kp_result['points'])}_points_published"


def process_translation(item_id):
    item = _fetch_item(item_id)
    if not item:
        return 'item_not_found'
    body = item['original_text'] if item['display_policy'] == 'full_syndicated' or item['extraction_status'] == 'available' else None
    publisher_summary = item['summary'] if item['summary'] and item['summary'].strip() else None
    gateway = gw.build_default_gateway(DSN)
    outcomes = []

    # Priority 1: Translate Title
    if item['title']:
        digest = gw.content_hash('translation', item['title'], gw.LATEST_PROMPT_VERSION['translation'])
        existing = q('''SELECT status,input_text_sha256,human_reviewed FROM news_item_translations
            WHERE item_id=%s AND field='title' AND target_language='fa' ''', (item_id,))
        if existing and existing[0][2]:
            outcomes.append('title:skipped_human_reviewed')
        elif existing and existing[0][0] == 'available' and existing[0][1] == digest:
            outcomes.append('title:unchanged_skip')
        else:
            result = ci.translate_to_persian(item['title'], gateway=gateway)
            outcomes.append(f'title:{_persist_translation_field(item_id, "title", item["title"], result)}')
    else:
        outcomes.append('title:no_source_text')

    # Priority 2: Translate Publisher Summary (strictly publisher summary, never body)
    if publisher_summary:
        digest = gw.content_hash('translation', publisher_summary, gw.LATEST_PROMPT_VERSION['translation'])
        existing = q('''SELECT status,input_text_sha256,human_reviewed FROM news_item_translations
            WHERE item_id=%s AND field='summary' AND target_language='fa' ''', (item_id,))
        if existing and existing[0][2]:
            outcomes.append('summary:skipped_human_reviewed')
        elif existing and existing[0][0] == 'available' and existing[0][1] == digest:
            outcomes.append('summary:unchanged_skip')
        else:
            result = ci.translate_to_persian(publisher_summary, gateway=gateway)
            outcomes.append(f'summary:{_persist_translation_field(item_id, "summary", publisher_summary, result)}')
    else:
        outcomes.append('summary:no_source_text')

    # Priority 3: Translate Article Body (only if body is available)
    if body:
        digest = gw.content_hash('translation', body, gw.LATEST_PROMPT_VERSION['translation'])
        existing = q('''SELECT status,input_text_sha256,human_reviewed FROM news_item_translations
            WHERE item_id=%s AND field='body' AND target_language='fa' ''', (item_id,))
        if existing and existing[0][2]:
            outcomes.append('body:skipped_human_reviewed')
        elif existing and existing[0][0] == 'available' and existing[0][1] == digest:
            outcomes.append('body:unchanged_skip')
        else:
            result = ci.translate_to_persian(body, gateway=gateway)
            outcomes.append(f'body:{_persist_translation_field(item_id, "body", body, result)}')
    else:
        outcomes.append('body:no_source_text')

    # Priority 4: AI Analytical Summaries (executive_summary, why_it_matters)
    analytical_context = body or publisher_summary
    for field, summary_fn in (('executive_summary', ci.generate_executive_summary), ('why_it_matters', ci.generate_why_it_matters)):
        if not analytical_context:
            outcomes.append(f'{field}:no_source_text')
            continue
        prompt_version = {'executive_summary': gw.EXECUTIVE_SUMMARY_PROMPT_VERSION,
                          'why_it_matters': gw.WHY_IT_MATTERS_PROMPT_VERSION}[field]
        digest = gw.content_hash('summary', analytical_context, prompt_version)
        existing = q('''SELECT status,input_text_sha256,human_reviewed FROM news_item_translations
            WHERE item_id=%s AND field=%s AND target_language='fa' ''', (item_id, field))
        if existing and existing[0][2]:
            outcomes.append(f'{field}:skipped_human_reviewed')
            continue
        if existing and existing[0][0] == 'available' and existing[0][1] == digest:
            outcomes.append(f'{field}:unchanged_skip')
            continue
        result = summary_fn(analytical_context, gateway=gateway)
        outcomes.append(f'{field}:{_persist_translation_field(item_id, field, analytical_context, result)}')

    # Priority 5: Key Points
    if analytical_context:
        kp_result = ci.extract_key_points(analytical_context, gateway=gateway)
        outcomes.append(f'key_points:{_persist_key_points(item_id, analytical_context, kp_result)}')
    else:
        outcomes.append('key_points:no_source_text')

    return '; '.join(outcomes)


# --------------------------------------------------------------------------- classification
def process_classification(item_id):
    item = _fetch_item(item_id)
    if not item:
        return 'item_not_found'
    locked = q('SELECT human_locked FROM item_classifications WHERE item_id=%s', (item_id,))
    if locked and locked[0][0]:
        return 'skipped_human_locked'
    body = item['original_text'] or item['summary']
    result = cv.classify(item['title'], body)
    evidence_topics = [e for e in result.evidence] + [s['label'] for s in result.subtopics]
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute('''INSERT INTO item_classifications(item_id,category_id,category_label,topics,taxonomy_version,
            method,confidence,reason,human_locked)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,false)
            ON CONFLICT(item_id) DO UPDATE SET category_id=EXCLUDED.category_id,category_label=EXCLUDED.category_label,
            topics=EXCLUDED.topics,taxonomy_version=EXCLUDED.taxonomy_version,method=EXCLUDED.method,
            confidence=EXCLUDED.confidence,reason=EXCLUDED.reason,classified_at=now()
            WHERE item_classifications.human_locked IS NOT TRUE''',
            (item_id, result.category_id, result.category_label, Jsonb(evidence_topics), result.taxonomy_version,
             result.method, result.confidence, 'matched: ' + ', '.join(evidence_topics[:8]) if evidence_topics else 'no keyword matched'))
        c.execute('''UPDATE news_items SET classification=%s,taxonomy_version=%s,topics=%s WHERE item_id=%s
            AND item_id NOT IN (SELECT item_id FROM item_classifications WHERE human_locked)''',
            (result.category_label, result.taxonomy_version, Jsonb(evidence_topics), item_id))
    return f'{result.category_id}:confidence={result.confidence}:subtopics={[s["id"] for s in result.subtopics]}'


# --------------------------------------------------------------------------- clustering
def process_clustering(item_ids, *, dry_run=False):
    rows = []
    for item_id in item_ids:
        item = _fetch_item(item_id)
        if not item:
            continue
        cat = q('SELECT category_id FROM item_classifications WHERE item_id=%s', (item_id,))
        rows.append(cl.ItemFeatures.build(
            item_id, item['title'], item['original_text'] or item['summary'] or '',
            item['published_at'], cat[0][0] if cat else None, item['canonical_url']))
    clusters = cl.cluster_items(rows)
    if dry_run:
        return clusters

    with psycopg.connect(DSN, autocommit=True) as c:
        # Idempotent by construction: the event_id is derived from the sorted
        # member set, so re-clustering unchanged input reproduces the same
        # event_id and INSERTs become no-ops / UPDATEs of the same row rather
        # than duplicate events.
        c.execute('''DELETE FROM news_event_members WHERE event_id IN
            (SELECT event_id FROM news_events WHERE clustering_method='distinctive_entity_v1')
            AND item_id = ANY(%s)''', (item_ids,))
        for cluster in clusters:
            event_id = hashlib.sha256('|'.join(cluster['members']).encode()).hexdigest()[:24]
            member_rows = [_fetch_item(m) for m in cluster['members']]
            member_rows = [m for m in member_rows if m]
            titles = [m['title'] for m in member_rows if m['title']]
            first_pub = min((m['published_at'] for m in member_rows if m['published_at']), default=None)
            last_pub = max((m['published_at'] for m in member_rows if m['published_at']), default=None)
            sources = q('SELECT DISTINCT source_id FROM news_items WHERE item_id = ANY(%s)', (cluster['members'],))
            c.execute('''INSERT INTO news_events(event_id,title,first_published_at,last_updated_at,source_count,
                member_count,clustering_method,algorithm_version)
                VALUES(%s,%s,%s,%s,%s,%s,'distinctive_entity_v1',%s)
                ON CONFLICT(event_id) DO UPDATE SET last_updated_at=EXCLUDED.last_updated_at,
                source_count=EXCLUDED.source_count,member_count=EXCLUDED.member_count,updated_at=now()''',
                (event_id, titles[0] if titles else 'رویداد بدون عنوان', first_pub, last_pub,
                 len(sources), len(cluster['members']), cl.ALGORITHM_VERSION))
            for m in cluster['members']:
                edge = next((e for e in cluster['edges'] if m in (e['a'], e['b'])), None)
                c.execute('''INSERT INTO news_event_members(event_id,item_id,similarity_score,membership_reason)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(event_id,item_id) DO UPDATE SET
                    similarity_score=EXCLUDED.similarity_score,membership_reason=EXCLUDED.membership_reason''',
                    (event_id, m, edge['score'] if edge else None, Jsonb(edge['reasons'] if edge else {})))
        # A re-cluster can drop an item_id from its old grouping (e.g. an
        # entity-extraction fix removes a false pairwise match). That item's
        # old event_id is never recomputed on its own, so its news_events row
        # would otherwise survive with zero members and a stale member_count.
        # Prune any event left with no members after the deletes/inserts above.
        c.execute('''DELETE FROM news_events e WHERE clustering_method='distinctive_entity_v1'
            AND NOT EXISTS (SELECT 1 FROM news_event_members m WHERE m.event_id = e.event_id)''')
    return clusters


# --------------------------------------------------------------------------- driver
def run_stage(stage, worker_id='pilot-worker', limit=None):
    processed, succeeded, failed = 0, 0, 0
    handler = {'extraction': process_extraction, 'media': process_media,
               'translation': process_translation, 'classification': process_classification}[stage]
    while limit is None or processed < limit:
        job = _claim_next(stage, worker_id)
        if not job:
            break
        processed += 1
        try:
            detail = handler(job['item_id'])
            _finish(job['job_id'], ok=True)
            succeeded += 1
            print(json.dumps({'stage': stage, 'item_id': job['item_id'], 'status': 'succeeded', 'detail': detail}, ensure_ascii=False))
        except Exception as exc:
            _finish(job['job_id'], ok=False, error=f'{type(exc).__name__}: {str(exc)[:200]}')
            failed += 1
            print(json.dumps({'stage': stage, 'item_id': job['item_id'], 'status': 'failed', 'error': str(exc)[:200]}, ensure_ascii=False))
    return {'stage': stage, 'processed': processed, 'succeeded': succeeded, 'failed': failed}


def enqueue_missing_articles(limit=250):
    """Find articles in news_items that lack full text extraction and queue them."""
    with psycopg.connect(DSN) as c:
        rows = c.execute('''
            SELECT n.item_id FROM news_items n
            LEFT JOIN news_item_content cn USING(item_id)
            WHERE (cn.extraction_status IS NULL OR cn.extraction_status NOT IN ('available', 'not_applicable'))
              AND (cn.original_text IS NULL OR length(trim(cn.original_text)) = 0)
              AND NOT EXISTS (
                  SELECT 1 FROM enrichment_jobs j 
                  WHERE j.item_id = n.item_id 
                    AND j.stage = 'extraction' 
                    AND j.status IN ('succeeded', 'processing', 'dead_letter')
              )
            ORDER BY n.published_at DESC NULLS LAST
            LIMIT %s
        ''', (limit,)).fetchall()
        
        if not rows:
            return 0
            
        item_ids = [r[0] for r in rows]
        for item_id in item_ids:
            job_id = _job_id(item_id, 'extraction')
            c.execute('''INSERT INTO enrichment_jobs(job_id,item_id,stage,status,available_at)
                VALUES(%s,%s,'extraction','pending',now())
                ON CONFLICT(item_id,stage) DO UPDATE SET
                    status='pending',
                    available_at=now(),
                    attempts=0,
                    updated_at=now()
                WHERE enrichment_jobs.status NOT IN ('succeeded', 'processing', 'dead_letter')''',
                (job_id, item_id))
        return len(item_ids)


def daemon_loop():
    """Continuously run enrichment workers in the background."""
    worker_id = f"worker-{os.getpid()}-{int(time.time())}"
    poll_interval = int(os.environ.get('ENRICHMENT_POLL_INTERVAL', '10'))
    print(f"Starting enrichment daemon [{worker_id}] with poll_interval={poll_interval}s...", flush=True)

    recovered = recover_stale_jobs(worker_id)
    if recovered:
        print(f"Recovered {recovered} stale jobs on startup", flush=True)

    n = enqueue_missing_articles(limit=200)
    if n:
        print(f"Enqueued {n} initial articles for extraction", flush=True)

    try:
        import publication_discovery as pd
        pd.run_discovery()
    except Exception as e:
        print(f"Publication discovery startup error: {e}", flush=True)

    last_scan = time.time()
    last_discovery = time.time()
    while True:
        try:
            now_sec = time.time()
            if now_sec - last_discovery > 600:
                try:
                    import publication_discovery as pd
                    pd.run_discovery()
                except Exception as e:
                    print(f"Publication discovery periodic error: {e}", flush=True)
                last_discovery = now_sec

            if now_sec - last_scan > 180:
                recover_stale_jobs(worker_id)
                enqueue_missing_articles(limit=200)
                last_scan = now_sec

            report = run_stage('extraction', worker_id=worker_id, limit=5)
            if report['processed'] > 0:
                print(f"Batch processed: {report}", flush=True)
            else:
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("Enrichment daemon stopped by user", flush=True)
            break
        except Exception as e:
            print(f"Enrichment loop error: {e}", file=sys.stderr, flush=True)
            time.sleep(poll_interval)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest')
    parser.add_argument('--enqueue', action='store_true')
    parser.add_argument('--enqueue-missing', action='store_true')
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--all-stages', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--recover-stale-jobs', action='store_true')
    args = parser.parse_args(argv)

    if args.daemon:
        daemon_loop()
        return 0

    if args.enqueue_missing:
        n = enqueue_missing_articles(limit=args.limit or 250)
        print(json.dumps({'enqueued': n}))
        return 0

    if args.recover_stale_jobs:
        n = recover_stale_jobs()
        print(json.dumps({'recovered': n}))
        return 0

    item_ids = None
    if args.manifest:
        manifest = json.loads(open(args.manifest, encoding='utf-8-sig').read())
        item_ids = [x['item_id'] for x in manifest['items']]

    if args.enqueue:
        if not item_ids:
            print('error: --enqueue requires --manifest', file=sys.stderr)
            return 2
        n = enqueue(item_ids, stages=[s for s in STAGES if s != 'clustering'])
        print(json.dumps({'enqueued': n, 'item_count': len(item_ids)}))
        return 0

    if args.stage and args.stage != 'clustering':
        report = run_stage(args.stage, limit=args.limit)
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if args.stage == 'clustering' or (args.all_stages and item_ids):
        if not item_ids:
            print('error: clustering requires --manifest', file=sys.stderr)
            return 2
        clusters = process_clustering(item_ids, dry_run=args.dry_run)
        print(json.dumps({'clusters': len(clusters), 'members': sum(len(c['members']) for c in clusters)}, ensure_ascii=False))
        return 0

    if args.all_stages:
        for stage in ('extraction', 'media', 'translation', 'classification'):
            print(json.dumps(run_stage(stage, limit=args.limit), ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
