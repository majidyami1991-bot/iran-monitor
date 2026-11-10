"""Scheduled wrapper for scripts/news_sync.py (one run per invocation).

  * single instance: an exclusive lock file; a lock older than STALE_SECONDS
    or held by a dead process is taken over (and logged);
  * Docker or either database container not running -> 'skipped' (exit 0),
    so a host without Docker produces a log line, not an error storm;
  * the sync itself runs in a child process with a timeout; its own
    transaction guarantees all-or-nothing, so the next cycle is the retry;
  * one JSON line per invocation in runtime/news-sync/scheduler.jsonl.

  pythonw scripts/news_sync_scheduled.py [--max-new 500]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runtime' / 'news-sync'
LOCK = RUNS / 'scheduler.lock'
LOG = RUNS / 'scheduler.jsonl'
STALE_SECONDS = 1800
TIMEOUT_SECONDS = 900
CONTAINERS = ('defence-monitor-news-news-db-1', 'iran-monitor-local-ai-ai-db-1')
_NOWIN = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


def _log(rec):
    RUNS.mkdir(parents=True, exist_ok=True)
    rec['ts'] = datetime.now(timezone.utc).isoformat()
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def _pid_alive(pid):
    if sys.platform == 'win32':
        r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True, **_NOWIN)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire():
    """True if this process now holds the lock."""
    RUNS.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({'pid': os.getpid(), 'at': time.time()}).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                held = json.loads(LOCK.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                held = {'pid': -1, 'at': 0}
            if time.time() - held.get('at', 0) > STALE_SECONDS or not _pid_alive(held.get('pid', -1)):
                _log({'event': 'stale_lock_taken_over', 'held': held})
                LOCK.unlink(missing_ok=True)
                continue
            return False
    return False


def docker_ready():
    for c in CONTAINERS:
        r = subprocess.run(['docker', 'inspect', '-f', '{{.State.Running}}', c], capture_output=True, text=True, timeout=30, **_NOWIN)
        if r.returncode != 0 or r.stdout.strip() != 'true':
            return False, f'{c} not running' if r.returncode == 0 else 'docker_unreachable'
    return True, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-new', type=int, default=500)
    a = ap.parse_args()
    if not acquire():
        _log({'event': 'skipped', 'reason': 'previous_run_still_active'})
        return 0
    t0 = time.time()
    try:
        try:
            ok, why = docker_ready()
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok, why = False, f'docker_cli_error:{type(exc).__name__}'
        if not ok:
            _log({'event': 'skipped', 'reason': why})
            return 0
        try:
            r = subprocess.run([sys.executable.replace('pythonw.exe', 'python.exe'), str(ROOT / 'scripts' / 'news_sync.py'),
                                'apply', '--max-new', str(a.max_new)], capture_output=True, timeout=TIMEOUT_SECONDS, **_NOWIN)
            out = r.stdout.decode('utf-8', 'replace')
            try:
                s = json.loads(out)
            except ValueError:
                s = {'status': 'failed', 'error': (out + r.stderr.decode('utf-8', 'replace'))[-800:]}
            applied = s.get('applied') or {}
            _log({'event': 'run', 'run_id': s.get('run_id'), 'status': s.get('status'), 'error': s.get('error'),
                  'seconds': round(time.time() - t0, 1), 'deferred_new_items': s.get('deferred_new_items'),
                  'inserted_items': (applied.get('news_items') or {}).get('inserted'),
                  'updated_items': (applied.get('news_items') or {}).get('updated')})
            return 0 if s.get('status') == 'succeeded' else 1
        except subprocess.TimeoutExpired:
            _log({'event': 'run', 'status': 'failed', 'error': f'timeout_{TIMEOUT_SECONDS}s'})
            return 1
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
