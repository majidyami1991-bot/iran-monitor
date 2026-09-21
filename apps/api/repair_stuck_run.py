"""Evidence-bound, idempotent repair for the single R2 checkpoint-failure run.

Default mode is read-only. Apply requires --apply and --collector-stopped.
This utility never fetches sources and never changes item/provenance rows.
"""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
from ops import DSN

RUN_ID='c8ab7a29-9832-434b-9607-ab0dffdcbebf'
SOURCE_ID='02125465-dc6c-5355-823c-989b485ed491'
PREVIOUS_CHECKPOINT_RUN='0f800369-f4b3-4e3b-9065-11122462daa6'
PREVIOUS_CHECKPOINT_SHA256='d1e1ba9196eb8db84ec0aa20e894bd8b80ec63b3c9700d609be67be7a7ebd371'
REPAIR_REASON='checkpoint_write_failed_after_source_commit'

class RepairBlocked(RuntimeError):pass

def _evidence(conn,state_dir):
    lock=conn.execute("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND granted AND database=(SELECT oid FROM pg_database WHERE datname=current_database())").fetchone()[0]
    if lock:raise RepairBlocked('advisory_lock_active')
    counts=conn.execute('SELECT (SELECT count(*) FROM news_items),(SELECT count(*) FROM sources),(SELECT count(*) FROM news_item_provenance)').fetchone()
    if counts!=(282,11,282):raise RepairBlocked('database_baseline_mismatch')
    run=conn.execute('''SELECT run_id,trigger_type,status,sources_planned,sources_attempted,sources_succeeded,sources_failed,http_requests,
        response_bytes,items_observed,items_inserted,duplicates,updates,rejected,finished_at,collector_version
        FROM collection_runs WHERE run_id=%s''',(RUN_ID,)).fetchone()
    if not run:raise RepairBlocked('target_run_missing')
    if run[2]=='failed':
        repaired=conn.execute('SELECT repaired_at,repair_reason FROM collection_runs WHERE run_id=%s',(RUN_ID,)).fetchone()
        if repaired and repaired[0] and repaired[1]==REPAIR_REASON:
            repaired_source=conn.execute('SELECT status FROM source_run_results WHERE run_id=%s AND source_id=%s',(RUN_ID,SOURCE_ID)).fetchone()
            if repaired_source==('committed_checkpoint_failed',):return {'already_repaired':True,'run_id':RUN_ID,'status':'failed','repair_reason':REPAIR_REASON}
            raise RepairBlocked('terminal_run_repair_evidence_mismatch')
    expected=(RUN_ID,'manual_validation','running',11,0,0,0,0,0,0,0,0,0,0,None,'1.1.0')
    if tuple(run)!=expected:raise RepairBlocked('target_run_does_not_match_r2_evidence')
    result_rows=conn.execute('''SELECT run_id,source_id,status,http_status,response_bytes,observed,inserted,duplicates,rejected
        FROM source_run_results WHERE run_id=%s ORDER BY source_id''',(RUN_ID,)).fetchall()
    if result_rows!=[(RUN_ID,SOURCE_ID,'succeeded',200,143641,10,0,0,0)]:raise RepairBlocked('source_result_does_not_match_r2_evidence')
    constraint=conn.execute("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='source_run_results'::regclass AND conname='source_run_results_pkey'").fetchone()
    if not constraint or constraint[1]!='PRIMARY KEY (run_id, source_id)':raise RepairBlocked('source_result_constraint_mismatch')
    checkpoint=Path(state_dir)/(SOURCE_ID+'.json')
    if not checkpoint.is_file():raise RepairBlocked('prior_checkpoint_missing')
    digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    try:checkpoint_doc=json.loads(checkpoint.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise RepairBlocked('prior_checkpoint_invalid') from exc
    if digest!=PREVIOUS_CHECKPOINT_SHA256 or checkpoint_doc.get('run_id')!=PREVIOUS_CHECKPOINT_RUN or checkpoint_doc.get('source_id')!=SOURCE_ID:
        raise RepairBlocked('prior_checkpoint_evidence_mismatch')
    return {'already_repaired':False,'run_id':RUN_ID,'source_id':SOURCE_ID,'status_before':'running','source_status_before':'succeeded','http_status':200,'http_requests':1,'response_bytes':143641,'items_observed':10,'items_inserted':0,'duplicates':0,'updates':'unknown_not_persisted','rejected':0,'database_counts':{'items':282,'sources':11,'provenance':282},'advisory_lock_active':False,'previous_checkpoint_run_id':PREVIOUS_CHECKPOINT_RUN,'previous_checkpoint_sha256':digest,'repair_reason':REPAIR_REASON,'unique_constraint':constraint[0]}

def repair(conn,*,apply=False,collector_stopped=False,state_dir='/state'):
    if not collector_stopped:raise RepairBlocked('collector_stopped_confirmation_required')
    with conn.transaction():
        evidence=_evidence(conn,state_dir)
        if evidence['already_repaired']:
            evidence.update({'mode':'apply' if apply else 'dry_run','applied':False,'no_op':True})
            return evidence
        if not apply:
            evidence.update({'mode':'dry_run','applied':False,'no_op':False})
            return evidence
        repaired_at=datetime.now(timezone.utc)
        diag={'repair_reason':REPAIR_REASON,'primary_error':{'class':'OSError','stage':'checkpoint','message_sanitized':'read-only filesystem at API /state mount'},'secondary_error':{'class':'UniqueViolation','constraint':'source_run_results_pkey','columns':['run_id','source_id'],'message_sanitized':'error handler attempted a second source-result insert'},'evidence_reference':'PHASE 8B-R2 sanitized report and ignored runtime evidence'}
        source=conn.execute('''UPDATE source_run_results SET status='committed_checkpoint_failed',finished_at=%s,http_requests=1,updates=NULL,
            error_class='OSError',error_message_sanitized='checkpoint write failed on read-only API state mount',error_stage='checkpoint',diagnostic_json=%s
            WHERE run_id=%s AND source_id=%s AND status='succeeded' AND http_status=200 AND response_bytes=143641
            AND observed=10 AND inserted=0 AND duplicates=0 AND rejected=0 RETURNING source_id''',(repaired_at,Jsonb(diag),RUN_ID,SOURCE_ID)).fetchone()
        if source!=(SOURCE_ID,):raise RepairBlocked('conditional_source_repair_did_not_match')
        run=conn.execute('''UPDATE collection_runs SET status='failed',finished_at=%s,repaired_at=%s,repair_reason=%s,
            sources_planned=11,sources_attempted=1,sources_succeeded=0,sources_failed=1,http_requests=1,response_bytes=143641,
            items_observed=10,items_inserted=0,duplicates=0,updates=NULL,rejected=0,
            error_summary='checkpoint_write_failed_after_source_commit; secondary_error=UniqueViolation(source_run_results_pkey); updates_count=unknown'
            WHERE run_id=%s AND status='running' AND trigger_type='manual_validation' AND finished_at IS NULL RETURNING status''',
            (repaired_at,repaired_at,REPAIR_REASON,RUN_ID)).fetchone()
        if run!=('failed',):raise RepairBlocked('conditional_run_repair_did_not_match')
        evidence.update({'mode':'apply','applied':True,'no_op':False,'status_after':'failed','repaired_at':repaired_at.isoformat()})
        return evidence

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--collector-stopped',action='store_true',help='confirm Docker inspection shows the collector is stopped')
    parser.add_argument('--apply',action='store_true',help='apply the evidence-bound repair; default is dry-run')
    args=parser.parse_args()
    if args.run_id!=RUN_ID:raise SystemExit('repair_blocked: unsupported_run_id')
    try:
        with psycopg.connect(DSN) as conn:
            result=repair(conn,apply=args.apply,collector_stopped=args.collector_stopped,state_dir='/state')
    except RepairBlocked as exc:raise SystemExit('repair_blocked: '+str(exc))
    print(json.dumps(result,ensure_ascii=False,separators=(',',':')))

if __name__=='__main__':main()
