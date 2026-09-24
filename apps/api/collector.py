"""Sequential, no-retry RSS cycle used by the opt-in 15-minute scheduler."""
import email.utils, hashlib, html, json, os, re, time, uuid, signal, logging, traceback, tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from defusedxml import ElementTree as ET
import psycopg
from psycopg.types.json import Jsonb
from ops import EXEC, REG, DSN, database_json, canonical_json_dumps
from content import extract as extract_content, display_policy, CONTENT_VERSION
import classify_v2 as cv

ROOT=Path('/app'); STATE=Path(os.getenv('COLLECTOR_STATE_DIR','/state'))
MAX_BYTES=2*1024*1024;TIMEOUT=30;UA='IranMonitor/1.0 (bounded RSS monitoring; project news-feed collector)';VERSION='1.2.0'
LOG=logging.getLogger('iran_monitor.collector')
LOCK_KEY=0x4952414E4D4F4E
SOURCE_TERMINAL={'succeeded','failed_fetch','failed_parse','failed_normalize','committed_checkpoint_failed','failed_finalize'}
def preflight_image():
    expected=os.getenv('EXPECTED_COLLECTOR_GIT_REVISION')
    if not expected:return
    try:info=json.loads((ROOT/'BUILD_INFO.json').read_text(encoding='utf-8'))
    except Exception:raise SystemExit('COLLECTOR_IMAGE_REVISION_MISMATCH')
    if info.get('git_revision')!=expected or info.get('serializer_version')!='1':raise SystemExit('COLLECTOR_IMAGE_REVISION_MISMATCH')
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None
class Text(HTMLParser):
    blocked={'script','style','iframe','object','svg','noscript'}
    def __init__(self):super().__init__(convert_charrefs=True);self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower() in self.blocked:self.skip+=1
        if tag.lower() in ('br','p','div','li','section','article','h1','h2','h3','tr'):self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag.lower() in self.blocked and self.skip:self.skip-=1
        if tag.lower() in ('p','div','li','section','article','h1','h2','h3','tr'):self.parts.append(' ')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def clean(s):
    if isinstance(s,(list,tuple)):
        s=' '.join(x for x in (clean(v) for v in s) if x)
    elif not isinstance(s,str) and callable(getattr(s,'itertext',None)):
        s=''.join(s.itertext())
    elif s is not None and not isinstance(s,str):
        return None
    if not s:return None
    p=Text();p.feed(html.unescape(s));p.close();t=' '.join(' '.join(p.parts).split());t=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',t).strip()
    return t[:2000] or None
def text(node,path):
    n=node.find(path)
    if n is None:return None
    return ''.join(n.itertext()).strip()

def content_hash(item):
    # Capture-time values are evidence, not story content; excluding them makes
    # the same item hash stable across naturally repeated feed reads.
    stable={k:v for k,v in item.items() if k not in ('collected_at','fetched_at','content_html')}
    return hashlib.sha256(canonical_json_dumps(stable).encode('utf-8')).hexdigest()

def safe_message(exc):
    message=str(exc) or type(exc).__name__
    message=re.sub(r'(?i)(password|secret|token|authorization|api[_-]?key)(\s*[:=]\s*)[^\s,;]+',r'\1\2[REDACTED]',message)
    message=re.sub(r'https?://[^\s"\']+',lambda m:sanitize_url(m.group(0)),message)
    message=re.sub(r'(?i)(postgres(?:ql)?://)[^/@\s]+:[^/@\s]+@',r'\1[REDACTED]@',message)
    return re.sub(r'[\r\n\t]+',' ',message)[:240]

def sanitize_url(value):
    try:
        p=urlsplit(value);query=[]
        for k,v in parse_qsl(p.query,keep_blank_values=True):
            query.append((k,'[REDACTED]' if re.search(r'(?i)(token|key|secret|auth|password|signature|sig)',k) else v))
        return urlunsplit((p.scheme,p.netloc,p.path,urlencode(query),'') )
    except Exception:return '[URL]'

def safe_trace(exc):
    """Traceback without source lines, local values, feed text, or absolute paths."""
    return [{'file':Path(f.filename).name,'function':f.name,'line':f.lineno} for f in traceback.extract_tb(exc.__traceback__)][-12:]

def log_failure(*,run_id,source_id,stage,exc,item_index=None,feed_format=None,field_names=None,value_types=None):
    record={'run_id':run_id,'source_id':source_id,'stage':stage,'exception_class':type(exc).__name__,'exception_message_sanitized':safe_message(exc),'stack_trace_sanitized':safe_trace(exc),'item_index':item_index,'feed_format':feed_format,'field_names':sorted(field_names or []),'value_types':value_types or {},'collector_version':VERSION}
    LOG.error(json.dumps(record,ensure_ascii=False,separators=(',',':')))
    return record
def parse(data,sid,received):
    root=ET.fromstring(data);tag=root.tag.rsplit('}',1)[-1].lower();nodes=[]
    xml_lang='{http://www.w3.org/XML/1998/namespace}lang'
    feed_language=root.attrib.get(xml_lang) or text(root,'channel/language') or text(root,'{*}language')
    # The publisher's own feed title is the only authoritative brand name in the
    # pipeline; the source document records URLs only.
    feed_title=clean(text(root,'channel/title') or text(root,'{*}title'))
    if tag in ('rss','rdf'):
        nodes=root.findall('.//{*}item')
    elif tag=='feed':nodes=root.findall('{*}entry')
    else:raise ValueError('unsupported_feed_format')
    items=[];rejected=0;seen=set()
    for n in nodes:
        try:
            title=text(n,'title') or text(n,'{*}title'); title=(title or '').strip()
            link=''
            for x in n.findall('link')+n.findall('{*}link'):
                href=x.attrib.get('href');rel=x.attrib.get('rel','alternate')
                if href and rel in ('alternate',''):link=href;break
                if x.text:link=x.text.strip();break
            link=link or text(n,'link') or text(n,'{*}link')
            u=urlsplit(link or '')
            if not title or len(title)>10000 or u.scheme not in ('http','https') or not u.hostname or u.username or u.password:raise ValueError()
            canonical=urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path or '/',urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith(('utm_','fbclid','gclid'))]),''))
            sidhash=hashlib.sha256((sid+'|'+canonical).encode()).hexdigest()
            if sidhash in seen:rejected+=1;continue
            seen.add(sidhash)
            candidates=[('content_encoded',text(n,'{http://purl.org/rss/1.0/modules/content/}encoded')),('description',text(n,'description')),('description',text(n,'{*}description')),('atom_summary',text(n,'{*}summary')),('atom_content',text(n,'{*}content'))]
            source=None;summary=None;content_html=None
            for kind,value in candidates:
                summary=clean(value)
                if summary:source=kind;content_html=value;break
            # The richest payload carries the body; a short description may coexist
            # with a full content:encoded block, so keep the largest for extraction.
            for kind,value in candidates:
                if kind in ('content_encoded','atom_content') and value and len(value)>len(content_html or ''):content_html=value
            rawdate=text(n,'pubDate') or text(n,'{*}published') or text(n,'{*}updated') or text(n,'{*}date');published=None
            if rawdate:
                try:
                    d=email.utils.parsedate_to_datetime(rawdate)
                    if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
                    published=d.astimezone(timezone.utc)
                except (TypeError,ValueError):
                    try:published=datetime.fromisoformat(rawdate.replace('Z','+00:00')).astimezone(timezone.utc)
                    except ValueError:published=None
            guid=text(n,'guid') or text(n,'{*}id')
            language=n.attrib.get(xml_lang) or feed_language
            items.append({'item_id':sidhash,'source_id':sid,'title':title,'canonical_url':canonical,'external_guid':guid,'published_at':published.isoformat() if published else None,'collected_at':received,'fetched_at':received,'summary_raw':summary,'summary_text':summary,'summary_source':source,'summary_available':bool(summary),'content_html':content_html,'content_language':language.strip()[:64] if language and language.strip() else None,'classification':None,'topics':[]})
        except (ValueError,TypeError):rejected+=1
    return items,len(nodes),rejected,{'feed_title':feed_title[:200] if feed_title else None,'feed_language':feed_language}
def atomic_json(path,obj):
    """Write a JSON checkpoint through a same-directory fsynced temp file."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=None
    try:
        fd,name=tempfile.mkstemp(prefix=f'.{path.name}.',suffix='.tmp',dir=path.parent);tmp=Path(name)
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
            json.dump(obj,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path);tmp=None
        try:
            dfd=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
            try:os.fsync(dfd)
            finally:os.close(dfd)
        except OSError:pass
    except BaseException:
        if tmp is not None:
            try:tmp.unlink()
            except OSError:pass
        raise

def read_checkpoint(path):
    """Read and validate a legacy-compatible JSON checkpoint."""
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:return None
    if not isinstance(data,dict) or not all(k in data for k in ('source_id','run_id','committed_at','last_http_status','response_sha256')):
        raise ValueError('invalid_checkpoint_shape')
    if not isinstance(data['source_id'],str) or not isinstance(data['run_id'],str) or not isinstance(data['response_sha256'],str):
        raise ValueError('invalid_checkpoint_types')
    return data

def store_content(c,item):
    """Persist body text and declared media for one item from its feed payload.

    Runs inside the caller's transaction and makes no network request: media rows
    record what the feed declared, and stay `unverified` until a separate,
    policy-aware pass checks them.
    """
    raw=item.get('content_html')
    if not raw:
        c.execute('''INSERT INTO news_item_content(item_id,original_language,original_text,text_chars,extraction_method,extraction_status,display_policy,source_url,content_sha256)
            VALUES(%s,%s,NULL,0,'feed_payload','unavailable','link_only',%s,NULL)
            ON CONFLICT(item_id) DO UPDATE SET extraction_status='unavailable',display_policy='link_only',updated_at=now()''',
            (item['item_id'],item.get('content_language'),item['canonical_url']))
        return 0
    result=extract_content(raw,item_id=item['item_id'],base_url=item['canonical_url'],summary_source=item.get('summary_source'))
    text=result['text'];policy=display_policy(item.get('summary_source'),text)
    digest=hashlib.sha256((text or '').encode('utf-8')).hexdigest() if text else None
    c.execute('''INSERT INTO news_item_content(item_id,content_version,original_language,original_text,text_chars,extraction_method,extraction_status,display_policy,source_url,content_sha256)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(item_id) DO UPDATE SET original_text=EXCLUDED.original_text,text_chars=EXCLUDED.text_chars,
        extraction_status=EXCLUDED.extraction_status,display_policy=EXCLUDED.display_policy,
        content_sha256=EXCLUDED.content_sha256,updated_at=now()
        WHERE news_item_content.content_sha256 IS DISTINCT FROM EXCLUDED.content_sha256''',
        (item['item_id'],CONTENT_VERSION,item.get('content_language'),text,len(text or ''),
         'feed_'+(item.get('summary_source') or 'unknown'),result['status'],policy,item['canonical_url'],digest))
    for m in result['media']:
        c.execute('''INSERT INTO news_item_media(media_id,item_id,kind,url,mime_type,declared_width,declared_height,alt_text,position,relevance,rejection_reason,discovery_method,verification_status)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(media_id) DO NOTHING''',
            (m['media_id'],m['item_id'],m['kind'],m['url'],m['mime_type'],m['declared_width'],m['declared_height'],
             m['alt_text'],m['position'],m['relevance'],m['rejection_reason'],m['discovery_method'],m['verification_status']))
    return len(result['media'])

def _source_start(c,runid,sid,started):
    """Insert exactly one running result before the bounded request begins."""
    with c.transaction():
        row=c.execute('''INSERT INTO source_run_results(run_id,source_id,started_at,status,http_requests)
            VALUES(%s,%s,%s,'running',1) ON CONFLICT (run_id,source_id) DO NOTHING RETURNING source_id''',(runid,sid,started)).fetchone()
        if row:return True
        old=c.execute('SELECT status FROM source_run_results WHERE run_id=%s AND source_id=%s',(runid,sid)).fetchone()
        raise RuntimeError('duplicate_source_result:'+str(old[0] if old else 'unknown'))

def _source_transition(c,runid,sid,*,status,finished,http_status=None,size=None,observed=None,inserted=None,duplicates=None,updates=None,rejected=None,error_class=None,error_message=None,error_stage=None,diagnostic=None,response_sha256=None,checkpoint_payload=None):
    if status not in SOURCE_TERMINAL and status!='running':raise ValueError('invalid_source_status')
    with c.transaction():
        row=c.execute('''UPDATE source_run_results SET status=%s,finished_at=%s,http_status=COALESCE(%s,http_status),response_bytes=COALESCE(%s,response_bytes),
            observed=COALESCE(%s,observed),inserted=COALESCE(%s,inserted),duplicates=COALESCE(%s,duplicates),updates=COALESCE(%s,updates),rejected=COALESCE(%s,rejected),http_requests=1,error_class=%s,
            error_message_sanitized=%s,error_stage=%s,diagnostic_json=%s,response_sha256=%s,
            checkpoint_payload=COALESCE(%s,checkpoint_payload)
            WHERE run_id=%s AND source_id=%s AND status IN ('running','committed_checkpoint_failed') RETURNING status''',
            (status,finished,http_status,size,observed,inserted,duplicates,updates,rejected,error_class,error_message,error_stage,Jsonb(diagnostic) if diagnostic is not None else None,response_sha256,Jsonb(checkpoint_payload) if checkpoint_payload is not None else None,runid,sid)).fetchone()
        if row:return row[0]
        old=c.execute('SELECT status FROM source_run_results WHERE run_id=%s AND source_id=%s',(runid,sid)).fetchone()
        if old and old[0]==status:return status
        raise RuntimeError('invalid_source_transition:'+str(old[0] if old else 'missing_source_result')+'->'+status)

def _error_status(stage):
    if stage=='fetch':return 'failed_fetch'
    if stage=='xml_parsing':return 'failed_parse'
    if stage in ('classification','normalization','content_extraction'):return 'failed_normalize'
    return 'failed_finalize'

def recover_pending_checkpoints():
    """Resume committed checkpoint payloads without fetching or reinserting items."""
    recovered=[];pending=[]
    with psycopg.connect(DSN) as c:
        pending=c.execute("SELECT run_id,source_id,checkpoint_payload FROM source_run_results WHERE status IN ('running','committed_checkpoint_failed') AND checkpoint_payload IS NOT NULL ORDER BY started_at,source_id").fetchall()
        for runid,sid,payload in pending:
            if isinstance(payload,str):payload=json.loads(payload)
            if payload.get('run_id')!=runid or payload.get('source_id')!=sid:raise ValueError('checkpoint_payload_identity_mismatch')
            try:atomic_json(STATE/(sid+'.json'),payload)
            except Exception as exc:
                diag=log_failure(run_id=runid,source_id=sid,stage='checkpoint_recovery',exc=exc)
                _source_transition(c,runid,sid,status='committed_checkpoint_failed',finished=datetime.now(timezone.utc),http_status=payload.get('last_http_status'),error_class=type(exc).__name__,error_message=safe_message(exc),error_stage='checkpoint_recovery',diagnostic=diag,checkpoint_payload=payload)
                continue
            _source_transition(c,runid,sid,status='succeeded',finished=datetime.now(timezone.utc),http_status=payload.get('last_http_status'),response_sha256=payload.get('response_sha256'),checkpoint_payload=payload)
            recovered.append((runid,sid))
    for runid in sorted({r for r,_ in recovered}):finalize_run(runid,interrupted=True)
    return recovered
def one_request(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname:raise ValueError('invalid_manifest_url')
    opener=build_opener(ProxyHandler(),NoRedirect())
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9'})
    started=datetime.now(timezone.utc)
    try:
        with opener.open(req,timeout=TIMEOUT) as r:
            status=r.status;chunks=[];total=0
            while True:
                b=r.read(min(65536,MAX_BYTES+1-total))
                if not b:break
                chunks.append(b);total+=len(b)
                if total>MAX_BYTES:raise ValueError('response_too_large')
            return status,b''.join(chunks),total,started,None
    except HTTPError as e:return e.code,b'',0,started,'http_error'
    except (URLError,TimeoutError,ValueError) as e:return None,b'',0,started,type(e).__name__
def source_run(c,runid,source):
    sid=source['source_id'];url=source['verified_feed_url'];started=datetime.now(timezone.utc)
    status=None;size=observed=inserted=duplicates=updates=rejected=0;items=[];stage='fetch';item_index=None;feed_format=None;digest=None;payload=None
    _source_start(c,runid,sid,started)
    try:
        status,body,size,reqstart,err=one_request(url)
        if status!=200:raise ValueError(err or 'http_status')
        stage='xml_parsing';items,observed,rejected,feed_meta=parse(body,sid,datetime.now(timezone.utc))
        try:feed_format=ET.fromstring(body).tag.rsplit('}',1)[-1].lower()
        except Exception:feed_format='unknown'
        digest=hashlib.sha256(body).hexdigest();stage='classification'
        for item_index,item in enumerate(items):
            r=cv.classify(item['title'],item['summary_text'])
            topics=list(dict.fromkeys(list(r.evidence)+[s['label'] for s in r.subtopics]))
            item['classification']=r.category_label;item['category_id']=r.category_id;item['topics']=topics
            item['classification_confidence']=r.confidence;item['classification_method']=r.method
            item['taxonomy_version']=r.taxonomy_version
        stage='database_transaction'
        with c.transaction():
            for item_index,i in enumerate(items):
                previous=c.execute('SELECT item_id,title,published_at,summary_text FROM news_items WHERE item_id=%s OR canonical_url=%s FOR UPDATE',(i['item_id'],i['canonical_url'])).fetchone()
                if previous:
                    if previous[0]==i['item_id'] and previous[1]==i['title'] and previous[2]==(datetime.fromisoformat(i['published_at']) if i['published_at'] else None) and previous[3]==i['summary_text']:duplicates+=1
                    else:updates+=1
                    stage='content_extraction'
                    if previous[0]==i['item_id']:store_content(c,i)
                    stage='database_transaction'
                    continue
                stage='content_hash';item_hash=content_hash(i);stage='database_insert'
                c.execute('''INSERT INTO news_items(item_id,source_id,title,summary,canonical_url,external_guid,published_at,collected_at,fetched_at,summary_raw,summary_text,summary_source,summary_available,content_language,adapter_type,provenance_status,content_hash,classification,taxonomy_version,topics) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'rss','COMPLETE',%s,%s,%s,%s) ON CONFLICT DO NOTHING''',(i['item_id'],sid,i['title'],i['summary_text'],i['canonical_url'],i['external_guid'],i['published_at'],i['collected_at'],i['fetched_at'],i['summary_raw'],i['summary_text'],i['summary_source'],i['summary_available'],i['content_language'],item_hash,i['classification'],i['taxonomy_version'],Jsonb(database_json(i['topics'],path='normalized_item.topics'))))
                if c.execute('SELECT 1 FROM news_items WHERE item_id=%s',(i['item_id'],)).fetchone():
                    c.execute('''INSERT INTO item_classifications(item_id,category_id,category_label,topics,taxonomy_version,method,confidence,reason)
                        SELECT %s,%s,%s,%s,%s,%s,%s,%s ON CONFLICT(item_id) DO NOTHING''',
                        (i['item_id'],i['category_id'],i['classification'],Jsonb(database_json(i['topics'],path='classification.topics')),i['taxonomy_version'],i['classification_method'],i['classification_confidence'],('matched: '+', '.join(i['topics'][:8])) if i['topics'] else 'no keyword matched'))
                    c.execute("INSERT INTO news_item_provenance(item_id,source_id,feed_url,execution_reference,evidence_status,evidence_json) VALUES(%s,%s,%s,%s,'COMPLETE',%s) ON CONFLICT(item_id) DO NOTHING",(i['item_id'],sid,url,runid,Jsonb(database_json({'http_status':status,'response_sha256':digest,'received_at':i['collected_at'],'summary_source':i['summary_source']},path='provenance_payload'))))
                    stage='content_extraction';store_content(c,i);stage='database_insert'
                    inserted+=1
                else:duplicates+=1
            committed=datetime.now(timezone.utc)
            payload={'source_id':sid,'run_id':runid,'committed_at':committed.isoformat(),'item_count':inserted,'last_http_status':status,'response_sha256':digest}
            c.execute("UPDATE sources SET last_attempt_at=%s,last_success_at=%s,last_http_status=%s,last_item_at=COALESCE((SELECT max(COALESCE(published_at,fetched_at)) FROM news_items WHERE source_id=%s),last_item_at),consecutive_failures=0,health_status='healthy',display_name=COALESCE(%s,display_name),language=COALESCE(language,%s),updated_at=now() WHERE source_id=%s",(started,committed,status,sid,feed_meta.get('feed_title'),feed_meta.get('feed_language'),sid))
            c.execute('''UPDATE source_run_results SET http_status=%s,response_bytes=%s,observed=%s,inserted=%s,duplicates=%s,updates=%s,rejected=%s,response_sha256=%s,checkpoint_payload=%s
                WHERE run_id=%s AND source_id=%s AND status='running' ''',(status,size,observed,inserted,duplicates,updates,rejected,digest,Jsonb(payload),runid,sid))
        stage='checkpoint'
        try:atomic_json(STATE/(sid+'.json'),payload)
        except Exception as exc:
            diag=log_failure(run_id=runid,source_id=sid,stage=stage,exc=exc,item_index=item_index,feed_format=feed_format,field_names=(items[item_index].keys() if item_index is not None and item_index<len(items) else ()),value_types=({k:type(v).__name__ for k,v in items[item_index].items()} if item_index is not None and item_index<len(items) else {}))
            _source_transition(c,runid,sid,status='committed_checkpoint_failed',finished=datetime.now(timezone.utc),http_status=status,size=size,observed=observed,inserted=inserted,duplicates=duplicates,updates=updates,rejected=rejected,error_class=type(exc).__name__,error_message=safe_message(exc),error_stage='checkpoint',diagnostic=diag,response_sha256=digest,checkpoint_payload=payload)
            return {'status':'committed_checkpoint_failed','attempted':1,'http_requests':1,'bytes':size,'observed':observed,'inserted':inserted,'duplicates':duplicates,'updates':updates,'rejected':rejected,'error':type(exc).__name__,'error_summary':'checkpoint: '+safe_message(exc)}
        _source_transition(c,runid,sid,status='succeeded',finished=datetime.now(timezone.utc),http_status=status,size=size,observed=observed,inserted=inserted,duplicates=duplicates,updates=updates,rejected=rejected,response_sha256=digest,checkpoint_payload=payload)
        return {'status':'succeeded','attempted':1,'http_requests':1,'bytes':size,'observed':observed,'inserted':inserted,'duplicates':duplicates,'updates':updates,'rejected':rejected,'error':None}
    except Exception as exc:
        diag=log_failure(run_id=runid,source_id=sid,stage=stage,exc=exc,item_index=item_index,feed_format=feed_format,field_names=(items[item_index].keys() if item_index is not None and item_index<len(items) else ()),value_types=({k:type(v).__name__ for k,v in items[item_index].items()} if item_index is not None and item_index<len(items) else {}))
        error_status=_error_status(stage);error_class=type(exc).__name__;error_message=safe_message(exc)
        try:
            with c.transaction():
                c.execute("UPDATE sources SET last_attempt_at=%s,last_http_status=%s,consecutive_failures=consecutive_failures+1,health_status=CASE WHEN consecutive_failures+1>=3 THEN 'failing' ELSE 'degraded' END,updated_at=now() WHERE source_id=%s",(started,status,sid))
            _source_transition(c,runid,sid,status=error_status,finished=datetime.now(timezone.utc),http_status=status,size=size,observed=observed,inserted=0,duplicates=0,updates=0,rejected=rejected,error_class=error_class,error_message=error_message,error_stage=stage,diagnostic=diag,response_sha256=digest,checkpoint_payload=payload)
        except Exception as secondary:
            secondary_diag=log_failure(run_id=runid,source_id=sid,stage='error_handler',exc=secondary,field_names=('primary_exception','primary_stage'),value_types={'primary_exception':error_class,'primary_stage':stage})
            LOG.error(json.dumps({'run_id':runid,'source_id':sid,'primary_error':diag,'secondary_error':secondary_diag},ensure_ascii=False,separators=(',',':')))
            return {'status':'failed_finalize','attempted':1,'http_requests':1,'bytes':size,'observed':observed,'inserted':0,'duplicates':0,'updates':None,'rejected':rejected,'error':error_class,'error_summary':f'{stage}: {error_message}; error_handler: {safe_message(secondary)}'}
        return {'status':error_status,'attempted':1,'http_requests':1,'bytes':size,'observed':observed,'inserted':0,'duplicates':0,'updates':0,'rejected':rejected,'error':error_class,'error_summary':f'{stage}: {error_message}'}

def finalize_run(runid,*,interrupted=False,run_error=None):
    """Finalize a run once from its persisted source results; repeat calls are no-ops."""
    with psycopg.connect(DSN) as c:
        with c.transaction():
            current=c.execute('SELECT status,sources_planned FROM collection_runs WHERE run_id=%s FOR UPDATE',(runid,)).fetchone()
            if not current:raise ValueError('collection_run_not_found')
            if current[0]!='running':return {'run_id':runid,'status':current[0],'already_finalized':True}
            c.execute("UPDATE source_run_results SET status='failed_finalize',finished_at=COALESCE(finished_at,now()),error_class=COALESCE(error_class,'RunFinalizedWithOpenSource'),error_message_sanitized=COALESCE(error_message_sanitized,'source did not reach a terminal state'),error_stage=COALESCE(error_stage,'finalize') WHERE run_id=%s AND status='running' AND checkpoint_payload IS NULL",(runid,))
            agg=c.execute('''SELECT count(*),count(*) FILTER(WHERE status='succeeded'),count(*) FILTER(WHERE status<>'succeeded'),
                COALESCE(sum(http_requests),0),COALESCE(sum(response_bytes),0),COALESCE(sum(observed),0),COALESCE(sum(inserted),0),
                COALESCE(sum(duplicates),0),CASE WHEN bool_or(updates IS NULL) THEN NULL ELSE COALESCE(sum(updates),0) END,COALESCE(sum(rejected),0),
                string_agg(source_id||':'||status||COALESCE(':'||error_message_sanitized,''),'; ' ORDER BY source_id) FILTER(WHERE status<>'succeeded')
                FROM source_run_results WHERE run_id=%s''',(runid,)).fetchone()
            attempted,succeeded,failed,requests,size,observed,inserted,duplicates,updates,rejected,errors=agg
            planned=current[1];status='succeeded' if attempted==planned and failed==0 else ('partial' if succeeded else 'failed')
            if interrupted or run_error:status='failed' if succeeded==0 else 'partial'
            summary='; '.join(x for x in (errors,run_error,'cycle_incomplete' if attempted<planned and not run_error else None) if x) or None
            c.execute('''UPDATE collection_runs SET finished_at=now(),status=%s,sources_attempted=%s,sources_succeeded=%s,sources_failed=%s,
                http_requests=%s,response_bytes=%s,items_observed=%s,items_inserted=%s,duplicates=%s,updates=%s,rejected=%s,error_summary=%s
                WHERE run_id=%s AND status='running' ''',(status,attempted,succeeded,failed,requests,size,observed,inserted,duplicates,updates,rejected,summary,runid))
            return {'run_id':runid,'status':status,'sources_attempted':attempted,'sources_succeeded':succeeded,'sources_failed':failed,'http_requests':requests,'items_inserted':inserted,'duplicates':duplicates,'updates':updates,'error_summary':summary}

def cycle(trigger='scheduled'):
    preflight_image()
    with psycopg.connect(DSN,autocommit=True) as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(%s)',(LOCK_KEY,)).fetchone()[0]:
            rid=str(uuid.uuid4());now=datetime.now(timezone.utc)
            lock.execute("INSERT INTO collection_runs(run_id,started_at,finished_at,trigger_type,status,sources_planned,skipped_locked,collector_version) VALUES(%s,%s,%s,%s,'skipped_locked',%s,true,%s)",(rid,now,now,trigger,len(EXEC),VERSION));return {'run_id':rid,'status':'skipped_locked'}
        rid=str(uuid.uuid4());start=datetime.now(timezone.utc);results=[];run_error=None;final=None
        try:
            # Planned count follows the executable set; a stale constant would mark
            # every run partial the moment a source is added.
            lock.execute("INSERT INTO collection_runs(run_id,started_at,trigger_type,status,sources_planned,collector_version) VALUES(%s,%s,%s,'running',%s,%s)",(rid,start,trigger,len(EXEC),VERSION))
            recover_pending_checkpoints()
            with psycopg.connect(DSN) as c:
                for src in sorted(EXEC.values(),key=lambda x:x['source_id']):
                    try:results.append(source_run(c,rid,src))
                    except Exception as exc:
                        diag=log_failure(run_id=rid,source_id=src['source_id'],stage='source_dispatch',exc=exc)
                        results.append({'status':'failed_finalize','attempted':0,'http_requests':0,'bytes':0,'observed':0,'inserted':0,'duplicates':0,'updates':None,'rejected':0,'error':type(exc).__name__,'error_summary':safe_message(exc)})
        except Exception as exc:
            diag=log_failure(run_id=rid,source_id='collector',stage='cycle',exc=exc)
            run_error=type(exc).__name__+': '+safe_message(exc)
        finally:
            try:final=finalize_run(rid,interrupted=bool(run_error),run_error=run_error)
            finally:lock.execute('SELECT pg_advisory_unlock(%s)',(LOCK_KEY,))
        return {**(final or {'run_id':rid,'status':'failed'}),'sources':results}
def run():
    interval=int(os.getenv('NEWS_COLLECTION_INTERVAL_SECONDS','900'));enabled=os.getenv('NEWS_COLLECTION_ENABLED','false').lower()=='true'
    if interval!=900:raise ValueError('NEWS_COLLECTION_INTERVAL_SECONDS must be 900')
    recover_pending_checkpoints()
    import threading
    stopping=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stopping.set());signal.signal(signal.SIGINT,lambda *_:stopping.set())
    started=datetime.now(timezone.utc);deadline=time.monotonic()+interval
    atomic_json(STATE/'health.json',{'started_at':started.isoformat(),'enabled':enabled,'interval_seconds':interval,'next_run_at':(started+__import__('datetime').timedelta(seconds=interval)).isoformat() if enabled else None})
    if not enabled:
        while not stopping.wait(60):atomic_json(STATE/'health.json',{'heartbeat_at':datetime.now(timezone.utc).isoformat(),'enabled':False,'interval_seconds':interval})
        return
    while not stopping.is_set():
        remaining=deadline-time.monotonic()
        if remaining>0:
            stopping.wait(min(10,remaining));atomic_json(STATE/'health.json',{'heartbeat_at':datetime.now(timezone.utc).isoformat(),'enabled':True,'interval_seconds':interval,'next_run_at':(datetime.now(timezone.utc)+__import__('datetime').timedelta(seconds=max(0,int(deadline-time.monotonic())))).isoformat()})
            continue
        result=cycle('scheduled');atomic_json(STATE/'last-cycle.json',result);deadline+=interval
        atomic_json(STATE/'health.json',{'heartbeat_at':datetime.now(timezone.utc).isoformat(),'enabled':True,'interval_seconds':interval,'next_run_at':(datetime.now(timezone.utc)+__import__('datetime').timedelta(seconds=max(0,int(deadline-time.monotonic())))).isoformat()})
if __name__=='__main__':run()
