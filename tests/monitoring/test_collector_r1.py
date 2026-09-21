import datetime, io, json, logging, sys, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '/app')
import collector
from ops import classify

FIXTURES=Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'
FAILED_IDS=[
 '1c638686-e35b-53e9-959c-dc122aa9079f','3bef586c-ca0d-5ee7-a837-beb5f31f510a',
 '516b4133-492d-5c4d-b021-b1113c54b756','854ac2a3-ba0c-5f95-a62b-6d296294960a',
 'a7040487-3b56-54d0-aa0a-a86ee5eac297','c1781f8f-c222-5fc4-99a9-5fcc73e5f537']

class FakeCursor:
    def __init__(self, conn): self.conn=conn; self.result=None; self.rowcount=1
    def execute(self, sql, params=()):
        self.conn.sql.append(sql)
        if sql.startswith('INSERT INTO source_run_results'):
            if self.conn.existing_result:self.rowcount=0;self.result=None
            else:self.conn.source_result_inserts+=1;self.conn.source_status='running';self.result=(params[1],)
        elif sql.startswith('UPDATE source_run_results SET status=%s'):
            if self.conn.source_status in ('running','committed_checkpoint_failed'):
                self.conn.source_status=params[0];self.result=(params[0],)
            else:self.rowcount=0;self.result=None
        elif sql.startswith('UPDATE source_run_results SET http_status='):
            self.conn.checkpoint_payload=params[8];self.result=None
        elif sql.startswith('SELECT status FROM source_run_results'):
            self.result=(self.conn.source_status,) if self.conn.source_status else None
        elif sql.startswith('SELECT item_id,title,published_at,summary_text'):
            self.result=self.conn.previous
        elif sql.startswith('INSERT INTO news_items'):
            self.conn.inserted.add(params[0]); self.result=None
        elif sql.startswith('SELECT 1 FROM news_items'):
            self.result=(1,) if params[0] in self.conn.inserted else None
        else: self.result=None
        return self
    def fetchone(self): return self.result
class Tx:
    def __init__(self,c):self.c=c
    def __enter__(self):return self
    def __exit__(self,t,v,b):
        if t is None:self.c.commits+=1
        else:self.c.rollbacks+=1
        return False
class FakeConnection:
    def __init__(self,previous=None):self.previous=previous;self.inserted=set();self.sql=[];self.commits=0;self.rollbacks=0;self.source_result_inserts=0;self.source_status=None;self.checkpoint_payload=None;self.existing_result=False
    def transaction(self):return Tx(self)
    def execute(self,sql,params=()):return FakeCursor(self).execute(sql,params)

def fixture_items(source_id):
    raw=(FIXTURES/f'{source_id}.xml').read_bytes()
    return collector.parse(raw,source_id,datetime.datetime(2026,9,21,9,0,tzinfo=datetime.timezone.utc))

class HistoricalFailureFixtures(unittest.TestCase):
    def test_all_six_reproduce_datetime_json_typeerror_before_fix_and_hash_after_fix(self):
        for sid in FAILED_IDS:
            with self.subTest(source_id=sid):
                items,observed,rejected=fixture_items(sid)
                self.assertEqual((observed,rejected),(1,0))
                item=items[0]
                with self.assertRaisesRegex(TypeError,'datetime is not JSON serializable'):
                    json.dumps(item,sort_keys=True)
                digest=collector.content_hash(item)
                self.assertEqual(len(digest),64)
                self.assertEqual(collector.content_hash(item),digest)
                self.assertEqual(item['source_id'],sid)

    def test_six_source_runs_complete_insert_path_offline(self):
        for sid in FAILED_IDS:
            with self.subTest(source_id=sid):
                items,_,_=fixture_items(sid); body=(FIXTURES/f'{sid}.xml').read_bytes(); conn=FakeConnection(); checkpoints=[]
                source={'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed.xml'}
                def request(_url):return 200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None
                def checkpoint(path,obj):
                    self.assertEqual(conn.commits,2)
                    checkpoints.append((str(path),obj))
                with patch.object(collector,'one_request',side_effect=request),patch.object(collector,'atomic_json',side_effect=checkpoint):
                    result=collector.source_run(conn,'offline-fixture-run',source)
                self.assertEqual(result['status'],'succeeded')
                self.assertEqual(result['inserted'],1)
                self.assertEqual(conn.commits,3)
                self.assertEqual(len(checkpoints),1)
                self.assertIn(items[0]['item_id'],conn.inserted)

    def test_update_candidate_is_never_overwritten_and_is_counted_duplicate_or_update(self):
        sid=FAILED_IDS[0]; items,_,_=fixture_items(sid); i=items[0]
        old_date=datetime.datetime.fromisoformat(i['published_at']) if i['published_at'] else None
        conn=FakeConnection((i['item_id'],i['title'],old_date,i['summary_text']))
        body=(FIXTURES/f'{sid}.xml').read_bytes()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'atomic_json'):
            result=collector.source_run(conn,'offline-update-run',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed.xml'})
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(result['duplicates'],1)
        self.assertFalse(any(x.startswith('INSERT INTO news_items') for x in conn.sql))

    def test_checkpoint_is_after_commit_and_failure_has_no_checkpoint(self):
        sid=FAILED_IDS[1]; body=(FIXTURES/f'{sid}.xml').read_bytes(); conn=FakeConnection()
        checkpoints=[]
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)):
            def check_checkpoint(path,obj):
                self.assertEqual(conn.commits,2)
                checkpoints.append(path)
            with patch.object(collector,'atomic_json',side_effect=check_checkpoint):
                result=collector.source_run(conn,'offline-commit-run',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed.xml'})
            self.assertEqual(result['status'],'succeeded')
            self.assertEqual(len(checkpoints),1)
        sid=FAILED_IDS[2]; body=(FIXTURES/f'{sid}.xml').read_bytes(); conn=FakeConnection()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'content_hash',side_effect=TypeError('injected')),patch.object(collector,'atomic_json') as checkpoint:
            result=collector.source_run(conn,'offline-failed-run',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed.xml'})
            self.assertEqual(result['status'],'failed_finalize')
            checkpoint.assert_not_called()

    def test_logging_is_sanitized_and_contains_diagnostic_shape(self):
        stream=io.StringIO();handler=logging.StreamHandler(stream);logger=collector.LOG;logger.addHandler(handler);logger.setLevel(logging.ERROR)
        try:
            try:raise TypeError('Object of type datetime is not JSON serializable token=TOPSECRET https://fixture.invalid/a?api_key=TOPSECRET&ok=1')
            except TypeError as exc:
                rec=collector.log_failure(run_id='r',source_id=FAILED_IDS[0],stage='content_hash',exc=exc,item_index=0,feed_format='rss',field_names=['title','collected_at'],value_types={'collected_at':'datetime'})
            log=stream.getvalue()
        finally:logger.removeHandler(handler)
        self.assertNotIn('TOPSECRET',log)
        self.assertIn('[REDACTED]',log)
        for key in ('run_id','source_id','stage','exception_class','exception_message_sanitized','stack_trace_sanitized','item_index','feed_format','field_names','value_types','collector_version'):
            self.assertIn(key,rec)
        self.assertNotIn('https://fixture.invalid/a?api_key=TOPSECRET',log)

    def test_malformed_nullable_list_object_string_and_invalid_date_are_safe(self):
        self.assertIsNone(collector.clean(None))
        self.assertIsNone(collector.clean({'unexpected':'object'}))
        self.assertEqual(collector.clean(['<p>first</p>',None,{'bad':'shape'},'second']),'first second')
        self.assertEqual(collector.clean('plain text'),'plain text')
        self.assertEqual(classify(None,{'unexpected':'object'})[0]['id'],'other')
        for sid in FAILED_IDS:
            item=fixture_items(sid)[0][0]
            self.assertIsNone(item['published_at']) if b'not-a-date' in (FIXTURES/f'{sid}.xml').read_bytes() else self.assertIsNotNone(item['published_at'])

    def test_relative_article_url_is_rejected_without_crashing_feed(self):
        xml=b'<rss><channel><item><title>Relative URL</title><link>/news/1</link></item><item><title>Valid</title><link>https://fixture.invalid/valid</link></item></channel></rss>'
        items,observed,rejected=collector.parse(xml,FAILED_IDS[0],datetime.datetime.now(datetime.timezone.utc))
        self.assertEqual((observed,rejected),(2,1));self.assertEqual(len(items),1)

if __name__=='__main__':unittest.main()
