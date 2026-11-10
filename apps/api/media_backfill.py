"""Offline media backfill (no network request of any kind).

    python /app/media_backfill.py --feeds-dir /evidence/feeds [--dry-run]

1. Re-parses saved raw feed payloads (captured earlier by one audit read per
   feed) with the collector's own parser and stores the RSS media each
   already-collected item declares.
2. Re-evaluates every stored image row under the current media policy
   (v2 columns only; legacy columns are left as they are).
3. Recomputes the single primary image for every item.

Idempotent: a second run writes nothing. news_items, translations,
provenance, staging and checkpoints are never written.
"""
import argparse
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

import collector
import media_pipeline as mp

DSN = os.environ['DATABASE_URL']


def usable_primary_items(c):
    return {r[0] for r in c.execute('''SELECT item_id FROM news_item_media WHERE kind='image' AND is_primary
        AND COALESCE(validation_status,'unknown') NOT IN ('rejected','blocked','unreachable')''').fetchall()}


def reevaluate_rows(c):
    """Apply the current rejection rules to every stored image row."""
    changed = 0
    cur = c.cursor(row_factory=dict_row)
    rows = cur.execute('''SELECT media_id, url, canonical_url, original_url, source_method, source_field, width, height, mime_type,
        file_size_bytes, alt_text, caption, credit, position, validation_status, policy_rejection_reason, policy_version, policy_score
        FROM news_item_media WHERE kind='image' ''').fetchall()
    for r in rows:
        cand = mp._row_to_candidate(r)
        if r['validation_status'] in ('valid', 'blocked', 'unreachable'):
            new_status = r['validation_status']
        elif cand.rejection_reason:
            new_status = 'rejected'
        else:
            new_status = 'pending' if cand.insecure_http else 'unknown'
        new_reason = cand.rejection_reason if new_status == 'rejected' else None
        if (new_status, new_reason, cand.score, mp.POLICY_VERSION) != (r['validation_status'], r['policy_rejection_reason'],
                                                                      r.get('policy_score'), r['policy_version']):
            # v2 columns only: legacy rejection_reason/relevance stay as the old API expects.
            cur2 = c.execute('''UPDATE news_item_media SET validation_status=%s, policy_rejection_reason=%s, policy_score=%s,
                policy_version=%s, updated_at=now() WHERE media_id=%s AND (validation_status, policy_rejection_reason, policy_score, policy_version)
                IS DISTINCT FROM (%s, %s, %s, %s)''',
                             (new_status, new_reason, cand.score, mp.POLICY_VERSION, r['media_id'],
                              new_status, new_reason, cand.score, mp.POLICY_VERSION))
            changed += cur2.rowcount
    return changed


def run(feeds_dir, dry_run=False):
    report = {'feeds': 0, 'feed_items': 0, 'feed_items_in_db': 0, 'rss_candidates': 0, 'by_method': {}}
    with psycopg.connect(DSN) as c:
        before = usable_primary_items(c)
        db_items = {r[0] for r in c.execute('SELECT item_id FROM news_items').fetchall()}
        writes = 0
        targets = set()
        for f in sorted(Path(feeds_dir).glob('*.xml')):
            sid = f.stem
            items, _, _, _ = collector.parse(f.read_bytes(), sid, '1970-01-01T00:00:00+00:00')
            report['feeds'] += 1
            for it in items:
                report['feed_items'] += 1
                if it['item_id'] not in db_items:
                    continue
                report['feed_items_in_db'] += 1
                cands = [mp.Candidate(**d) for d in it.get('rss_media', [])]
                for cd in cands:
                    report['by_method'][cd.source_method] = report['by_method'].get(cd.source_method, 0) + 1
                report['rss_candidates'] += len(cands)
                if cands:
                    targets.add(it['item_id'])
                    writes += mp.persist(c, it['item_id'], cands)
        writes += reevaluate_rows(c)
        for iid in sorted(db_items):
            writes += mp.reselect_primary(c, iid)
        after = usable_primary_items(c)
        report.update({'items_total': len(db_items), 'items_with_primary_before': len(before),
                       'items_with_primary_after': len(after), 'target_items_with_rss_media': len(targets),
                       'recovered_items': len((after - before) & targets), 'gained_primary_total': len(after - before),
                       'lost_primary': len(before - after), 'lost_primary_sample': sorted(before - after)[:10],
                       'rows_written': writes, 'dry_run': dry_run})
        if dry_run:
            c.rollback()
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--feeds-dir', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    print(json.dumps(run(args.feeds_dir, args.dry_run), indent=1))
