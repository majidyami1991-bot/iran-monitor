import datetime, errno, json, pathlib, tempfile, unittest
from unittest.mock import patch

import collector

class AtomicCheckpointTests(unittest.TestCase):
    def payload(self):
        return {'source_id':'s-1','run_id':'r-1','committed_at':'2026-09-21T00:00:00+00:00','item_count':0,'last_http_status':200,'response_sha256':'a'*64}

    def test_atomic_json_uses_same_directory_and_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            target=pathlib.Path(d)/'s-1.json';real=collector.os.replace
            def check(src,dst):
                self.assertEqual(pathlib.Path(src).parent,pathlib.Path(dst).parent)
                return real(src,dst)
            with patch.object(collector.os,'replace',side_effect=check):collector.atomic_json(target,self.payload())
            self.assertEqual(collector.read_checkpoint(target),self.payload())
            self.assertEqual(list(pathlib.Path(d).iterdir()),[target])

    def test_permission_failure_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(collector.tempfile,'mkstemp',side_effect=PermissionError(errno.EACCES,'denied')):
                with self.assertRaises(PermissionError):collector.atomic_json(pathlib.Path(d)/'s.json',self.payload())
            self.assertEqual(list(pathlib.Path(d).iterdir()),[])

    def test_disk_full_cleans_partial_temp_and_preserves_original_error(self):
        with tempfile.TemporaryDirectory() as d:
            target=pathlib.Path(d)/'s.json';target.write_text('{"old":true}',encoding='utf-8')
            with patch.object(collector.json,'dump',side_effect=OSError(errno.ENOSPC,'disk full')):
                with self.assertRaisesRegex(OSError,'disk full'):collector.atomic_json(target,self.payload())
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')),{"old":True})
            self.assertEqual([x.name for x in pathlib.Path(d).iterdir()],['s.json'])

    def test_invalid_checkpoint_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'s.json';p.write_text('{',encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):collector.read_checkpoint(p)

class FakeTx:
    def __init__(self,c):self.c=c
    def __enter__(self):return self
    def __exit__(self,t,v,b):return False

class FakeRecoveryCursor:
    def __init__(self,c):self.c=c;self.rowcount=1;self.result=None
    def execute(self,sql,params=()):
        if 'SELECT run_id,source_id,checkpoint_payload' in sql:self.result=self.c.pending
        elif sql.startswith('UPDATE source_run_results SET status=%s'):
            target=params[0]
            if self.c.status in ('running','committed_checkpoint_failed'):
                self.c.status=target;self.result=(target,)
            else:self.rowcount=0;self.result=None
        elif sql.startswith('SELECT status FROM source_run_results'):
            self.result=(self.c.status,) if self.c.status else None
        else:self.result=None
        return self
    def fetchall(self):return self.result or []
    def fetchone(self):return self.result

class FakeRecoveryConnection:
    def __init__(self,pending=()):self.pending=list(pending);self.status='running'
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def transaction(self):return FakeTx(self)
    def execute(self,sql,params=()):return FakeRecoveryCursor(self).execute(sql,params)

class CheckpointRecoveryTests(unittest.TestCase):
    def test_restart_recovery_rewrites_checkpoint_without_network_or_item_insert(self):
        payload={'source_id':'s-1','run_id':'r-1','committed_at':'2026-09-21T00:00:00+00:00','item_count':1,'last_http_status':200,'response_sha256':'b'*64}
        conn=FakeRecoveryConnection([('r-1','s-1',payload)])
        with tempfile.TemporaryDirectory() as d, patch.object(collector,'STATE',pathlib.Path(d)), patch.object(collector.psycopg,'connect',return_value=conn), patch.object(collector,'finalize_run') as final, patch.object(collector,'one_request') as request:
            self.assertEqual(collector.recover_pending_checkpoints(),[('r-1','s-1')])
            self.assertEqual(collector.read_checkpoint(pathlib.Path(d)/'s-1.json'),payload)
            self.assertEqual(conn.status,'succeeded');final.assert_called_once_with('r-1',interrupted=True);request.assert_not_called()

    def test_checkpoint_payload_identity_mismatch_is_rejected(self):
        payload={'source_id':'other','run_id':'r-1','committed_at':'t','last_http_status':200,'response_sha256':'x'}
        conn=FakeRecoveryConnection([('r-1','s-1',payload)])
        with patch.object(collector.psycopg,'connect',return_value=conn):
            with self.assertRaisesRegex(ValueError,'identity_mismatch'):collector.recover_pending_checkpoints()

class SourceTransitionTests(unittest.TestCase):
    def test_source_result_is_inserted_once_and_later_updated(self):
        from test_collector_r1 import FakeConnection, FAILED_IDS
        sid=FAILED_IDS[0];body=(pathlib.Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'/f'{sid}.xml').read_bytes();c=FakeConnection()
        with tempfile.TemporaryDirectory() as d, patch.object(collector,'STATE',pathlib.Path(d)), patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)):
            result=collector.source_run(c,'r-once',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(result['status'],'succeeded');self.assertEqual(c.source_result_inserts,1)
        self.assertEqual(c.source_status,'succeeded')
        self.assertTrue(any('UPDATE source_run_results SET http_status=' in x for x in c.sql))

    def test_checkpoint_failure_after_commit_has_one_result_and_recoverable_status(self):
        from test_collector_r1 import FakeConnection, FAILED_IDS
        sid=FAILED_IDS[1];body=(pathlib.Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'/f'{sid}.xml').read_bytes();c=FakeConnection()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'atomic_json',side_effect=PermissionError('read-only')):
            result=collector.source_run(c,'r-checkpoint',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(result['status'],'committed_checkpoint_failed');self.assertEqual(c.source_result_inserts,1)
        self.assertEqual(c.source_status,'committed_checkpoint_failed');self.assertIsNotNone(c.checkpoint_payload)
        self.assertEqual(c.rollbacks,0)

    def test_duplicate_source_result_is_not_inserted_twice(self):
        from test_collector_r1 import FakeConnection
        c=FakeConnection();c.existing_result=True;c.source_status='succeeded'
        with patch.object(collector,'one_request') as request:
            with self.assertRaisesRegex(RuntimeError,'duplicate_source_result:succeeded'):
                collector.source_run(c,'r-duplicate',{'source_id':'s-1','verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(c.source_result_inserts,0);request.assert_not_called()

    def test_process_crash_after_commit_keeps_resume_payload(self):
        from test_collector_r1 import FakeConnection, FAILED_IDS
        sid=FAILED_IDS[3];body=(pathlib.Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'/f'{sid}.xml').read_bytes();c=FakeConnection()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'atomic_json',side_effect=SystemExit('process crash')):
            with self.assertRaisesRegex(SystemExit,'process crash'):collector.source_run(c,'r-crash-window',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(c.source_status,'running');self.assertIsNotNone(c.checkpoint_payload)
        self.assertEqual(c.source_result_inserts,1)

    def test_secondary_handler_error_does_not_mask_primary_exception(self):
        from test_collector_r1 import FakeConnection, FAILED_IDS
        sid=FAILED_IDS[4];body=(pathlib.Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'/f'{sid}.xml').read_bytes();c=FakeConnection()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'content_hash',side_effect=TypeError('primary datetime serialization')),patch.object(collector,'_source_transition',side_effect=RuntimeError('secondary database handler failure')):
            result=collector.source_run(c,'r-handler',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(result['error'],'TypeError');self.assertIn('secondary database handler failure',result['error_summary'])
        self.assertEqual(result['status'],'failed_finalize');self.assertEqual(c.source_result_inserts,1)

    def test_error_handler_updates_existing_source_result_not_inserts_again(self):
        from test_collector_r1 import FakeConnection
        c=FakeConnection();c.source_status='running'
        result=collector._source_transition(c,'r','s',status='failed_fetch',finished=datetime.datetime.now(datetime.timezone.utc),error_class='URLError',error_message='offline',error_stage='fetch')
        self.assertEqual(result,'failed_fetch');self.assertEqual(c.source_result_inserts,0)
        result2=collector._source_transition(c,'r','s',status='failed_fetch',finished=datetime.datetime.now(datetime.timezone.utc))
        self.assertEqual(result2,'failed_fetch');self.assertEqual(c.source_result_inserts,0)

    def test_typeerror_fixture_failure_never_calls_checkpoint_and_preserves_typeerror(self):
        from test_collector_r1 import FakeConnection, FAILED_IDS
        sid=FAILED_IDS[2];body=(pathlib.Path(__file__).parent/'fixtures'/'phase-8b-failed-feeds'/f'{sid}.xml').read_bytes();c=FakeConnection()
        with patch.object(collector,'one_request',return_value=(200,body,len(body),datetime.datetime.now(datetime.timezone.utc),None)),patch.object(collector,'content_hash',side_effect=TypeError('injected')) as hashfn,patch.object(collector,'atomic_json') as checkpoint:
            result=collector.source_run(c,'r-typeerror',{'source_id':sid,'verified_feed_url':'https://fixture.invalid/feed'})
        self.assertEqual(result['status'],'failed_finalize');self.assertEqual(result['error'],'TypeError')
        hashfn.assert_called_once();checkpoint.assert_not_called();self.assertEqual(c.source_result_inserts,1)

class FinalizeCursor:
    def __init__(self,db):self.db=db;self.result=None
    def execute(self,sql,params=()):
        if sql.startswith('SELECT status,sources_planned'):self.result=(self.db.status,11)
        elif sql.startswith("UPDATE source_run_results SET status='failed_finalize'"):self.result=None
        elif sql.startswith('SELECT count(*),count(*) FILTER'):
            self.result=(1,0,1,1,143641,10,0,0,None,0,'source:committed_checkpoint_failed:read-only')
        elif sql.startswith('UPDATE collection_runs SET finished_at='):
            self.db.status=params[0];self.db.finalize_calls+=1;self.result=None
        else:self.result=None
        return self
    def fetchone(self):return self.result

class FinalizeConnection:
    def __init__(self):self.status='running';self.finalize_calls=0
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def transaction(self):return FakeTx(self)
    def execute(self,sql,params=()):return FinalizeCursor(self).execute(sql,params)

class RunFinalizationTests(unittest.TestCase):
    def test_finalize_twice_is_idempotent(self):
        db=FinalizeConnection()
        with patch.object(collector.psycopg,'connect',return_value=db):
            first=collector.finalize_run('r-final')
            second=collector.finalize_run('r-final')
        self.assertEqual(first['status'],'failed');self.assertEqual(second['status'],'failed')
        self.assertTrue(second['already_finalized']);self.assertEqual(db.finalize_calls,1)

if __name__=='__main__':unittest.main()
