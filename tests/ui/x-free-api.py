"""X-FREE API integration test, run against the disposable test pair
(web 127.0.0.1:3003 -> news-api-xtest -> database iran_monitor_xtest).
Never run it against production or the preview on :3002 — it creates
clearly marked test-fixture posts.

    python tests/ui/x-free-api.py disabled   # ingest switch off
    python tests/ui/x-free-api.py enabled    # full write-path checks

Fixture posts use real registry handles with synthetic status ids and text
marked [TEST FIXTURE]; they exist only in the throwaway database.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:3003/api/v1/'
ORIGIN = 'http://127.0.0.1:3003'
results = []


def req(path, method='GET', body=None, headers=None, origin=ORIGIN, ctype='application/json'):
    h = dict(headers or {})
    if method != 'GET':
        h['content-type'] = ctype
        if origin:
            h['origin'] = origin
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b'{}')
        except ValueError:
            return e.code, {'raw': raw[:200].decode('utf-8', 'replace')}


def check(name, cond, detail=None):
    results.append({'name': name, 'pass': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' -> {str(detail)[:200]}'))


def token():
    s, d = req('social/csrf')
    return d.get('token')


def post(body, **kw):
    return req('social/manual-posts', 'POST', body, headers={'x-im-csrf': token() or ''}, **kw)


def disabled():
    s, d = req('social/status')
    check('status reports manual mode, no API, no scraping, no scheduler',
          s == 200 and d['mode'] == 'manual' and not d['official_api'] and not d['scraping'] and not d['scheduler'], d)
    check('status reports ingest disabled', d.get('manual_ingest_enabled') is False, d)
    s, d = req('social/csrf')
    check('csrf token refused while ingest disabled', s == 403 and d.get('detail') == 'manual_ingest_disabled', (s, d))
    s, d = req('social/manual-posts', 'POST', {'url': 'https://x.com/a/status/123456', 'analyst': 'qa bot'}, headers={'x-im-csrf': 'x.y'})
    check('POST refused while ingest disabled', s == 403 and d.get('detail') == 'manual_ingest_disabled', (s, d))
    s, d = req('social/accounts')
    check('36 accounts seeded from the registry manifest', s == 200 and d['total'] == 36, d.get('total'))


def enabled():
    s, accts = req('social/accounts')
    handles = {a['handle'][1:]: a['source_id'] for a in accts['accounts']}
    h1, h2 = sorted(handles)[0], sorted(handles)[1]
    s, ev = req('timeline/events?page_size=1')
    event_id = ev['events'][0]['event_id']
    s, feed = req('feed?page_size=1')
    item_id = feed['items'][0]['item_id']

    s, d = req('social/status')
    check('status reports ingest enabled in the test pair', d.get('manual_ingest_enabled') is True, d)

    # --- CSRF / origin / content type
    s, d = req('social/manual-posts', 'POST', {'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot'})
    check('missing CSRF token -> 403', s == 403 and d.get('detail') == 'csrf_token_invalid', (s, d))
    s, d = post({'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot'}, origin='https://evil.example')
    check('foreign Origin -> 403', s == 403 and d.get('detail') == 'origin_not_allowed', (s, d))
    s, d = req('social/manual-posts', 'POST', b'url=https://x.com/a/status/1', headers={'x-im-csrf': token()},
               ctype='application/x-www-form-urlencoded')
    check('non-JSON (cross-site form) -> 415', s == 415, (s, d))
    s, d = post({'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot', 'evil_field': 1})
    check('unknown field -> 422', s == 422, (s, d))

    # --- URL validation
    for url, code in [
        (f'https://x.com.evil.io/{h1}/status/900000000000000009', 'url_host_not_x'),
        (f'https://t.co/abcdef', 'url_host_not_x'),
        (f'http://x.com/{h1}/status/900000000000000009', 'url_not_https'),
        (f'https://x.com/{h1}', 'url_not_a_status_link'),
        ('https://x.com/elonmusk/status/900000000000000009', 'handle_not_in_registry'),
    ]:
        s, d = post({'url': url, 'analyst': 'qa bot'})
        check(f'rejects {url[:48]} as {code}', s == 422 and d.get('detail') == code, (s, d))

    # --- dry run writes nothing
    s, d = post({'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot', 'dry_run': True})
    check('dry_run returns the record without writing', s == 200 and d.get('dry_run') is True, (s, d))
    s, d = req('social/posts/900000000000000001')
    check('dry_run left nothing behind', s == 404, s)

    # --- create: link only (no text)
    s, p1 = post({'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot', 'importance': 'high',
                  'topic_id': 'security_defense', 'event_id': event_id, 'related_item_id': item_id,
                  'analyst_note': '[TEST FIXTURE] link-only registration'})
    check('create link-only post', s == 200 and p1.get('post_id') == '900000000000000001', (s, p1))
    check('no text invented: availability link_only, text not recorded',
          p1.get('original_text') is None and p1.get('availability_status') == 'link_only'
          and p1['provenance_json']['text_source'] == 'not_recorded', p1)
    check('provenance: manual, not fetched from X, not API output',
          p1['provenance_json']['fetched_from_x'] is False and p1['provenance_json']['text_is_x_api_output'] is False
          and p1['provenance_json']['registered_by'] == 'qa bot', p1['provenance_json'])
    check('event and news links stored', p1.get('event_id') == event_id and p1.get('related_item_id') == item_id, p1)
    check('history row "created"', [h['action'] for h in p1.get('history', [])] == ['created'], p1.get('history'))

    # --- create via twitter.com with text + XSS payload
    xss = '[TEST FIXTURE] <script>alert("xss")</script><img src=x onerror=alert(2)> Israel intercepts drones over Eilat'
    s, p2 = post({'url': f'https://twitter.com/{h2.upper()}/status/900000000000000002?s=20', 'analyst': 'qa bot',
                  'original_text': xss, 'importance': 'medium', 'verification_status': 'verified',
                  'topic_id': 'regional_geopolitics', 'published_at': '2026-09-28T09:30:00Z'})
    check('create via twitter.com canonicalises to x.com', s == 200 and p2.get('post_url') == f'https://x.com/{h2.upper()}/status/900000000000000002', (s, p2))
    check('HTML/script stored verbatim as inert text', p2.get('original_text') == xss, p2.get('original_text'))
    check('analyst text provenance recorded', p2['provenance_json']['text_source'] == 'analyst_entered' and p2['availability_status'] == 'text_recorded', p2['provenance_json'])

    # --- duplicates
    s, d = post({'url': f'https://x.com/{h1}/status/900000000000000001', 'analyst': 'qa bot'})
    check('duplicate (same URL) -> 409', s == 409 and d.get('detail') == 'duplicate_post', (s, d))
    s, d = post({'url': f'https://twitter.com/{h1}/status/900000000000000001', 'analyst': 'qa bot'})
    check('duplicate (same id via twitter.com) -> 409', s == 409, (s, d))

    # --- account counters
    s, a = req(f'social/accounts/{handles[h1]}')
    check('account post_count and last_manual_post_at maintained', a['post_count'] == 1 and a['last_manual_post_at'], a)

    # --- filters
    s, d = req(f'social/posts?source_id={handles[h1]}')
    check('filter by account', d['total'] == 1 and d['posts'][0]['post_id'] == '900000000000000001', d.get('total'))
    s, d = req('social/posts?topic=regional_geopolitics')
    check('filter by topic', d['total'] == 1 and d['posts'][0]['post_id'] == '900000000000000002', d.get('total'))
    s, d = req('social/posts?has_event=true')
    check('filter has_event', d['total'] == 1 and d['posts'][0]['event_id'] == event_id, d.get('total'))
    s, d = req('social/posts?importance=high')
    check('filter importance', d['total'] == 1, d.get('total'))
    s, d = req('social/posts?verification=verified')
    check('filter verification', d['total'] == 1, d.get('total'))
    s, d = req('social/posts?date_from=2026-09-28&date_to=2026-09-28')
    check('filter date range (published_at)', any(p['post_id'] == '900000000000000002' for p in d['posts']), d.get('total'))
    s, d = req('social/posts?has_translation=true')
    check('filter has_translation (none yet)', d['total'] == 0, d.get('total'))

    # --- patch, history, soft delete
    s, d = req('social/manual-posts/900000000000000001', 'PATCH',
               {'analyst': 'qa bot', 'verification_status': 'disputed', 'original_text': '[TEST FIXTURE] text added later'},
               headers={'x-im-csrf': token()})
    check('PATCH updates fields', s == 200 and d['verification_status'] == 'disputed' and d['availability_status'] == 'text_recorded', (s, d))
    check('PATCH appends history with previous values',
          d['history'][-1]['action'] == 'updated' and d['history'][-1]['previous_value_json'].get('verification_status') == 'unverified', d['history'])
    s, d = req('social/manual-posts/900000000000000001', 'PATCH', {'analyst': 'qa bot', 'availability_status': 'withdrawn'},
               headers={'x-im-csrf': token()})
    check('withdraw instead of delete', s == 200 and d['availability_status'] == 'withdrawn'
          and d['history'][-1]['action'] == 'availability_changed', (s, d.get('history')))
    s, d = req('social/posts')
    check('withdrawn post hidden from the default stream', all(p['post_id'] != '900000000000000001' for p in d['posts']), d.get('total'))
    s, d = req('social/posts/900000000000000001')
    check('withdrawn post still retrievable with full history', s == 200 and len(d['history']) == 3, (s, len(d.get('history', []))))
    s, d = req('social/manual-posts/900000000000000001', 'DELETE', {}, headers={'x-im-csrf': token()})
    check('no physical delete endpoint', s in (404, 405), s)

    # --- optional AI / rule actions (provider disabled in the test pair)
    for action in ('classify', 'entities', 'suggest_event'):
        s, d = req('social/posts/900000000000000002/ai', 'POST', {'analyst': 'qa bot', 'action': action}, headers={'x-im-csrf': token()})
        check(f'rule action {action} runs on request and is labelled', s == 200 and d['audit']['kind'] == 'rule'
              and d['post']['history'][-1]['action'] == 'ai_' + action, (s, d.get('audit')))
    s, d = req('social/posts/900000000000000002/ai', 'POST', {'analyst': 'qa bot', 'action': 'translate'}, headers={'x-im-csrf': token()})
    check('translate with provider unavailable: honest status, post intact',
          s == 200 and d['status'] == 'provider_not_configured' and d['post']['translated_text_fa'] is None
          and d['post']['original_text'] == xss, (s, d.get('status')))
    s, d = req('social/posts/900000000000000002/ai', 'POST', {'analyst': 'qa bot', 'action': 'hack'}, headers={'x-im-csrf': token()})
    check('unknown AI action refused', s == 422, (s, d))
    s, d = req('social/stats')
    check('stats consistent', s == 200 and d['accounts'] == 36 and d['posts'] == 1 and d['accounts_without_posts'] == 35, d)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'enabled'
    (disabled if mode == 'disabled' else enabled)()
    failed = [r for r in results if not r['pass']]
    print(f'\nX-FREE API {mode}: {len(results) - len(failed)}/{len(results)} passed')
    sys.exit(1 if failed else 0)
