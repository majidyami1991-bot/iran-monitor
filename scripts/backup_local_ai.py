"""Backup of the 3003 Local-AI database with SHA-256, an isolated restore test
and a second copy on another disk. Never deletes anything.

  python scripts/backup_local_ai.py [--second-copy D:/IranMonitorBackups/local-ai] [--no-restore-test]

Steps
  1. pg_dump -Fc inside the ai-db container (read-only for the data) -> runtime/backups-local-ai/
  2. SHA-256 of the dump file
  3. restore test in a THROWAWAY postgres:16-alpine container with --network none
     (never in a running database): pg_restore, then exact row counts of the key
     tables compared with the live counts taken in the same snapshot as the dump
  4. copy to --second-copy (different physical disk), re-hash, free-space check first
  5. one JSON line in runtime/ops-status/backups/manifest.jsonl (read by the admin page)
Secrets: the dump contains no credentials; the DB password is never read here
(the throwaway container uses its own trust auth on no network).
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runtime' / 'backups-local-ai'
MANIFEST = ROOT / 'runtime' / 'ops-status' / 'backups' / 'manifest.jsonl'
DB = 'iran-monitor-local-ai-ai-db-1'
IMAGE = 'postgres:16-alpine'
KEY_TABLES = ['news_items', 'news_item_content', 'news_item_translations', 'news_item_translation_history', 'news_events',
              'news_event_members', 'item_topic_assignments', 'assistant_sessions', 'assistant_messages', 'news_sync_runs']
_NOWIN = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, **_NOWIN, **kw)
    if r.returncode != 0:
        raise RuntimeError(f'{cmd[:4]} failed: {r.stderr.decode("utf-8", "replace")[-800:]}')
    return r.stdout.decode('utf-8', 'replace')


def count_sql():
    return ' UNION ALL '.join(f"SELECT '{t}', (SELECT count(*) FROM {t})" for t in KEY_TABLES) + ';'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--second-copy', default='D:/IranMonitorBackups/local-ai')
    ap.add_argument('--no-restore-test', action='store_true')
    a = ap.parse_args()
    ts = datetime.now(timezone.utc)
    stamp = ts.strftime('%Y%m%dT%H%M%SZ')
    OUT.mkdir(parents=True, exist_ok=True)
    dump = OUT / f'ai-db-{stamp}.dump'
    rec = {'ts': ts.isoformat(), 'db': '3003 ai-db', 'dump': dump.name}
    # 1. counts right before and after the dump: equal => no writes in between for these tables (exact VERIFIED)
    before = sh(['docker', 'exec', '-i', DB, 'sh', '-c', 'psql -X -At -F "|" -U "$POSTGRES_USER" -d "$POSTGRES_DB"'], input=count_sql().encode())
    sh(['docker', 'exec', DB, 'sh', '-c', 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/backup.dump'])
    after = sh(['docker', 'exec', '-i', DB, 'sh', '-c', 'psql -X -At -F "|" -U "$POSTGRES_USER" -d "$POSTGRES_DB"'], input=count_sql().encode())
    sh(['docker', 'cp', f'{DB}:/tmp/backup.dump', str(dump)])
    sh(['docker', 'exec', DB, 'rm', '-f', '/tmp/backup.dump'])
    live_b = dict(x.split('|') for x in before.split())
    live_a = dict(x.split('|') for x in after.split())
    rec['sha256'] = sha256(dump)
    rec['size_bytes'] = dump.stat().st_size
    rec['live_counts_before'], rec['live_counts_after'] = live_b, live_a
    Path(str(dump) + '.sha256').write_text(f'{rec["sha256"]}  {dump.name}\n', encoding='utf-8')
    # 3. isolated restore test
    if not a.no_restore_test:
        name = f'restore-test-{uuid.uuid4().hex[:8]}'
        try:
            sh(['docker', 'run', '-d', '--rm', '--name', name, '--network', 'none', '-e', 'POSTGRES_HOST_AUTH_METHOD=trust',
                '-e', 'POSTGRES_USER=defence_monitor', '-e', 'POSTGRES_DB=restore_test', IMAGE])
            for _ in range(60):
                if subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'defence_monitor', '-d', 'restore_test'],
                                  capture_output=True, **_NOWIN).returncode == 0:
                    break
                time.sleep(1)
            time.sleep(2)
            sh(['docker', 'cp', str(dump), f'{name}:/tmp/r.dump'])
            r = subprocess.run(['docker', 'exec', name, 'pg_restore', '-U', 'defence_monitor', '-d', 'restore_test', '--no-owner', '/tmp/r.dump'],
                               capture_output=True, **_NOWIN)
            rec['restore_warnings'] = r.stderr.decode('utf-8', 'replace').count('error:')
            restored = dict(x.split('|') for x in sh(['docker', 'exec', '-i', name, 'psql', '-X', '-At', '-F', '|', '-U', 'defence_monitor',
                                                      '-d', 'restore_test'], input=count_sql().encode()).split())
            rec['restored_counts'] = restored
            stable = live_b == live_a
            rec['verify'] = ('VERIFIED' if stable and restored == live_b else
                             'VERIFIED_WITHIN_CONCURRENT_WRITES' if all(int(live_b[t]) <= int(restored[t]) <= int(live_a[t]) for t in KEY_TABLES)
                             else 'MISMATCH')
        finally:
            subprocess.run(['docker', 'stop', name], capture_output=True, **_NOWIN)   # --rm removes the throwaway container
    # 4. second copy
    dest = Path(a.second_copy)
    try:
        free = shutil.disk_usage(dest.anchor).free
        if free < rec['size_bytes'] * 20:
            raise RuntimeError(f'not enough free space on {dest.anchor}: {free}')
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dump, dest / dump.name)
        shutil.copy2(str(dump) + '.sha256', dest / (dump.name + '.sha256'))
        rec['second_copy'] = str(dest)
        rec['second_copy_sha_ok'] = sha256(dest / dump.name) == rec['sha256']
        rec['second_copy_free_gb'] = round(free / 1e9)
    except (OSError, RuntimeError) as exc:
        rec['second_copy'] = None
        rec['second_copy_error'] = str(exc)[:200]
    rec['offsite'] = 'not_configured (needs a target and key custody decision)'
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(json.dumps({k: rec.get(k) for k in ('dump', 'sha256', 'size_bytes', 'verify', 'restore_warnings', 'second_copy', 'second_copy_sha_ok')}, indent=1))
    return 0 if rec.get('verify', 'VERIFIED').startswith('VERIFIED') and rec.get('second_copy_sha_ok') else 1


if __name__ == '__main__':
    sys.exit(main())
