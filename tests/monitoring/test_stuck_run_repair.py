import json, pathlib, tempfile, unittest
from contextlib import contextmanager
from unittest.mock import patch
import repair_stuck_run as repair

class RepairCursor:
    def __init__(self,db):self.db=db;self.result=None;self.rowcount=1
    def execute(self,sql,params=()):
        if 'SELECT count(*) FROM pg_locks' in sql:self.result=(self.db.lock_count,)
        elif 'SELECT (SELECT count(*) FROM news_items)' in sql:self.result=(282,11,282)
        elif 'SELECT run_id,trigger_type,status,sources_planned' in sql:self.result=self.db.run
        elif 'SELECT repaired_at,repair_reason' in sql:self.result=(self.db.repaired_at,self.db.repair_reason)
        elif "SELECT conname,pg_get_constraintdef" in sql:self.result=('source_run_results_pkey','PRIMARY KEY (run_id, source_id)')
        elif 'SELECT run_id,source_id,status,http_status,response_bytes,observed' in sql:
            self.result=[(repair.RUN_ID,repair.SOURCE_ID,self.db.source_status,200,143641,10,0,0,0)]
        elif "SELECT status FROM source_run_results WHERE run_id=%s AND source_id=%s" in sql:self.result=(self.db.source_status,)
        elif sql.startswith("UPDATE source_run_results SET status='committed_checkpoint_failed'"):
            if self.db.source_status=='succeeded':self.db.source_status='committed_checkpoint_failed';self.result=(repair.SOURCE_ID,)
            else:self.rowcount=0;self.result=None
        elif sql.startswith("UPDATE collection_runs SET status='failed'"):
            if self.db.run[2]=='running':
                self.db.run=(self.db.run[0],self.db.run[1],'failed',11,1,0,1,1,143641,10,0,0,None,0,self.db.repaired_at,'1.1.0')
                self.db.repaired_at=params[1];self.db.repair_reason=params[2];self.result=('failed',)
            else:self.rowcount=0;self.result=None
        else:self.result=None
        return self
    def fetchone(self):return self.result
    def fetchall(self):return self.result or []

class RepairTx:
    def __init__(self,db):self.db=db
    def __enter__(self):return self
    def __exit__(self,exc_type,*args):return False

class FakeRepairDB:
    def __init__(self):
        self.lock_count=0;self.source_status='succeeded';self.repaired_at=None;self.repair_reason=None
        self.run=(repair.RUN_ID,'manual_validation','running',11,0,0,0,0,0,0,0,0,0,0,None,'1.1.0')
    def transaction(self):return RepairTx(self)
    def execute(self,sql,params=()):return RepairCursor(self).execute(sql,params)

class StuckRunRepairTests(unittest.TestCase):
    def evidence(self,tmp):
        p=pathlib.Path(tmp)/(repair.SOURCE_ID+'.json')
        p.write_text(json.dumps({'source_id':repair.SOURCE_ID,'run_id':repair.PREVIOUS_CHECKPOINT_RUN,'committed_at':'2026-09-20T00:00:00+00:00','last_http_status':200,'response_sha256':'previous'}),encoding='utf-8')
        digest=__import__('hashlib').sha256(p.read_bytes()).hexdigest()
        return p,digest

    def test_dry_run_checks_evidence_without_database_updates(self):
        db=FakeRepairDB()
        with tempfile.TemporaryDirectory() as d:
            _,digest=self.evidence(d)
            with patch.object(repair,'PREVIOUS_CHECKPOINT_SHA256',digest):
                result=repair.repair(db,collector_stopped=True,state_dir=d)
        self.assertEqual(result['mode'],'dry_run');self.assertFalse(result['applied'])
        self.assertEqual(db.run[2],'running');self.assertEqual(db.source_status,'succeeded')

    def test_apply_updates_only_target_run_and_second_apply_is_noop(self):
        db=FakeRepairDB()
        with tempfile.TemporaryDirectory() as d:
            _,digest=self.evidence(d)
            with patch.object(repair,'PREVIOUS_CHECKPOINT_SHA256',digest):
                first=repair.repair(db,apply=True,collector_stopped=True,state_dir=d)
                second=repair.repair(db,apply=True,collector_stopped=True,state_dir=d)
        self.assertTrue(first['applied']);self.assertEqual(db.run[2],'failed')
        self.assertEqual((db.run[4],db.run[5],db.run[6],db.run[7],db.run[8],db.run[9]),(1,0,1,1,143641,10))
        self.assertEqual(db.source_status,'committed_checkpoint_failed')
        self.assertTrue(second['no_op']);self.assertFalse(second['applied'])

    def test_active_advisory_lock_blocks_dry_run_and_apply(self):
        db=FakeRepairDB();db.lock_count=1
        with tempfile.TemporaryDirectory() as d:
            self.evidence(d)
            with self.assertRaisesRegex(repair.RepairBlocked,'advisory_lock_active'):
                repair.repair(db,collector_stopped=True,state_dir=d)
        self.assertEqual(db.run[2],'running')

    def test_missing_stopped_collector_confirmation_blocks_repair(self):
        with self.assertRaisesRegex(repair.RepairBlocked,'collector_stopped_confirmation_required'):
            repair.repair(FakeRepairDB(),apply=True,collector_stopped=False)

    def test_mismatched_source_result_blocks_repair(self):
        db=FakeRepairDB();db.source_status='failed_fetch'
        with tempfile.TemporaryDirectory() as d:
            _,digest=self.evidence(d)
            with patch.object(repair,'PREVIOUS_CHECKPOINT_SHA256',digest):
                with self.assertRaisesRegex(repair.RepairBlocked,'source_result_does_not_match'):
                    repair.repair(db,collector_stopped=True,state_dir=d)

if __name__=='__main__':unittest.main()
