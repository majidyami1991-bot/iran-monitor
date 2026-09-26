"""Additive PostgreSQL metadata, bounded operational read APIs and migrations."""
import json, os, re, math, dataclasses
from datetime import datetime, date, time, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID
from pathlib import Path
from urllib.parse import urlsplit
import psycopg
from fastapi import HTTPException, Query, Response
import classify_v2 as cv
import ai_gateway as aig

DSN=os.environ['DATABASE_URL']
INTERVAL=int(os.getenv('NEWS_COLLECTION_INTERVAL_SECONDS','900'))
ROOT=Path('/app')
METADATA_DIR=Path(os.getenv('COLLECTOR_METADATA_DIR','/app/sources'))
METADATA_FILES=('source-registry.json','rss-execution-readiness.json','collection-capabilities.json','classification-taxonomy-v1.json','feed-sitemap-discovery.json')
def _metadata(name):
    path=METADATA_DIR/name
    if not path.is_file(): raise RuntimeError(f'collector_metadata_missing:{name}:{METADATA_DIR}')
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as exc: raise RuntimeError(f'collector_metadata_invalid:{name}') from exc

def to_json_compatible(value, *, path='$'):
    """Recursively normalize JSON/JSONB values; reject ambiguous or unknown types."""
    if value is None or isinstance(value,(str,int,bool)): return value
    if isinstance(value,float):
        if not math.isfinite(value): raise TypeError(f'unsupported_json_value:{path}:non_finite_float')
        return value
    if isinstance(value,datetime):
        if value.tzinfo is None or value.utcoffset() is None: raise TypeError(f'unsupported_json_type:{path}:naive_datetime')
        return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    if isinstance(value,date) and not isinstance(value,datetime): return value.isoformat()
    if isinstance(value,time):
        if value.tzinfo is None or value.utcoffset() is None: raise TypeError(f'unsupported_json_type:{path}:naive_time')
        return value.isoformat()
    if isinstance(value,UUID): return str(value).lower()
    if isinstance(value,Decimal): return format(value,'f')
    if isinstance(value,Enum): return to_json_compatible(value.value,path=path)
    if isinstance(value,Path): return str(value)
    if dataclasses.is_dataclass(value) and not isinstance(value,type): return to_json_compatible(dataclasses.asdict(value),path=path)
    if hasattr(value,'model_dump'): return to_json_compatible(value.model_dump(mode='python'),path=path)
    if isinstance(value,(list,tuple)): return [to_json_compatible(v,path=f'{path}[{i}]') for i,v in enumerate(value)]
    if isinstance(value,dict):
        out={}
        for k,v in value.items():
            if not isinstance(k,str): raise TypeError(f'unsupported_json_key:{path}:{type(k).__name__}')
            out[k]=to_json_compatible(v,path=f'{path}.{k}')
        return out
    raise TypeError(f'unsupported_json_type:{path}:{type(value).__name__}')

def canonical_json_dumps(value):
    return json.dumps(to_json_compatible(value),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def database_json(value, *, path='$'):
    return to_json_compatible(value,path=path)

DDL='''
ALTER TABLE sources ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS category text;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS feed_url text;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS language text;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS enabled_for_scheduler boolean NOT NULL DEFAULT false;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_attempt_at timestamptz;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_success_at timestamptz;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_http_status integer;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_item_at timestamptz;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS consecutive_failures integer NOT NULL DEFAULT 0;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS health_status text NOT NULL DEFAULT 'not_run';
ALTER TABLE sources ADD COLUMN IF NOT EXISTS source_url text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS summary_source text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS summary_available boolean;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS content_language text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS fetched_at timestamptz;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS summary_raw text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS summary_text text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS classification text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS taxonomy_version text;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS topics jsonb NOT NULL DEFAULT '[]'::jsonb;
CREATE TABLE IF NOT EXISTS item_classifications(item_id text PRIMARY KEY REFERENCES news_items(item_id),category_id text NOT NULL,category_label text NOT NULL,topics jsonb NOT NULL DEFAULT '[]'::jsonb,taxonomy_version text NOT NULL,method text NOT NULL,classified_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS collection_runs(run_id text PRIMARY KEY,started_at timestamptz NOT NULL,finished_at timestamptz,trigger_type text NOT NULL,status text NOT NULL,sources_planned integer NOT NULL DEFAULT 11,sources_attempted integer NOT NULL DEFAULT 0,sources_succeeded integer NOT NULL DEFAULT 0,sources_failed integer NOT NULL DEFAULT 0,http_requests integer NOT NULL DEFAULT 0,response_bytes bigint NOT NULL DEFAULT 0,items_observed integer NOT NULL DEFAULT 0,items_inserted integer NOT NULL DEFAULT 0,duplicates integer NOT NULL DEFAULT 0,updates integer NOT NULL DEFAULT 0,rejected integer NOT NULL DEFAULT 0,error_summary text,collector_version text NOT NULL,skipped_locked boolean NOT NULL DEFAULT false);
CREATE TABLE IF NOT EXISTS source_run_results(run_id text NOT NULL REFERENCES collection_runs(run_id),source_id text NOT NULL REFERENCES sources(source_id),started_at timestamptz NOT NULL,finished_at timestamptz,status text NOT NULL,http_status integer,response_bytes bigint NOT NULL DEFAULT 0,observed integer NOT NULL DEFAULT 0,inserted integer NOT NULL DEFAULT 0,duplicates integer NOT NULL DEFAULT 0,rejected integer NOT NULL DEFAULT 0,error_class text,error_message_sanitized text,PRIMARY KEY(run_id,source_id));
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS error_stage text;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS diagnostic_json jsonb;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS http_requests integer NOT NULL DEFAULT 0;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS updates integer;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS response_sha256 text;
ALTER TABLE source_run_results ADD COLUMN IF NOT EXISTS checkpoint_payload jsonb;
ALTER TABLE collection_runs ADD COLUMN IF NOT EXISTS repaired_at timestamptz;
ALTER TABLE collection_runs ADD COLUMN IF NOT EXISTS repair_reason text;
ALTER TABLE collection_runs ALTER COLUMN updates DROP NOT NULL;
CREATE INDEX IF NOT EXISTS collection_runs_started_idx ON collection_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS source_run_results_source_idx ON source_run_results(source_id,finished_at DESC);
CREATE INDEX IF NOT EXISTS news_items_fetched_idx ON news_items(fetched_at DESC);
CREATE INDEX IF NOT EXISTS news_items_category_idx ON news_items(classification);
CREATE TABLE IF NOT EXISTS news_item_content(
  item_id text PRIMARY KEY REFERENCES news_items(item_id),
  content_version integer NOT NULL DEFAULT 1,
  original_language text,
  original_text text,
  text_chars integer NOT NULL DEFAULT 0,
  extraction_method text NOT NULL,
  extraction_status text NOT NULL,
  display_policy text NOT NULL,
  source_url text,
  content_sha256 text,
  extracted_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS news_item_translations(
  item_id text NOT NULL REFERENCES news_items(item_id),
  field text NOT NULL,
  target_language text NOT NULL DEFAULT 'fa',
  status text NOT NULL,
  text text,
  provider text,
  model text,
  content_version integer NOT NULL DEFAULT 1,
  source_chars integer,
  latency_ms integer,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(item_id,field,target_language));
CREATE TABLE IF NOT EXISTS news_item_media(
  media_id text PRIMARY KEY,
  item_id text NOT NULL REFERENCES news_items(item_id),
  kind text NOT NULL,
  url text NOT NULL,
  mime_type text,
  byte_size bigint,
  declared_width integer,
  declared_height integer,
  alt_text text,
  position integer,
  relevance text NOT NULL,
  rejection_reason text,
  discovery_method text NOT NULL,
  verification_status text NOT NULL DEFAULT 'unverified',
  content_sha256 text,
  discovered_at timestamptz NOT NULL DEFAULT now(),
  verified_at timestamptz);
CREATE INDEX IF NOT EXISTS news_item_media_item_idx ON news_item_media(item_id,relevance,position);
CREATE INDEX IF NOT EXISTS news_item_translations_status_idx ON news_item_translations(status,field);
CREATE INDEX IF NOT EXISTS news_item_content_status_idx ON news_item_content(extraction_status);

-- Phase: content enrichment pilot. Additive only; nothing above is altered
-- in a way that could lose data, and every ALTER is IF NOT EXISTS / guarded.
ALTER TABLE news_item_content ADD COLUMN IF NOT EXISTS content_type text;
ALTER TABLE news_item_content ADD COLUMN IF NOT EXISTS copyright_status text;
ALTER TABLE news_item_content ADD COLUMN IF NOT EXISTS unavailable_reason text;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS input_text_sha256 text;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS quality_status text;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS human_reviewed boolean NOT NULL DEFAULT false;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS human_reviewed_at timestamptz;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS caption text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS attribution text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS copyright_status text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS document_title text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS security_status text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS verified_mime text;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS verified_width integer;
ALTER TABLE news_item_media ADD COLUMN IF NOT EXISTS verified_height integer;
ALTER TABLE item_classifications ADD COLUMN IF NOT EXISTS confidence real;
ALTER TABLE item_classifications ADD COLUMN IF NOT EXISTS reason text;
ALTER TABLE item_classifications ADD COLUMN IF NOT EXISTS human_locked boolean NOT NULL DEFAULT false;
ALTER TABLE item_classifications ADD COLUMN IF NOT EXISTS human_edited_at timestamptz;
CREATE TABLE IF NOT EXISTS news_events(
  event_id text PRIMARY KEY,
  title text NOT NULL,
  first_published_at timestamptz,
  last_updated_at timestamptz,
  source_count integer NOT NULL DEFAULT 0,
  member_count integer NOT NULL DEFAULT 0,
  clustering_method text NOT NULL,
  algorithm_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS news_event_members(
  event_id text NOT NULL REFERENCES news_events(event_id),
  item_id text NOT NULL REFERENCES news_items(item_id),
  similarity_score real,
  membership_reason jsonb,
  manually_removed boolean NOT NULL DEFAULT false,
  added_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(event_id,item_id));
CREATE INDEX IF NOT EXISTS news_event_members_item_idx ON news_event_members(item_id) WHERE NOT manually_removed;
CREATE TABLE IF NOT EXISTS enrichment_jobs(
  job_id text PRIMARY KEY,
  item_id text NOT NULL REFERENCES news_items(item_id),
  stage text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3,
  last_error text,
  locked_at timestamptz,
  locked_by text,
  available_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(item_id,stage));
CREATE INDEX IF NOT EXISTS enrichment_jobs_pickup_idx ON enrichment_jobs(status,available_at);

-- AI Gateway: audit log (every call, success or not) and response cache
-- (keyed so a provider or prompt-version change is a cache miss, never a
-- silent reuse of another provider's or prompt version's output).
CREATE TABLE IF NOT EXISTS ai_requests_log(
  request_id bigserial PRIMARY KEY,
  task_type text NOT NULL,
  provider text,
  model text,
  prompt_version text NOT NULL,
  content_sha256 text NOT NULL,
  status text NOT NULL,
  latency_ms integer,
  tokens_in integer,
  tokens_out integer,
  estimated_cost_usd numeric(12,6),
  cache_hit boolean NOT NULL DEFAULT false,
  error text,
  created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ai_requests_log_created_idx ON ai_requests_log(created_at);
CREATE INDEX IF NOT EXISTS ai_requests_log_task_idx ON ai_requests_log(task_type,status);

CREATE TABLE IF NOT EXISTS ai_response_cache(
  content_sha256 text NOT NULL,
  task_type text NOT NULL,
  prompt_version text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL DEFAULT '',
  response_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(content_sha256,task_type,prompt_version,provider,model));

-- Content Intelligence: additive columns on the existing per-field
-- translation table (never a new copy of original_title/original_language/
-- original_summary/original_content_excerpt — those already live on
-- news_items and news_item_content and stay untouched; see
-- docs/CONTENT INTELLIGENCE ARCHITECTURE.md "Data model" for the mapping).
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS prompt_version text;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS quality_score real;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS review_status text NOT NULL DEFAULT 'not_applicable';
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS reviewed_by text;
ALTER TABLE news_item_translations ADD COLUMN IF NOT EXISTS superseded_at timestamptz;

-- Append-only history: the "current" row above may be updated in place (as
-- it already was before this phase, for fast reads), but every generation
-- attempt is also recorded here and never deleted or overwritten — this is
-- the actual versioned record the brief requires. Re-running a task inserts
-- a new content_version here and stamps the *previous* current row's
-- superseded_at above; nothing is destroyed.
CREATE TABLE IF NOT EXISTS news_item_translation_history(
  history_id bigserial PRIMARY KEY,
  item_id text NOT NULL REFERENCES news_items(item_id),
  field text NOT NULL,
  target_language text NOT NULL DEFAULT 'fa',
  content_version integer NOT NULL,
  status text NOT NULL,
  text text,
  provider text,
  model text,
  prompt_version text,
  input_text_sha256 text,
  quality_score real,
  quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
  latency_ms integer,
  error text,
  generated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS news_item_translation_history_item_idx ON news_item_translation_history(item_id,field,target_language,content_version);

-- Key points: a new concept (not a duplicate of anything existing), one row
-- per extracted point, each carrying its own evidence span so a reviewer
-- (or an automated check) can verify the point against the source text
-- rather than trusting it blindly.
CREATE TABLE IF NOT EXISTS content_key_points(
  point_id bigserial PRIMARY KEY,
  item_id text NOT NULL REFERENCES news_items(item_id),
  point_index integer NOT NULL,
  text_fa text NOT NULL,
  evidence_span text,
  evidence_verified boolean NOT NULL DEFAULT false,
  source_field text NOT NULL DEFAULT 'original_text',
  confidence real,
  provider text,
  model text,
  prompt_version text,
  content_version integer NOT NULL DEFAULT 1,
  superseded_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(item_id,point_index,content_version));
CREATE INDEX IF NOT EXISTS content_key_points_item_idx ON content_key_points(item_id) WHERE superseded_at IS NULL;
'''
REGISTRY=_metadata('source-registry.json')
READY=_metadata('rss-execution-readiness.json')
CAPS=_metadata('collection-capabilities.json')
TAX=_metadata('classification-taxonomy-v1.json')
TAX2=_metadata('classification-taxonomy-v2.json')
DISC=_metadata('feed-sitemap-discovery.json')
EXEC={x['source_id']:x for x in READY if x.get('executable') is True}
CAP={x['source_id']:x for x in CAPS}
REG={x['source_id']:x for x in REGISTRY}
DISCOVERY={x['source_id']:x for x in DISC}

def q(sql,args=()):
    with psycopg.connect(DSN) as c:return c.execute(sql,args).fetchall()

def objects(sql,keys,args=()):
    return [dict(zip(keys,row)) for row in q(sql,args)]

def canonical_source(x):
    raw=x.get('canonical_key') or x.get('canonical_url') or x.get('url')
    p=urlsplit(raw or '')
    return raw if p.scheme in ('https','http') and p.hostname and not p.username and not p.password else None

def classify(title,summary):
    safe_title=title if isinstance(title,str) else ''
    safe_summary=summary if isinstance(summary,str) else ''
    text=(' '+(safe_title+' '+safe_summary).casefold().replace('\u200c',' ')+' ')
    labels=[]; topics=[]
    for category in TAX.get('categories',[]) if isinstance(TAX.get('categories',[]),list) else []:
        if not isinstance(category,dict):continue
        hits=[]
        words=(category.get('keywords_en') if isinstance(category.get('keywords_en'),list) else [])+(category.get('keywords_fa') if isinstance(category.get('keywords_fa'),list) else [])
        for word in words:
            if not isinstance(word,str):continue
            needle=word.casefold()
            found=(needle in text) if len(needle.strip())>4 and any(ord(ch)>127 for ch in needle) else (' '+needle.strip()+' ' in text)
            if found:hits.append(word.strip())
        if hits:
            labels.append(category)
            topics.extend(hits)
    primary=labels[0] if labels else TAX.get('fallback',{'id':'other','label':'سایر'})
    return primary, list(dict.fromkeys(topics)), [x['id'] for x in labels]

def migrate():
    with psycopg.connect(DSN) as c:
        c.execute(DDL)
        # A source validated for execution must exist as a row before a cycle can
        # record results against it; the update below cannot create one.
        for sid,r in REG.items():
            if sid not in EXEC:continue
            canonical=canonical_source(r); host=r.get('hostname') or (urlsplit(canonical).hostname if canonical else None)
            c.execute('INSERT INTO sources(source_id,name,hostname,source_type,canonical_url,enabled,enabled_for_scheduler) VALUES(%s,%s,%s,%s,%s,false,true) ON CONFLICT(source_id) DO NOTHING',(sid,host,host,r.get('source_type'),canonical))
        for sid,r in REG.items():
            canonical=canonical_source(r); host=r.get('hostname') or (urlsplit(canonical).hostname if canonical else None)
            readiness=EXEC.get(sid); cap=CAP.get(sid,{})
            display=r.get('publisher_name') or r.get('display_name') or r.get('title')
            # Registry currently records canonical URLs and hostnames, not publisher brands.
            if display and display.startswith(('http://','https://')):display=None
            safe_name=display or host
            tier=(readiness.get('implementation_tier') if readiness else None) or cap.get('implementation_tier') or ('TIER_1_FEED' if readiness else None)
            c.execute('''UPDATE sources SET name=%s,display_name=COALESCE(display_name,%s),canonical_url=COALESCE(canonical_url,%s),source_url=COALESCE(source_url,%s),hostname=COALESCE(hostname,%s),source_type=COALESCE(source_type,%s),category=COALESCE(category,%s),feed_url=COALESCE(feed_url,%s),collection_tier=COALESCE(collection_tier,%s),enabled_for_scheduler=%s,health_status=CASE WHEN last_success_at IS NOT NULL THEN health_status ELSE 'not_run' END WHERE source_id=%s''',(safe_name,display,canonical,canonical,host,r.get('source_type'),r.get('canonical_category'),readiness.get('verified_feed_url') if readiness else None,tier,bool(readiness),sid))
        # Legacy entries lack captured RSS payloads. Keep NULL summary_available
        # to mean unknown; never convert missing historic evidence to source-absent.
        # Only collected_at is evidence of a feed retrieval. Older seed rows
        # have neither collected_at nor fetched_at; do not mislabel insert time.
        c.execute('UPDATE news_items SET fetched_at=NULL WHERE collected_at IS NULL AND fetched_at=created_at')
        c.execute('UPDATE news_items SET fetched_at=COALESCE(fetched_at,collected_at),summary_text=COALESCE(summary_text,summary)')
        # Classification is recomputed from the item's own text, not copied from
        # whatever the table already held: a stale row must not survive because it
        # was written first. Keep the input identical to the collector's
        # (COALESCE(summary_text,summary)) so the two never disagree.
        # taxonomy v2.1.0 (classify_v2, multi-level with confidence and
        # subtopics) is the production classifier for the whole corpus as of
        # this phase — the old single-label v1 classify() no longer runs here.
        # A human correction (human_locked) must never be overwritten by this
        # routine backfill, which runs on every API startup.
        locked={r[0] for r in c.execute('SELECT item_id FROM item_classifications WHERE human_locked').fetchall()}
        # Use the richer extracted article body when available (same input
        # enrichment_worker.process_classification uses) — not just the RSS
        # summary — so this routine backfill never silently downgrades an
        # item that was classified from fuller text. Real regression found
        # live: 431 -> 378 security_defense items after a restart because this
        # query used to read only news_items.summary.
        rows=c.execute('''SELECT n.item_id,n.title,COALESCE(cn.original_text,n.summary_text,n.summary)
            FROM news_items n LEFT JOIN news_item_content cn USING(item_id) ORDER BY n.item_id''').fetchall()
        for iid,title,summary in rows:
            if iid in locked:continue
            r=cv.classify(title,summary)
            evidence=list(dict.fromkeys(list(r.evidence)+[s['label'] for s in r.subtopics]))
            c.execute('''INSERT INTO item_classifications(item_id,category_id,category_label,topics,taxonomy_version,method,confidence,reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(item_id) DO UPDATE SET category_id=EXCLUDED.category_id,category_label=EXCLUDED.category_label,
                topics=EXCLUDED.topics,taxonomy_version=EXCLUDED.taxonomy_version,method=EXCLUDED.method,
                confidence=EXCLUDED.confidence,reason=EXCLUDED.reason,classified_at=now()
                WHERE item_classifications.category_label IS DISTINCT FROM EXCLUDED.category_label
                   OR item_classifications.topics IS DISTINCT FROM EXCLUDED.topics
                   OR item_classifications.taxonomy_version IS DISTINCT FROM EXCLUDED.taxonomy_version''',
                (iid,r.category_id,r.category_label,json.dumps(evidence,ensure_ascii=False),r.taxonomy_version,r.method,
                 r.confidence,('matched: '+', '.join(evidence[:8])) if evidence else 'no keyword matched'))
        c.execute('''UPDATE news_items n SET classification=i.category_label,taxonomy_version=i.taxonomy_version,topics=i.topics FROM item_classifications i
            WHERE i.item_id=n.item_id AND (n.classification IS DISTINCT FROM i.category_label OR n.topics IS DISTINCT FROM i.topics OR n.taxonomy_version IS DISTINCT FROM i.taxonomy_version)''')
        # Phase 8A is backfilled only if complete sanitized per-source evidence exists.
        ev=Path('/ops-evidence')
        manifest=ev/'final-report.json'
        if manifest.is_file():
            report=json.loads(manifest.read_text(encoding='utf-8-sig'))
            if report.get('LIVE_CYCLE_INVOCATIONS')==1 and report.get('HTTP_REQUEST_COUNT')<=11:
                runid='phase-8a-'+(report.get('GIT_COMMIT_HASH') or 'unknown')[:12]
                started=datetime.fromtimestamp(manifest.stat().st_mtime,tz=timezone.utc)
                created=c.execute('''INSERT INTO collection_runs(run_id,started_at,finished_at,trigger_type,status,sources_planned,sources_attempted,sources_succeeded,sources_failed,http_requests,response_bytes,items_observed,items_inserted,duplicates,updates,rejected,collector_version) VALUES(%s,%s,%s,'manual','succeeded',11,11,%s,0,%s,%s,%s,%s,%s,0,0,'8a-pilot') ON CONFLICT(run_id) DO NOTHING RETURNING run_id''',(runid,started,started,int(report['RSS_SOURCES_SUCCEEDED']),int(report['HTTP_REQUEST_COUNT']),int(report['TOTAL_RESPONSE_BYTES']),int(report['TOTAL_ITEMS_OBSERVED']),int(report['INSERTED_ITEM_COUNT']),int(report['DUPLICATE_UNCHANGED_ITEMS']))).fetchone()
                results_file=ev/'collection-results.json';transactions_file=ev/'transactions.json'
                if created and results_file.exists() and transactions_file.exists():
                    results=json.loads(results_file.read_text(encoding='utf-8-sig'));transactions=json.loads(transactions_file.read_text(encoding='utf-8-sig'));inserted={x for t in transactions for x in t.get('inserted',[])}
                    invocation=ev/'live-invocation.json'
                    if invocation.is_file():
                        started=datetime.fromisoformat(json.loads(invocation.read_text(encoding='utf-8-sig'))['started_at'].replace('Z','+00:00'))
                    for result in results:
                        sid=result.get('source_id');
                        if sid not in EXEC:continue
                        evidence=next((i for i in result.get('items',[]) if i.get('item_id') in inserted),None)
                        inserted_count=sum(1 for i in result.get('items',[]) if i.get('item_id') in inserted)
                        dup_count=sum(1 for i in result.get('items',[]) if i.get('classification')=='duplicate_unchanged')
                        c.execute('''INSERT INTO source_run_results(run_id,source_id,started_at,finished_at,status,http_status,response_bytes,observed,inserted,duplicates,rejected) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',(runid,sid,started,started,'succeeded' if result.get('status')=='success' else 'failed',int(result['http_status']) if str(result.get('http_status','')).isdigit() else None,int(result.get('response_bytes',0)),int(result.get('observed',0)),inserted_count,dup_count,int(result.get('rejected',0))))
                        if result.get('status')=='success':
                            received=datetime.fromisoformat(result['received_at'].replace('Z','+00:00')) if result.get('received_at') else started
                            c.execute("UPDATE sources SET last_attempt_at=%s,last_success_at=%s,last_http_status=%s,last_item_at=(SELECT max(COALESCE(published_at,fetched_at)) FROM news_items WHERE source_id=%s),consecutive_failures=0,health_status='healthy' WHERE source_id=%s",(received,received,int(result['http_status']) if str(result.get('http_status','')).isdigit() else None,sid,sid))

def health_for(source):
    if not source['last_success_at']:return 'not_run'
    failures=source['consecutive_failures'] or 0
    if failures>=3:return 'failing'
    if failures:return 'degraded'
    if (datetime.now(timezone.utc)-source['last_success_at']).total_seconds()>3*INTERVAL:return 'delayed'
    return 'healthy'

def register_ops(app):
    @app.on_event('startup')
    def schema_migration():migrate()

    @app.get('/api/v1/news')
    def news(search:str|None=None,source_id:str|None=None,category:str|None=None,topic:str|None=None,window:str='all',sort:str='newest',translation:str|None=None,has_image:bool|None=None,has_document:bool|None=None,has_event:bool|None=None,page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100)):
        if window not in ('all','24h','7d','30d'):raise HTTPException(422,'invalid_window')
        if sort not in ('newest','oldest'):raise HTTPException(422,'invalid_sort')
        if translation is not None and translation not in ('available','pending','unavailable','error'):raise HTTPException(422,'invalid_translation')
        clauses=[];args=[]
        if search:clauses.append("(n.title ILIKE %s OR COALESCE(n.summary_text,n.summary,'') ILIKE %s)");args += [f'%{search[:200]}%',f'%{search[:200]}%']
        if source_id:clauses.append('n.source_id=%s');args.append(source_id)
        if category:clauses.append('n.classification=%s');args.append(category[:100])
        if topic:clauses.append('n.topics @> %s::jsonb');args.append(json.dumps([topic[:100]],ensure_ascii=False))
        if window!='all':clauses.append("COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(n.published_at,n.fetched_at)<=now()");args.append({'24h':'24','7d':'168','30d':'720'}[window])
        if translation:clauses.append("COALESCE((SELECT status FROM news_item_translations t WHERE t.item_id=n.item_id AND t.field='summary' AND t.target_language='fa'),'pending')=%s");args.append(translation)
        if has_image is not None:clauses.append(("EXISTS" if has_image else "NOT EXISTS")+" (SELECT 1 FROM news_item_media m WHERE m.item_id=n.item_id AND m.relevance='article_image')")
        if has_document is not None:clauses.append(("EXISTS" if has_document else "NOT EXISTS")+" (SELECT 1 FROM news_item_media m WHERE m.item_id=n.item_id AND m.kind='document')")
        if has_event is not None:clauses.append(("EXISTS" if has_event else "NOT EXISTS")+" (SELECT 1 FROM news_event_members em WHERE em.item_id=n.item_id AND NOT em.manually_removed)")
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        order='COALESCE(n.published_at,n.fetched_at) '+('ASC' if sort=='oldest' else 'DESC')+' NULLS LAST,n.item_id'
        total=q('SELECT count(*) FROM news_items n'+where,args)[0][0]
        rows=q('''SELECT n.item_id,n.source_id,n.title,COALESCE(n.summary_text,n.summary) summary,
            n.summary_source,n.summary_available,n.content_language,n.canonical_url,n.external_guid,n.published_at,
            COALESCE(n.fetched_at,n.collected_at) fetched_at,n.first_seen_at,n.classification,n.topics,
            n.taxonomy_version,n.provenance_status,COALESCE(NULLIF(s.display_name,''),s.hostname),s.hostname,s.source_type,s.category,
            ts.status,ts.text,tt.status,tt.text,img.url,img.alt_text,img.verification_status,
            COALESCE(cn.extraction_status,'not_processed'),COALESCE(cn.display_policy,'link_only'),COALESCE(cn.text_chars,0),
            COALESCE(doc.has_document,false),COALESCE(ev.event_count,0)
            FROM news_items n JOIN sources s USING(source_id)
            LEFT JOIN news_item_translations ts ON ts.item_id=n.item_id AND ts.field='summary' AND ts.target_language='fa'
            LEFT JOIN news_item_translations tt ON tt.item_id=n.item_id AND tt.field='title' AND tt.target_language='fa'
            LEFT JOIN news_item_content cn ON cn.item_id=n.item_id
            LEFT JOIN LATERAL (SELECT url,alt_text,verification_status FROM news_item_media m
                WHERE m.item_id=n.item_id AND m.kind='image' AND m.relevance='article_image' LIMIT 1) img ON TRUE
            LEFT JOIN LATERAL (SELECT true has_document FROM news_item_media m
                WHERE m.item_id=n.item_id AND m.kind='document' AND NOT m.relevance LIKE 'rejected%%' LIMIT 1) doc ON TRUE
            LEFT JOIN LATERAL (SELECT count(*) event_count FROM news_event_members em
                WHERE em.item_id=n.item_id AND NOT em.manually_removed) ev ON TRUE
            '''+where+' ORDER BY '+order+' LIMIT %s OFFSET %s',args+[page_size,(page-1)*page_size])
        keys=['item_id','source_id','title','summary','summary_source','summary_available','content_language','canonical_url','external_guid','published_at','fetched_at','first_seen_at','category','topics','taxonomy_version','provenance_status','source_name','hostname','source_type','source_category','summary_fa_status','summary_fa','title_fa_status','title_fa','lead_image_url','lead_image_alt','lead_image_verification','content_status','display_policy','text_chars','has_document','event_count']
        items=[dict(zip(keys,r)) for r in rows]
        for x in items:
            x['summary_fa_status']=x['summary_fa_status'] or 'pending'
            x['title_fa_status']=x['title_fa_status'] or 'pending'
        return {'items':items,'total':total,'page':page,'page_size':page_size,'window':window,'sort':sort,'topic':topic,'category':category}

    @app.get('/api/v1/news/{item_id}')
    def news_item(item_id:str):
        rows=q('''SELECT n.item_id,n.source_id,n.title,COALESCE(n.summary_text,n.summary),n.summary_source,n.summary_available,n.content_language,n.canonical_url,n.external_guid,n.published_at,COALESCE(n.fetched_at,n.collected_at),n.first_seen_at,n.classification,n.topics,n.taxonomy_version,n.provenance_status,s.display_name,s.hostname,s.source_type,s.canonical_url,s.feed_url FROM news_items n JOIN sources s USING(source_id) WHERE n.item_id=%s''',(item_id,))
        if not rows:raise HTTPException(404,'news_item_not_found')
        item=dict(zip(['item_id','source_id','title','summary','summary_source','summary_available','content_language','canonical_url','external_guid','published_at','fetched_at','first_seen_at','category','topics','taxonomy_version','provenance_status','source_name','hostname','source_type','source_url','feed_url'],rows[0]))
        item['content']=_content_block(item_id)
        item['translations']=_translation_block(item_id)
        item['media']=_media_block(item_id)
        item['classification_detail']=_classification_block(item_id)
        item['events']=_item_events_block(item_id)
        item['provenance']=objects('SELECT feed_url,execution_reference,evidence_status,evidence_json FROM news_item_provenance WHERE item_id=%s',['feed_url','execution_reference','evidence_status','evidence_json'],(item_id,))
        return item

    def _classification_block(item_id):
        """Confidence, matched evidence and human-correction state; absent
        (not zero-filled) when no row exists yet — never a fabricated score."""
        rows=objects('''SELECT category_id,category_label,topics,taxonomy_version,method,confidence,reason,
            human_locked,human_edited_at,classified_at FROM item_classifications WHERE item_id=%s''',
            ['category_id','category_label','topics','taxonomy_version','method','confidence','reason','human_locked','human_edited_at','classified_at'],(item_id,))
        return rows[0] if rows else {'category_id':None,'category_label':None,'topics':[],'taxonomy_version':None,
            'method':None,'confidence':None,'reason':None,'human_locked':False,'human_edited_at':None,'classified_at':None,
            'note':'این خبر هنوز طبقه‌بندی نشده است.'}

    def _item_events_block(item_id):
        return objects('''SELECT e.event_id,e.title,e.member_count,e.source_count,e.first_published_at,
            e.last_updated_at,em.similarity_score,em.membership_reason
            FROM news_event_members em JOIN news_events e USING(event_id)
            WHERE em.item_id=%s AND NOT em.manually_removed ORDER BY e.member_count DESC''',
            ['event_id','title','member_count','source_count','first_published_at','last_updated_at','similarity_score','membership_reason'],(item_id,))

    @app.patch('/api/v1/news/{item_id}/classification')
    def correct_classification(item_id:str,category_id:str=Query(...),category_label:str=Query(...)):
        """Human correction. Locks the item so a future re-cluster/re-classify
        run never silently overwrites a person's decision (rerun-persistent)."""
        if not q('SELECT 1 FROM news_items WHERE item_id=%s',(item_id,)):raise HTTPException(404,'news_item_not_found')
        with psycopg.connect(DSN) as c:
            c.execute('''INSERT INTO item_classifications(item_id,category_id,category_label,topics,taxonomy_version,method,human_locked,human_edited_at)
                VALUES(%s,%s,%s,'[]'::jsonb,COALESCE((SELECT taxonomy_version FROM item_classifications WHERE item_id=%s),'2.0.0'),'human_correction',true,now())
                ON CONFLICT(item_id) DO UPDATE SET category_id=EXCLUDED.category_id,category_label=EXCLUDED.category_label,
                human_locked=true,human_edited_at=now(),method='human_correction',classified_at=now()''',
                (item_id,category_id[:100],category_label[:200],item_id))
            c.execute('UPDATE news_items SET classification=%s WHERE item_id=%s',(category_label[:200],item_id))
        return _classification_block(item_id)

    @app.get('/api/v1/events')
    def events(page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100)):
        total=q('SELECT count(*) FROM news_events')[0][0]
        rows=objects('''SELECT event_id,title,member_count,source_count,first_published_at,last_updated_at,
            clustering_method,algorithm_version FROM news_events ORDER BY last_updated_at DESC LIMIT %s OFFSET %s''',
            ['event_id','title','member_count','source_count','first_published_at','last_updated_at','clustering_method','algorithm_version'],
            (page_size,(page-1)*page_size))
        return {'events':rows,'total':total,'page':page,'page_size':page_size}

    @app.get('/api/v1/events/{event_id}')
    def event_detail(event_id:str):
        rows=objects('''SELECT event_id,title,member_count,source_count,first_published_at,last_updated_at,
            clustering_method,algorithm_version FROM news_events WHERE event_id=%s''',
            ['event_id','title','member_count','source_count','first_published_at','last_updated_at','clustering_method','algorithm_version'],(event_id,))
        if not rows:raise HTTPException(404,'event_not_found')
        event=rows[0]
        event['members']=objects('''SELECT n.item_id,n.title,n.published_at,n.canonical_url,s.hostname,
            em.similarity_score,em.membership_reason
            FROM news_event_members em JOIN news_items n USING(item_id) JOIN sources s ON s.source_id=n.source_id
            WHERE em.event_id=%s AND NOT em.manually_removed ORDER BY n.published_at ASC NULLS LAST''',
            ['item_id','title','published_at','canonical_url','hostname','similarity_score','membership_reason'],(event_id,))
        return event

    def _content_block(item_id):
        """Body text plus an explicit extraction status; never a fabricated field."""
        rows=objects('''SELECT content_version,original_language,original_text,text_chars,extraction_method,
            extraction_status,display_policy,content_sha256,extracted_at,updated_at FROM news_item_content WHERE item_id=%s''',
            ['content_version','original_language','original_text','text_chars','extraction_method','extraction_status','display_policy','content_sha256','extracted_at','updated_at'],(item_id,))
        if not rows:
            return {'extraction_status':'not_processed','display_policy':'link_only','original_text':None,
                'text_chars':0,'content_version':None,'extraction_method':None,
                'note':'این رکورد پیش از افزودن استخراج متن ثبت شده است.'}
        block=rows[0]
        # Only syndicated bodies are rendered in full; everything else stays a
        # summary plus a link to the publisher.
        if block['display_policy']!='full_syndicated':
            block['original_text_withheld_reason']='display_policy:'+block['display_policy']
        return block

    def _translation_block(item_id):
        rows=objects('''SELECT field,target_language,status,text,provider,model,content_version,source_chars,error,updated_at
            FROM news_item_translations WHERE item_id=%s''',
            ['field','target_language','status','text','provider','model','content_version','source_chars','error','updated_at'],(item_id,))
        found={r['field']:r for r in rows}
        for field in ('title','summary','body'):
            found.setdefault(field,{'field':field,'target_language':'fa','status':'pending','text':None,
                'provider':None,'model':None,'content_version':None,'source_chars':None,'error':None,'updated_at':None})
        return found

    def _media_block(item_id):
        rows=objects('''SELECT media_id,kind,url,mime_type,byte_size,declared_width,declared_height,alt_text,position,
            relevance,rejection_reason,discovery_method,verification_status,discovered_at
            FROM news_item_media WHERE item_id=%s ORDER BY (relevance='article_image') DESC,position NULLS LAST,media_id''',
            ['media_id','kind','url','mime_type','byte_size','declared_width','declared_height','alt_text','position','relevance','rejection_reason','discovery_method','verification_status','discovered_at'],(item_id,))
        accepted=[r for r in rows if not r['relevance'].startswith('rejected')]
        return {'images':[r for r in accepted if r['kind']=='image'],
            'documents':[r for r in accepted if r['kind']=='document'],
            'filtered_out':[{'url':r['url'],'relevance':r['relevance'],'rejection_reason':r['rejection_reason']} for r in rows if r['relevance'].startswith('rejected')],
            'note':'تصاویر و اسناد از خود خوراک منبع استخراج شده‌اند و هنوز دانلود و راستی‌آزمایی نشده‌اند.'}

    @app.get('/api/v1/sources')
    def sources(page:int=Query(1,ge=1),page_size:int=Query(50,ge=1,le=100)):
        total=q('SELECT count(*) FROM sources')[0][0]
        rows=q('''SELECT s.source_id,COALESCE(NULLIF(s.display_name,''),s.hostname) display_name,s.canonical_url,s.hostname,s.source_type,s.category,s.feed_url,s.collection_tier,s.language,s.enabled_for_scheduler,s.last_attempt_at,s.last_success_at,s.last_http_status,s.last_item_at,s.consecutive_failures,s.health_status,COUNT(n.item_id)::int item_count,COUNT(n.item_id) FILTER(WHERE COALESCE(n.published_at,n.fetched_at)>=now()-interval '24 hours')::int items_24h,COUNT(n.item_id) FILTER(WHERE COALESCE(n.published_at,n.fetched_at)>=now()-interval '7 days')::int items_7d,MAX(n.published_at) latest_published FROM sources s LEFT JOIN news_items n USING(source_id) GROUP BY s.id ORDER BY display_name NULLS LAST,s.hostname LIMIT %s OFFSET %s''',(page_size,(page-1)*page_size))
        data=[]
        for r in rows:
            keys=['source_id','display_name','canonical_url','hostname','source_type','category','feed_url','collection_tier','language','enabled_for_scheduler','last_attempt_at','last_success_at','last_http_status','last_item_at','consecutive_failures','health_status','item_count','items_24h','items_7d','latest_published']
            x=dict(zip(keys,r));x['health_status']=health_for(x);data.append(x)
        return {'sources':data,'total':total,'page':page,'page_size':page_size}

    @app.get('/api/v1/sources/coverage')
    def coverage():
        """Every registered source with its real collection status.

        Three counts are deliberately kept apart: how many sources the client
        listed, how many have a validated collection path, and how many actually
        produced a successful fetch. They are not the same number and the product
        must never merge them.
        """
        live={r[0]:r for r in q('''SELECT source_id,last_success_at,health_status,consecutive_failures,
            (SELECT count(*) FROM news_items n WHERE n.source_id=s.source_id) FROM sources s''')}
        rows=[]
        for sid,entry in REG.items():
            cap=CAP.get(sid,{});ready=EXEC.get(sid);row=live.get(sid)
            kind=entry.get('source_type')
            if kind=='x_account':
                state,reason='not_covered','X account: no authorised collection path or usage policy is in place.'
            elif ready:
                state,reason='active_rss','Validated RSS feed collected on the scheduled cycle.'
            elif cap.get('access_status')=='unreachable' or cap.get('robots_allowed') is False:
                state,reason='blocked','Publisher returns 403 or disallows automated access; not collected.'
            elif _has_feed_candidate(sid):
                state,reason='feed_candidate','A working feed was discovered but is not yet validated for execution.'
            elif _has_sitemap_candidate(sid):
                state,reason='sitemap_candidate','No feed; a readable sitemap exists but no tested parser does.'
            else:
                state,reason='html_candidate','No feed or sitemap discovered; would require an HTML listing parser.'
            rows.append({'source_id':sid,'hostname':entry.get('hostname'),'url':entry.get('canonical_key') or entry.get('url'),
                'source_type':kind,'category':entry.get('canonical_category'),'x_handle':entry.get('x_handle'),
                'coverage_state':state,'reason':reason,
                'feed_url':ready.get('verified_feed_url') if ready else None,
                'homepage_status':cap.get('homepage_status'),'robots_allowed':cap.get('robots_allowed'),
                'in_database':bool(row),'last_success_at':row[1] if row else None,
                'health_status':row[2] if row else None,'item_count':row[4] if row else 0})
        rows.sort(key=lambda r:(r['coverage_state'],r['hostname'] or ''))
        by_state={};by_type={}
        for r in rows:
            by_state[r['coverage_state']]=by_state.get(r['coverage_state'],0)+1
            by_type.setdefault(r['source_type'],{}).setdefault(r['coverage_state'],0)
            by_type[r['source_type']][r['coverage_state']]+=1
        monitored=[r for r in rows if r['coverage_state']=='active_rss' and r['last_success_at']]
        return {'registered':len(rows),'executable':by_state.get('active_rss',0),'monitored':len(monitored),
            'by_state':by_state,'by_source_type':by_type,'sources':rows,
            'definitions':{'registered':'در سند منابع مشتری ثبت شده است.',
                'executable':'مسیر جمع‌آوری معتبر و آزموده دارد.',
                'monitored':'دست‌کم یک دریافت موفق واقعی ثبت کرده است.'}}

    def _has_feed_candidate(sid):
        return any(str(c.get('status'))=='200' and 'sitemap' not in (c.get('url') or '')
                   for c in (DISCOVERY.get(sid,{}).get('feed_checks') or []))

    def _has_sitemap_candidate(sid):
        return any(str(c.get('status'))=='200' and 'sitemap' in (c.get('url') or '')
                   for c in (DISCOVERY.get(sid,{}).get('feed_checks') or []))

    @app.get('/api/v1/sources/{source_id}')
    def source(source_id:str):
        result=sources(page=1,page_size=100)['sources'];x=next((s for s in result if s['source_id']==source_id),None)
        if x is None:raise HTTPException(404,'source_not_found')
        x['provenance']=q('SELECT evidence_status,count(*)::int count FROM news_item_provenance WHERE source_id=%s GROUP BY evidence_status',(source_id,))
        x['timeline']=q("SELECT date_trunc('day',COALESCE(published_at,fetched_at)) bucket,count(*)::int count FROM news_items WHERE source_id=%s GROUP BY 1 ORDER BY 1 DESC LIMIT 30",(source_id,))
        x['latest_items']=news(source_id=source_id,page=1,page_size=20)['items']
        return x

    @app.get('/api/v1/stats/overview')
    def ops_overview():
        r=q("""SELECT count(*),count(*) FILTER(WHERE COALESCE(published_at,fetched_at)>=now()-interval '24 hours' AND COALESCE(published_at,fetched_at)<=now()),count(*) FILTER(WHERE COALESCE(published_at,fetched_at)>=now()-interval '7 days' AND COALESCE(published_at,fetched_at)<=now()),count(*) FILTER(WHERE summary_available IS TRUE),count(*) FILTER(WHERE summary_available IS FALSE),count(*) FILTER(WHERE summary_available IS NULL),count(*) FILTER(WHERE published_at IS NULL),count(*) FILTER(WHERE classification='سایر'),count(*) FILTER(WHERE provenance_status='COMPLETE') FROM news_items""")[0]
        health=[health_for(x) for x in sources(page=1,page_size=100)['sources']]
        last=objects("SELECT run_id,started_at,finished_at,status,sources_succeeded,sources_failed,items_inserted,duplicates FROM collection_runs ORDER BY started_at DESC LIMIT 1",['run_id','started_at','finished_at','status','sources_succeeded','sources_failed','items_inserted','duplicates'])
        return {'total_items':r[0],'items_24h':r[1],'items_7d':r[2],'summary_available':r[3],'summary_unavailable_known':r[4],'summary_status_unknown':r[5],'missing_publication_date':r[6],'uncategorized':r[7],'provenance_complete':r[8],'sources':len(health),'healthy_sources':health.count('healthy'),'not_run_sources':health.count('not_run'),'delayed_or_failed_sources':sum(x in ('degraded','failing','delayed') for x in health),'last_run':last[0] if last else None}

    @app.get('/api/v1/stats/timeline')
    def timeline(window:str='24h'):
        if window not in ('24h','7d','30d'):raise HTTPException(422,'invalid_window')
        hours={'24h':24,'7d':168,'30d':720}[window]
        unit='hour' if window=='24h' else 'day'
        return {'window':window,'timezone':'UTC','unit':unit,'series':objects(f"SELECT date_trunc('{unit}',COALESCE(published_at,fetched_at)) bucket,count(*)::int count FROM news_items WHERE COALESCE(published_at,fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(published_at,fetched_at)<=now() GROUP BY 1 ORDER BY 1",['bucket','count'],(hours,))}

    @app.get('/api/v1/stats/sources')
    def source_stats():return {'sources':sources(page=1,page_size=100)['sources']}

    @app.get('/api/v1/stats/topics')
    def topic_stats():return {'categories':objects('SELECT category_label label,count(*)::int count FROM item_classifications GROUP BY 1 ORDER BY count DESC,label',['label','count']),'topics':objects("SELECT x.topic,count(*)::int count FROM item_classifications,LATERAL jsonb_array_elements_text(topics) AS x(topic) GROUP BY 1 ORDER BY count DESC,topic LIMIT 20",['topic','count'])}

    @app.get('/api/v1/stats/topics/detailed')
    def topic_stats_detailed(window:str='30d'):
        if window not in ('24h','7d','30d','all'):raise HTTPException(422,'invalid_window')
        hours={'24h':24,'7d':168,'30d':720}.get(window)
        filt='TRUE' if hours is None else "COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(n.published_at,n.fetched_at)<=now()"
        args=() if hours is None else (hours,)
        categories=objects(f'''SELECT COALESCE(n.classification,'سایر') label,count(*)::int count,
            count(DISTINCT n.source_id)::int sources,max(COALESCE(n.published_at,n.fetched_at)) latest
            FROM news_items n WHERE {filt} GROUP BY 1 ORDER BY count DESC,label''', ['label','count','sources','latest'],args)
        topics=objects(f'''SELECT x.topic,count(*)::int count,count(DISTINCT n.source_id)::int sources,
            max(COALESCE(n.published_at,n.fetched_at)) latest
            FROM news_items n CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(n.topics,'[]'::jsonb)) AS x(topic)
            WHERE {filt} GROUP BY 1 ORDER BY count DESC,x.topic LIMIT 50''',['topic','count','sources','latest'],args)
        # Attach compact provenance context for drill-down; do not infer semantics.
        for row in topics:
            topic=row['topic']
            row['previous_count']=q('''SELECT count(*) FROM news_items n CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(n.topics,'[]'::jsonb)) x(topic)
                WHERE x.topic=%s AND COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval
                AND COALESCE(n.published_at,n.fetched_at)<now()-(%s || ' hours')::interval''',(topic,hours or 1440,hours or 720))[0][0] if hours else 0
            row['source_names']=objects(f'''SELECT DISTINCT COALESCE(NULLIF(s.display_name,''),s.hostname) name
                FROM news_items n JOIN sources s USING(source_id) CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(n.topics,'[]'::jsonb)) x(topic)
                WHERE x.topic=%s AND {filt} ORDER BY name LIMIT 5''',['name'],(topic,*args))
            row['recent_news']=objects(f'''SELECT n.item_id,n.title,n.canonical_url,COALESCE(n.published_at,n.fetched_at) observed_at,
                COALESCE(NULLIF(s.display_name,''),s.hostname) source_name
                FROM news_items n JOIN sources s USING(source_id) CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(n.topics,'[]'::jsonb)) x(topic)
                WHERE x.topic=%s AND {filt} ORDER BY COALESCE(n.published_at,n.fetched_at) DESC NULLS LAST LIMIT 5''',
                ['item_id','title','canonical_url','observed_at','source_name'],(topic,*args))
        source_rows=objects(f'''SELECT COALESCE(NULLIF(s.display_name,''),s.hostname) label,count(n.item_id)::int count,
            count(DISTINCT n.classification)::int categories,max(COALESCE(n.published_at,n.fetched_at)) latest
            FROM sources s LEFT JOIN news_items n ON n.source_id=s.source_id AND {filt}
            GROUP BY s.source_id,s.display_name,s.hostname ORDER BY count DESC,label''', ['label','count','categories','latest'],args)
        uncategorized=q("SELECT count(*) FROM news_items n WHERE COALESCE(n.classification,'سایر')='سایر'")[0][0]
        uncategorized_in_window=q(f"SELECT count(*) FROM news_items n WHERE {filt} AND COALESCE(n.classification,'سایر')='سایر'",args)[0][0]
        latest=q('SELECT max(COALESCE(published_at,fetched_at)) FROM news_items')[0][0]
        return {'window':window,'categories':categories,'topics':topics,'sources':source_rows,
            'uncategorized':uncategorized,'uncategorized_in_window':uncategorized_in_window,
            'latest_observation':latest,'method':'Aggregates from stored PostgreSQL records; categories and topics are rule-based labels, not semantic analysis.'}

    @app.get('/api/v1/stats/quality')
    def quality_stats():return ops_overview() | {'duplicates_prevented':q('SELECT COALESCE(sum(duplicates),0) FROM collection_runs')[0][0],'rejected':q('SELECT COALESCE(sum(rejected),0) FROM collection_runs')[0][0],'classified':q('SELECT count(*) FROM item_classifications')[0][0]}

    @app.get('/api/v1/stats/brief')
    def brief(window:str='24h'):
        if window not in ('24h','7d','30d'):raise HTTPException(422,'invalid_window')
        hours={'24h':24,'7d':168,'30d':720}[window]
        counts=q("SELECT count(*) FILTER(WHERE COALESCE(published_at,fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(published_at,fetched_at)<=now()),count(DISTINCT source_id) FILTER(WHERE COALESCE(published_at,fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(published_at,fetched_at)<=now()) FROM news_items",(hours,hours))[0]
        previous=q("SELECT count(*) FROM news_items WHERE COALESCE(published_at,fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(published_at,fetched_at)<now()-(%s || ' hours')::interval",(hours*2,hours))[0][0]
        quiet=q("SELECT COALESCE(NULLIF(s.display_name,''),s.hostname),s.hostname FROM sources s WHERE NOT EXISTS(SELECT 1 FROM news_items n WHERE n.source_id=s.source_id AND COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(n.published_at,n.fetched_at)<=now()) ORDER BY s.hostname",(hours,))
        cats=q("SELECT classification,count(*)::int FROM news_items WHERE COALESCE(published_at,fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(published_at,fetched_at)<=now() GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 3",(hours,))
        tops=q("SELECT x.topic,count(*)::int, count(DISTINCT n.source_id)::int FROM news_items n,LATERAL jsonb_array_elements_text(n.topics) AS x(topic) WHERE COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(n.published_at,n.fetched_at)<=now() GROUP BY 1 ORDER BY 2 DESC,3 DESC,1 LIMIT 5",(hours,))
        leaders=q("SELECT COALESCE(NULLIF(s.display_name,''),s.hostname),s.hostname,count(*)::int FROM news_items n JOIN sources s USING(source_id) WHERE COALESCE(n.published_at,n.fetched_at)>=now()-(%s || ' hours')::interval AND COALESCE(n.published_at,n.fetched_at)<=now() GROUP BY s.source_id,s.display_name,s.hostname ORDER BY 3 DESC,1 LIMIT 5",(hours,))
        return {'window':window,'items':counts[0],'active_sources':counts[1],'previous_items':previous,'change':counts[0]-previous,'categories':cats,'topics':tops,'leading_sources':leaders,'sources_without_recent_items':quiet,'method':'Counts and rule-based keyword categories from PostgreSQL; descriptive only.'}

    @app.get('/api/v1/collection/status')
    def collection_status():
        r=q('SELECT run_id,started_at,finished_at,status,sources_planned,sources_attempted,sources_succeeded,sources_failed,http_requests,response_bytes,items_observed,items_inserted,duplicates,updates,rejected,error_summary FROM collection_runs ORDER BY started_at DESC LIMIT 1')
        try:
            state=json.loads((Path(os.getenv('COLLECTOR_STATE_DIR','/state'))/'health.json').read_text(encoding='utf-8'))
            enabled=bool(state.get('enabled'));collector_health='healthy' if enabled and (state.get('heartbeat_at') or state.get('started_at')) else ('stopped' if not enabled else 'unknown')
            heartbeat=state.get('heartbeat_at') or state.get('started_at')
            if enabled and heartbeat:
                beat=datetime.fromisoformat(heartbeat.replace('Z','+00:00'))
                if (datetime.now(timezone.utc)-beat).total_seconds()>45:
                    enabled=False;collector_health='stopped_stale_heartbeat'
        except (OSError,ValueError):state={};enabled=False;collector_health='not_running'
        next_at=None
        if enabled and state.get('next_run_at'):
            next_at=datetime.fromisoformat(state['next_run_at'].replace('Z','+00:00'))
        elif enabled and state.get('started_at'):
            next_at=datetime.fromisoformat(state['started_at'].replace('Z','+00:00'))+__import__('datetime').timedelta(seconds=INTERVAL)
        return {'scheduler_enabled':enabled,'collector_health':collector_health,'interval_seconds':INTERVAL,'next_run_at':next_at if enabled else None,'last_run':dict(zip(['run_id','started_at','finished_at','status','sources_planned','sources_attempted','sources_succeeded','sources_failed','http_requests','response_bytes','items_observed','items_inserted','duplicates','updates','rejected','error_summary'],r[0])) if r else None,'lock':'postgres_advisory_lock'}

    @app.get('/api/v1/collection/runs')
    def runs(page:int=Query(1,ge=1,le=10000),page_size:int=Query(20,ge=1,le=100)):
        return {'runs':objects('SELECT run_id,started_at,finished_at,trigger_type,status,sources_planned,sources_attempted,sources_succeeded,sources_failed,http_requests,response_bytes,items_observed,items_inserted,duplicates,updates,rejected,skipped_locked FROM collection_runs ORDER BY started_at DESC LIMIT %s OFFSET %s',['run_id','started_at','finished_at','trigger_type','status','sources_planned','sources_attempted','sources_succeeded','sources_failed','http_requests','response_bytes','items_observed','items_inserted','duplicates','updates','rejected','skipped_locked'],(page_size,(page-1)*page_size)),'total':q('SELECT count(*) FROM collection_runs')[0][0],'page':page,'page_size':page_size}

    @app.get('/api/v1/collection/runs/{run_id}')
    def run_detail(run_id:str):
        r=q('SELECT run_id,started_at,finished_at,trigger_type,status,sources_planned,sources_attempted,sources_succeeded,sources_failed,http_requests,response_bytes,items_observed,items_inserted,duplicates,updates,rejected,skipped_locked FROM collection_runs WHERE run_id=%s',(run_id,))
        if not r:raise HTTPException(404,'collection_run_not_found')
        return {'run':dict(zip(['run_id','started_at','finished_at','trigger_type','status','sources_planned','sources_attempted','sources_succeeded','sources_failed','http_requests','response_bytes','items_observed','items_inserted','duplicates','updates','rejected','skipped_locked'],r[0])),'sources':objects('SELECT source_id,started_at,finished_at,status,http_status,response_bytes,observed,inserted,duplicates,rejected,error_class,error_message_sanitized,error_stage FROM source_run_results WHERE run_id=%s ORDER BY source_id',['source_id','started_at','finished_at','status','http_status','response_bytes','observed','inserted','duplicates','rejected','error_class','error_message_sanitized','error_stage'],(run_id,))}

    @app.get('/api/v1/stats/content')
    def content_stats():
        """Honest per-field coverage: what exists, what is queued, what is absent."""
        total=q('SELECT count(*) FROM news_items')[0][0]
        body=dict(q("SELECT COALESCE(extraction_status,'not_processed'),count(*) FROM news_item_content GROUP BY 1"))
        body['not_processed']=body.get('not_processed',0)+total-q('SELECT count(*) FROM news_item_content')[0][0]
        policy=dict(q('SELECT display_policy,count(*) FROM news_item_content GROUP BY 1'))
        translations={}
        for field in ('title','summary','body'):
            counts=dict(q('SELECT status,count(*) FROM news_item_translations WHERE field=%s AND target_language=%s GROUP BY 1',(field,'fa')))
            counts['pending']=counts.get('pending',0)+total-sum(counts.values())
            translations[field]=counts
        media=dict(q('SELECT relevance,count(*) FROM news_item_media GROUP BY 1'))
        items_with_image=q("SELECT count(DISTINCT item_id) FROM news_item_media WHERE relevance='article_image'")[0][0]
        items_with_doc=q("SELECT count(DISTINCT item_id) FROM news_item_media WHERE kind='document'")[0][0]
        return {'total_items':total,'body_text':body,'display_policy':policy,'translations_fa':translations,
            'media_by_relevance':media,'items_with_article_image':items_with_image,
            'items_with_document':items_with_doc,
            'translation_provider':os.getenv('NEWS_TRANSLATION_PROVIDER') or 'none',
            'method':'Counts of stored rows only. A pending field means no provider produced it yet; nothing is generated to fill a gap.'}

    @app.get('/api/v1/taxonomy')
    def taxonomy():return TAX2

    @app.get('/api/v1/ai/provider-status')
    def ai_provider_status():
        """Never exposes AI_API_KEY. Reports what would happen if an AI-
        assisted feature were invoked right now — mode, provider, per-task
        model, and whether the circuit breaker is currently open — without
        actually calling anything."""
        cfg=aig.load_config()
        breaker=aig._BREAKERS.get(cfg.provider if cfg.mode==aig.Mode.EXTERNAL_PROVIDER else cfg.mode.value)
        return {'mode':cfg.mode.value,'provider':cfg.provider if cfg.mode==aig.Mode.EXTERNAL_PROVIDER else None,
            'models':cfg.models,'timeout_seconds':cfg.timeout_seconds,'max_concurrency':cfg.max_concurrency,
            'daily_budget_usd':cfg.daily_budget_usd,'api_key_configured':bool(cfg.api_key),
            'circuit_open':bool(breaker and breaker.is_open),
            'prompt_versions':aig.LATEST_PROMPT_VERSION,
            'note':'AI_API_KEY is never included in this response.'}

    @app.get('/api/v1/ai/cost-usage')
    def ai_cost_usage(days:int=Query(7,ge=1,le=90)):
        rows=objects(f'''SELECT date_trunc('day',created_at)::date d,task_type,provider,
            count(*)::int requests,count(*) FILTER(WHERE status='available')::int succeeded,
            count(*) FILTER(WHERE cache_hit)::int cache_hits,
            COALESCE(sum(tokens_in),0)::bigint tokens_in,COALESCE(sum(tokens_out),0)::bigint tokens_out,
            COALESCE(sum(estimated_cost_usd),0)::float cost_usd
            FROM ai_requests_log WHERE created_at>=now()-(%s||' days')::interval
            GROUP BY 1,2,3 ORDER BY 1 DESC,3''',
            ['date','task_type','provider','requests','succeeded','cache_hits','tokens_in','tokens_out','cost_usd'],(days,))
        today=q('''SELECT COALESCE(sum(estimated_cost_usd),0)::float FROM ai_requests_log
            WHERE created_at>=date_trunc('day',now())''')[0][0]
        errors=objects('''SELECT status,count(*)::int n FROM ai_requests_log
            WHERE created_at>=now()-interval '7 days' AND status NOT IN ('available','cached') GROUP BY 1 ORDER BY 2 DESC''',
            ['status','count'])
        return {'window_days':days,'rows':rows,'spent_today_usd':today,
            'daily_budget_usd':aig.load_config().daily_budget_usd,'recent_non_success_statuses':errors}

    @app.get('/api/v1/taxonomy/v1')
    def taxonomy_v1():return TAX

    @app.get('/api/v1/categories')
    def categories(window:str='30d'):
        if window not in ('24h','7d','30d','all'):raise HTTPException(422,'invalid_window')
        time_clause="AND COALESCE(n.published_at,n.fetched_at)>=now()-interval '%s'"%{'24h':'24 hours','7d':'7 days','30d':'30 days'}.get(window,'100 years')
        cat_ids=[c['id'] for c in TAX2['categories']]+[TAX2['fallback']['id']]
        rows=[]
        for cid in cat_ids:
            meta=next((c for c in TAX2['categories'] if c['id']==cid),TAX2['fallback'])
            total=q(f"SELECT count(*) FROM item_classifications c JOIN news_items n USING(item_id) WHERE c.category_id=%s {time_clause}",(cid,))[0][0]
            prev=q(f"SELECT count(*) FROM item_classifications c JOIN news_items n USING(item_id) WHERE c.category_id=%s AND COALESCE(n.published_at,n.fetched_at)>=now()-interval '{{0}}'*2 AND COALESCE(n.published_at,n.fetched_at)<now()-interval '{{0}}'".format({'24h':'24 hours','7d':'7 days','30d':'30 days'}.get(window,'100 years')),(cid,))[0][0] if window!='all' else None
            latest=q("SELECT max(COALESCE(n.published_at,n.fetched_at)) FROM item_classifications c JOIN news_items n USING(item_id) WHERE c.category_id=%s",(cid,))[0][0]
            sources=q("SELECT count(DISTINCT n.source_id) FROM item_classifications c JOIN news_items n USING(item_id) WHERE c.category_id=%s",(cid,))[0][0]
            sparkline=q(f"""SELECT date_trunc('day',COALESCE(n.published_at,n.fetched_at))::date d,count(*)::int n
                FROM item_classifications c JOIN news_items n USING(item_id)
                WHERE c.category_id=%s AND COALESCE(n.published_at,n.fetched_at)>=now()-interval '14 days' GROUP BY 1 ORDER BY 1""",(cid,))
            rows.append({'id':cid,'label':meta['label'],'subtopic_count':len(meta.get('subtopics') or []),
                'count':total,'previous_count':prev,'active_sources':sources,'latest_item_at':latest,
                'sparkline':sparkline,'is_fallback':cid==TAX2['fallback']['id']})
        total_all=sum(r['count'] for r in rows) or 1
        for r in rows:r['percent']=round(100*r['count']/total_all,1)
        rows.sort(key=lambda r:(-r['count']))
        return {'window':window,'categories':rows,'total_items':total_all}

    @app.get('/api/v1/categories/{category_id}')
    def category_detail(category_id:str,window:str='30d'):
        meta=next((c for c in TAX2['categories'] if c['id']==category_id),None)
        is_other=category_id==TAX2['fallback']['id']
        if not meta and not is_other:raise HTTPException(404,'category_not_found')
        label=TAX2['fallback']['label'] if is_other else meta['label']
        total=q('SELECT count(*) FROM item_classifications WHERE category_id=%s',(category_id,))[0][0]
        timeline=q("""SELECT date_trunc('day',COALESCE(n.published_at,n.fetched_at))::date d,count(*)::int n
            FROM item_classifications c JOIN news_items n USING(item_id)
            WHERE c.category_id=%s AND COALESCE(n.published_at,n.fetched_at)>=now()-interval '90 days' GROUP BY 1 ORDER BY 1""",(category_id,))
        sources=q("""SELECT COALESCE(NULLIF(s.display_name,''),s.hostname) name,count(*)::int n
            FROM item_classifications c JOIN news_items n USING(item_id) JOIN sources s ON s.source_id=n.source_id
            WHERE c.category_id=%s GROUP BY 1 ORDER BY 2 DESC LIMIT 8""",(category_id,))
        subtopics=[]
        if meta:
            for sub in (meta.get('subtopics') or []):
                cnt=q("SELECT count(*) FROM item_classifications WHERE category_id=%s AND topics @> %s::jsonb",
                    (category_id,json.dumps([sub['label']],ensure_ascii=False)))[0][0]
                subtopics.append({'id':sub['id'],'label':sub['label'],'count':cnt})
            subtopics.sort(key=lambda s:-s['count'])
        events=objects("""SELECT DISTINCT e.event_id,e.title,e.member_count FROM news_events e
            JOIN news_event_members em USING(event_id) JOIN item_classifications c ON c.item_id=em.item_id
            WHERE c.category_id=%s ORDER BY e.member_count DESC LIMIT 5""",
            ['event_id','title','member_count'],(category_id,))
        latest=objects("""SELECT n.item_id,n.title,n.published_at,COALESCE(NULLIF(s.display_name,''),s.hostname) source_name,c.confidence
            FROM item_classifications c JOIN news_items n USING(item_id) JOIN sources s ON s.source_id=n.source_id
            WHERE c.category_id=%s ORDER BY COALESCE(n.published_at,n.fetched_at) DESC LIMIT 20""",
            ['item_id','title','published_at','source_name','confidence'],(category_id,))
        review_sample=None
        if is_other:
            review_sample=objects("""SELECT n.item_id,n.title,COALESCE(NULLIF(s.display_name,''),s.hostname) source_name,n.published_at
                FROM item_classifications c JOIN news_items n USING(item_id) JOIN sources s ON s.source_id=n.source_id
                WHERE c.category_id='other' ORDER BY COALESCE(n.published_at,n.fetched_at) DESC LIMIT 30""",
                ['item_id','title','source_name','published_at'])
        return {'id':category_id,'label':label,'is_fallback':is_other,'total_items':total,
            'taxonomy_version':TAX2['version'],'timeline':timeline,'main_sources':sources,
            'subtopics':subtopics,'key_events':events,'latest_items':latest,
            'other_explanation':('این دسته آخرین راه طبقه‌بندی است: خبرهایی که با هیچ‌یک از کلیدواژه‌های '
                'دسته‌های تعریف‌شده مطابقت نداشتند اینجا قرار می‌گیرند. برخی از این خبرها واقعاً بی‌ربط به '
                'حوزه دفاعی-امنیتی و ژئوپلیتیک هستند (مثلاً اخبار سرگرمی یا حوادث محلی)؛ برخی دیگر ممکن است '
                'به قواعد طبقه‌بندی بیشتری نیاز داشته باشند. نمونه زیر برای بازبینی انسانی ارائه شده است.'
                ) if is_other else None,
            'review_sample':review_sample}

    @app.get('/api/v1/health')
    def health_detail():return {'status':'ok','database':'ready','items':q('SELECT count(*) FROM news_items')[0][0],'sources':q('SELECT count(*) FROM sources')[0][0],'scheduler_enabled':collection_status()['scheduler_enabled']}

    @app.get('/api/v1/health/collection')
    def collection_health(response:Response):
        """Fails with 503 when monitoring has stalled, so an external check can alert.

        Nothing here notifies anyone; it gives a uniform signal for whatever the
        operator already polls. `expected_collection` distinguishes a scheduler
        that is deliberately off from one that has died.
        """
        status=collection_status()
        last=q("SELECT started_at,finished_at,status FROM collection_runs WHERE trigger_type<>'skipped_locked' ORDER BY started_at DESC LIMIT 1")
        stale_after=3*INTERVAL
        problems=[]
        if not status['scheduler_enabled']:
            problems.append('scheduler_disabled')
        elif status['collector_health']!='healthy':
            problems.append('collector_'+status['collector_health'])
        age=None
        if last:
            age=int((datetime.now(timezone.utc)-last[0][0]).total_seconds())
            if status['scheduler_enabled'] and age>stale_after:
                problems.append(f'last_run_age_{age}s_over_{stale_after}s')
            if last[0][2] in ('failed',):
                problems.append('last_run_failed')
        elif status['scheduler_enabled']:
            problems.append('no_run_recorded')
        stuck=q("SELECT count(*) FROM collection_runs WHERE status='running' AND started_at<now()-interval '1 hour'")[0][0]
        if stuck:problems.append(f'runs_stuck_in_running:{stuck}')
        ok=not problems
        if not ok:response.status_code=503
        return {'status':'ok' if ok else 'degraded','problems':problems,
            'expected_collection':status['scheduler_enabled'],
            'collector_health':status['collector_health'],
            'last_run_age_seconds':age,'stale_after_seconds':stale_after,
            'last_run':status['last_run'],'checked_at':datetime.now(timezone.utc)}
