import json,urllib.error,urllib.parse,urllib.request,pathlib,re
baseline=json.loads(pathlib.Path('runtime/evidence/phase-8b/baseline.json').read_text(encoding='utf-8-sig'))
BASE='http://127.0.0.1:3001/api/v1/'
def get(path):
    with urllib.request.urlopen(BASE+path,timeout=30) as r:
        assert r.status==200;return json.load(r)
coverage=get('sources/coverage')
EXPECTED_SOURCES=coverage['executable']
h=get('health');assert h['status']=='ok' and h['items']>=282 and h['sources']==EXPECTED_SOURCES,(h['sources'],EXPECTED_SOURCES)
assert isinstance(h['scheduler_enabled'],bool)
assert get('collection/status')['scheduler_enabled']==h['scheduler_enabled']
allnews=get('news?page_size=100&page=1');assert allnews['total']==h['items'] and len(allnews['items'])==100
items=[]
for page in range(1,(allnews['total']+99)//100+1):
    batch=get(f'news?page_size=100&page={page}')
    assert batch['total']==allnews['total'] and batch['page']==page
    assert 0<len(batch['items'])<=100
    items.extend(batch['items'])
assert len(items)==allnews['total'] and len({x['item_id'] for x in items})==len(items);assert len({x['canonical_url'] for x in items})==len(items)
ordering=[x['published_at'] or x['fetched_at'] for x in items];assert ordering==sorted(ordering,reverse=True)
old={x['item_id']:x for x in baseline['db']['items']};after={x['item_id']:x for x in items};assert set(old).issubset(after)
for item_id,b in old.items():
 a=after[item_id]
 for key in ('source_id','title','canonical_url','external_guid','published_at','summary','provenance_status'):
  assert a.get(key)==b.get(key),(item_id,key)
 assert a.get('content_language') is None,(item_id,'historical_language_must_remain_unknown')
sources=get('sources?page_size=100')['sources'];assert len(sources)==EXPECTED_SOURCES and all(x['display_name'] and x['hostname'] for x in sources)
assert all(not __import__('re').fullmatch(r'[0-9a-f-]{36}',x['display_name'] or '') for x in sources)
assert sum(x['enabled_for_scheduler'] for x in sources)==EXPECTED_SOURCES
for s in [x for x in sources if x['item_count']>0][:5]:
    d=get('sources/'+s['source_id']);assert d['source_id']==s['source_id'] and d['latest_items'] is not None
    assert all(x['source_id']==s['source_id'] for x in d['latest_items'])
selected=next(x['source_id'] for x in sources if x['item_count']>0);filtered=get('news?source_id='+selected+'&page_size=30');assert filtered['items'] and all(x['source_id']==selected for x in filtered['items'])
category=next((x['category'] for x in items if x['category']),None)
assert category and get('news?category='+urllib.parse.quote(category))['items']
assert get('news?window=all&sort=oldest&page_size=2')['items'][0]['item_id']!=allnews['items'][0]['item_id']
assert get('news?search='+urllib.parse.quote(items[0]['title'][:20]))['items']
for endpoint in ['stats/overview','stats/timeline?window=24h','stats/timeline?window=7d','stats/timeline?window=30d','stats/sources','stats/topics','stats/quality','stats/brief?window=24h','collection/status','collection/runs?page_size=10','taxonomy']:
    assert get(endpoint) is not None,endpoint
assert get('collection/runs')['runs']
assert coverage['registered']==62 and coverage['executable']<=coverage['registered'] and coverage['monitored']<=coverage['executable']
assert len(coverage['sources'])==coverage['registered'] and all(x['coverage_state'] and x['reason'] for x in coverage['sources'])
assert coverage['by_state'].get('not_covered',0)==36
content=get('stats/content');assert content['total_items']==h['items'] and 'translations_fa' in content
assert get('stats/overview')['total_items']==h['items']
last_run=get('stats/overview')['last_run']
assert last_run is None or (isinstance(last_run,dict) and 'finished_at' in last_run),'last_run must be an object, not a positional array'
img=get('news?has_image=true&page_size=5');assert img['total']>=0 and all(len(x.get('lead_image_url') or '')>0 for x in img['items'])
noimg=get('news?has_image=false&page_size=5');assert all(not x.get('lead_image_url') for x in noimg['items'])
doc=get('news?has_document=true&page_size=1');assert doc['total']>=0
for status in ('available','pending','unavailable'):
    r=get('news?translation='+status+'&page_size=1');assert r['total']>=0,status
try:get('news?translation=not-a-status')
except urllib.error.HTTPError as e:assert e.code==422
else:raise AssertionError('invalid_translation_filter_not_rejected')
try:get('news?window=invalid')
except urllib.error.HTTPError as e:assert e.code==422
else:raise AssertionError('invalid_filter_not_rejected')
try:get('news/does-not-exist')
except urllib.error.HTTPError as e:assert e.code==404
else:raise AssertionError('missing_item_not_404')
assert get('news/'+items[0]['item_id'])['item_id']==items[0]['item_id']
topic=next((t for t in get('stats/topics')['topics'] if t['count']>0),None)
if topic:
    byt=get('news?topic='+urllib.parse.quote(topic['topic']))
    assert byt['total']==topic['count'],(byt['total'],topic['count'])
    assert all(topic['topic'] in (x['topics'] or []) for x in byt['items'])
print(f"API_SMOKE_PASS sources={EXPECTED_SOURCES} items={h['items']} registered={coverage['registered']} monitored={coverage['monitored']}")
