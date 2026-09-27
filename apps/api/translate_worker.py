"""Bounded, resumable Persian translation and summarisation pass.

Run it against a limited batch, inspect the result, then widen. Every unit of
work is committed on its own, so the process can be stopped at any point and
restarted without repeating finished work or losing partial progress. With no
provider configured it performs no work and reports that, rather than writing
placeholder text.

    python /app/translate_worker.py --limit 5 --dry-run
    python /app/translate_worker.py --limit 5
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone

import psycopg

import ai_gateway as gw
import content_intelligence as ci

FIELDS = ('title', 'summary', 'body')
BODY_MAX_CHARS = int(os.getenv('NEWS_TRANSLATION_BODY_MAX_CHARS', '12000'))


def pending_items(conn, limit, fields, item_id=None, source_id=None):
    """Items missing at least one requested Persian field, newest first."""
    clauses, args = [], []
    if item_id:
        clauses.append('n.item_id=%s')
        args.append(item_id)
    if source_id:
        clauses.append('n.source_id=%s')
        args.append(source_id)
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = conn.execute(f'''
        SELECT n.item_id, n.title, COALESCE(n.summary_text,n.summary), c.original_text,
               COALESCE(c.display_policy,'link_only'), COALESCE(c.content_version,1)
        FROM news_items n LEFT JOIN news_item_content c ON c.item_id=n.item_id
        {where}
        ORDER BY COALESCE(n.published_at,n.fetched_at) DESC NULLS LAST, n.item_id
        LIMIT %s''', args + [limit * 4]).fetchall()
    done = {(r[0], r[1]) for r in conn.execute(
        "SELECT item_id,field FROM news_item_translations WHERE target_language='fa' AND status='available'").fetchall()}
    out = []
    for item_id_, title, summary, body, policy, version in rows:
        missing = [f for f in fields if (item_id_, f) not in done]
        if missing:
            out.append({'item_id': item_id_, 'title': title, 'summary': summary, 'body': body,
                        'display_policy': policy, 'content_version': version, 'missing': missing})
        if len(out) >= limit:
            break
    return out


def source_text(item, field):
    if field == 'title':
        return item['title']
    if field == 'summary':
        # A literal translation of the source's own summary field only —
        # never composed from body text. Mixing "translate the real summary"
        # with "summarize the article" under one field/task would misrepresent
        # translated_summary_fa as a faithful rendering of original_summary
        # when it was actually an AI-authored rewrite of different material.
        return item['summary'] or None
    return (item['body'] or '')[:BODY_MAX_CHARS] or None


def record(conn, item_id, field, version, text, result):
    from psycopg.types.json import Jsonb
    validation = result.get('validation') or {}
    quality_score = validation.get('quality_score')
    quality_flags = validation.get('flags') or []
    conn.execute('''INSERT INTO news_item_translations
        (item_id,field,target_language,status,text,provider,model,content_version,source_chars,latency_ms,error,
         input_text_sha256,prompt_version,quality_score,quality_flags)
        VALUES(%s,%s,'fa',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(item_id,field,target_language) DO UPDATE SET
        status=EXCLUDED.status,text=EXCLUDED.text,provider=EXCLUDED.provider,model=EXCLUDED.model,
        content_version=EXCLUDED.content_version,source_chars=EXCLUDED.source_chars,
        latency_ms=EXCLUDED.latency_ms,error=EXCLUDED.error,input_text_sha256=EXCLUDED.input_text_sha256,
        prompt_version=EXCLUDED.prompt_version,quality_score=EXCLUDED.quality_score,
        quality_flags=EXCLUDED.quality_flags,updated_at=now()
        WHERE news_item_translations.human_reviewed IS NOT TRUE''',
        (item_id, field, result['status'], result['text'], result.get('provider'), result.get('model'),
         version, len(text or ''), result.get('latency_ms'), result.get('error'),
         result.get('content_hash'), result.get('prompt_version'), quality_score, Jsonb(quality_flags)))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Translate stored news content into Persian.')
    parser.add_argument('--limit', type=int, default=5, help='maximum items to process')
    parser.add_argument('--fields', default='title,summary', help='comma separated: title,summary,body')
    parser.add_argument('--item-id', help='process a single item')
    parser.add_argument('--source-id', help='restrict to one source')
    parser.add_argument('--dry-run', action='store_true', help='report the plan without calling a provider')
    parser.add_argument('--sleep', type=float, default=float(os.getenv('NEWS_TRANSLATION_SLEEP_SECONDS', '1.0')),
                        help='pause between provider calls to respect rate limits')
    args = parser.parse_args(argv)

    fields = tuple(f.strip() for f in args.fields.split(',') if f.strip() in FIELDS)
    if not fields:
        print(json.dumps({'status': 'error', 'error': 'no_valid_fields'}))
        return 2

    gateway = gw.build_default_gateway(os.environ['DATABASE_URL'])
    configured = gateway.config.mode == gw.Mode.EXTERNAL_PROVIDER
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'provider': gateway.adapter.name,
              'mode': gateway.config.mode.value, 'provider_configured': configured, 'fields': list(fields),
              'limit': args.limit, 'dry_run': args.dry_run,
              'processed': 0, 'available': 0, 'errors': 0, 'skipped_no_source_text': 0, 'items': []}

    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.autocommit = True
        items = pending_items(conn, args.limit, fields, args.item_id, args.source_id)
        report['candidates'] = len(items)

        if not configured:
            report['status'] = 'provider_not_configured'
            report['note'] = ('Set AI_PROVIDER and AI_API_KEY to enable. '
                              'No text was written; every field stays pending.')
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        if args.dry_run:
            report['status'] = 'dry_run'
            report['items'] = [{'item_id': i['item_id'], 'missing': i['missing'],
                                'body_chars': len(i['body'] or ''), 'display_policy': i['display_policy']}
                               for i in items]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        for item in items:
            entry = {'item_id': item['item_id'], 'fields': {}}
            for field in item['missing']:
                text = source_text(item, field)
                if field == 'summary' and not text:
                    # Never invent a summary from other material when the
                    # source didn't provide one — record the honest reason
                    # and skip, rather than falling back to the article body.
                    result = {'status': 'source_summary_missing', 'text': None, 'provider': None, 'model': None,
                              'prompt_version': None, 'content_hash': None, 'latency_ms': None, 'error': None,
                              'validation': None}
                else:
                    result = ci.translate_to_persian(text, gateway=gateway)
                record(conn, item['item_id'], field, item['content_version'], text, result)
                entry['fields'][field] = result['status']
                report['processed'] += 1
                if result['status'] == 'available':
                    report['available'] += 1
                elif result['status'] == 'source_summary_missing':
                    report['skipped_no_source_text'] += 1
                elif result['status'] == 'error' and result.get('error') == 'no_source_text':
                    report['skipped_no_source_text'] += 1
                elif result['status'] == 'error':
                    report['errors'] += 1
                elif result['status'] == 'unavailable':
                    report['skipped_no_source_text'] += 1
                if result['status'] not in ('unavailable', 'pending') and args.sleep > 0:
                    time.sleep(args.sleep)
            report['items'].append(entry)

    report['status'] = 'completed'
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
