"""Bounded live media pilot: at most 10 items, one invocation, sequential.

    python /app/media_pilot.py --manifest /m/pilot.json --dry-run   # zero requests
    NEWS_ARTICLE_MEDIA_FALLBACK_ENABLED=true python /app/media_pilot.py --manifest /m/pilot.json

Per item: if it has no eligible RSS primary, ONE guarded article-HTML
request reads Open Graph / JSON-LD metadata (flag-gated); then ONE guarded,
ranged GET validates the chosen primary image. Budgets: 10 article requests,
10 image validations, concurrency 1, retry 0. Stops at the first SSRF/security
refusal, oversize response or contract mismatch. Hosts not recorded as
robots-allowed and accessible are skipped without any request.
"""
import argparse
import json
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

import media_pipeline as mp

DSN = os.environ['DATABASE_URL']
MAX_ITEMS, MAX_ARTICLE, MAX_VALIDATE = 10, 10, 10
STOP_MARKERS = ('resolved_address_blocked', 'blocked_host', 'invalid_scheme', 'credentials_in_url', 'response_too_large',
                'too_many_redirects', 'redirect_without_location')


def allowed_hosts():
    path = os.path.join(os.getenv('COLLECTOR_METADATA_DIR', '/app/sources'), 'collection-capabilities.json')
    caps = json.load(open(path, encoding='utf-8-sig'))
    return {c['hostname'] for c in caps if c.get('robots_allowed') is True and c.get('access_status') == 'accessible'}


def run(manifest, dry_run):
    ids = [x['item_id'] for x in manifest['items']]
    if len(ids) > MAX_ITEMS:
        raise SystemExit('manifest_exceeds_10_items')
    hosts = allowed_hosts()
    rep = {'started_at': datetime.now(timezone.utc).isoformat(), 'dry_run': dry_run, 'fallback_enabled': mp.fallback_enabled(),
           'items': [], 'article_requests': 0, 'validation_requests': 0, 'retries': 0, 'stop_reason': None}
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        for iid in ids:
            n = c.execute('SELECT n.item_id, n.canonical_url, s.hostname FROM news_items n JOIN sources s USING (source_id) WHERE n.item_id=%s',
                          (iid,)).fetchone()
            if not n:
                rep['stop_reason'] = f'contract_mismatch:item_not_found:{iid[:12]}'
                break
            entry = {'item_id': iid, 'host': n['hostname'], 'actions': []}
            rep['items'].append(entry)
            primary = c.execute('''SELECT media_id, COALESCE(canonical_url,url) AS url, source_method, validation_status FROM news_item_media
                WHERE item_id=%s AND kind='image' AND is_primary''', (iid,)).fetchone()
            if not primary:
                if n['hostname'] not in hosts:
                    entry['actions'].append('skipped_host_not_allowed')
                    continue
                if dry_run:
                    entry['actions'].append('would_fetch_article_metadata')
                elif rep['article_requests'] >= MAX_ARTICLE:
                    entry['actions'].append('article_budget_exhausted')
                else:
                    cands, audit = mp.fetch_article_meta(n['canonical_url'])
                    rep['article_requests'] += audit.get('requests', 0)
                    entry['article'] = audit
                    entry['article_candidates'] = [{'method': cd.source_method, 'field': cd.source_field, 'url': cd.url,
                                                    'rejected': cd.rejection_reason} for cd in cands]
                    if audit.get('status') == 'error' and any(m in audit.get('error', '') for m in STOP_MARKERS):
                        rep['stop_reason'] = 'security_or_size:' + audit['error'][:80]
                        break
                    if audit.get('status') == 'disabled':
                        rep['stop_reason'] = 'contract_mismatch:fallback_flag_off'
                        break
                    if cands:
                        mp.persist(c, iid, cands)
                primary = c.execute('''SELECT media_id, COALESCE(canonical_url,url) AS url, source_method, validation_status
                    FROM news_item_media WHERE item_id=%s AND kind='image' AND is_primary''', (iid,)).fetchone()
            target = primary
            if not target:
                # An unproven candidate (e.g. HTML image with only a display size) can be validated to become primary.
                target = c.execute('''SELECT media_id, COALESCE(canonical_url,url) AS url, source_method, validation_status
                    FROM news_item_media WHERE item_id=%s AND kind='image' AND validation_status IN ('unknown','pending')
                    ORDER BY policy_score DESC NULLS LAST, position NULLS LAST LIMIT 1''', (iid,)).fetchone()
            if not target:
                entry['actions'].append('no_candidate_to_validate')
                continue
            entry['validate_url'] = target['url']
            if not host_allowed(urlhost(target['url']), hosts):
                entry['actions'].append('validation_skipped_host_not_allowed')
                continue
            if dry_run:
                entry['actions'].append('would_validate_image')
                continue
            if rep['validation_requests'] >= MAX_VALIDATE:
                entry['actions'].append('validation_budget_exhausted')
                continue
            v = mp.validate_image(target['url'])
            rep['validation_requests'] += v.get('requests', 0)
            entry['validation'] = v
            c.execute('''UPDATE news_item_media SET validation_status=%s, http_status=%s, validated_at=now(), updated_at=now(),
                width=COALESCE(%s, width), height=COALESCE(%s, height), policy_rejection_reason=CASE WHEN %s='rejected' THEN %s ELSE policy_rejection_reason END
                WHERE media_id=%s''', (v['validation_status'], v.get('http_status'), v.get('width'), v.get('height'),
                                       v['validation_status'], v.get('reason'), target['media_id']))
            mp.reselect_primary(c, iid)
            if v['validation_status'] == 'blocked' and any(m in (v.get('reason') or '') for m in STOP_MARKERS):
                rep['stop_reason'] = 'security_or_size:' + (v.get('reason') or '')[:80]
                break
            if v['validation_status'] == 'rejected' and 'response_too_large' in (v.get('reason') or ''):
                rep['stop_reason'] = 'oversize:' + target['url'][:60]
                break
            final = c.execute('''SELECT source_method, validation_status FROM news_item_media WHERE item_id=%s AND is_primary''', (iid,)).fetchone()
            entry['primary_after'] = final
        if dry_run:
            c.rollback()
    rep['finished_at'] = datetime.now(timezone.utc).isoformat()
    return rep


def host_allowed(host, hosts):
    """A recorded publisher host, or a subdomain of one (images.jfeed.com
    under jfeed.com). Nothing else is ever requested."""
    roots = {h[4:] if h.startswith('www.') else h for h in hosts}
    return host in hosts or any(host == r or host.endswith('.' + r) for r in roots)


def urlhost(u):
    from urllib.parse import urlsplit
    return (urlsplit(u).hostname or '').lower()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    print(json.dumps(run(json.load(open(a.manifest, encoding='utf-8')), a.dry_run), indent=1, default=str))
