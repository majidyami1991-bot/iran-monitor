"""Independent check of every quote/citation in a v1.3 gate report against
the DB (read-only): record exists; quote occurs verbatim (whitespace-
normalised) in the stored ORIGINAL title or summary; source, date and URL of
the citation match the record. Translations are not consulted.

  python /harness/assistant_v13_verify_citations.py /evidence/phase4/v13-gate-real.json
"""
import json
import os
import re
import sys

import psycopg

norm = lambda s: re.sub(r'\s+', ' ', s or '').strip()
rep = json.load(open(sys.argv[1], encoding='utf-8'))
rows, bad = 0, []
with psycopg.connect(os.environ['DATABASE_URL']) as c:
    c.execute('SET TRANSACTION READ ONLY')
    for it in rep['items']:
        cites = {ci['evidence_id']: ci for ci in it['citations']}
        for f in it['selected_evidence'] or [{'evidence_id': ci['evidence_id'], 'record_id': ci['record_id'], 'quote': ci['title']}
                                               for ci in it['citations']]:
            ci = cites.get(f['evidence_id'])
            rid = f.get('record_id') or (ci or {}).get('record_id')
            r = c.execute('''SELECT n.title, COALESCE(NULLIF(btrim(n.summary_text), ''), n.summary), n.canonical_url,
                COALESCE(n.published_at, n.fetched_at, n.collected_at), COALESCE(NULLIF(s.display_name, ''), s.hostname)
                FROM news_items n JOIN sources s USING (source_id) WHERE n.item_id = %s''', (rid,)).fetchone()
            rows += 1
            if not r:
                bad.append((it['case'], rid, 'record_missing')); continue
            title, summ, url, pub, src = r
            if norm(f['quote']) not in norm(title) + ' \n ' + norm(summ):
                bad.append((it['case'], rid[:12], 'quote_not_in_original', f['quote'][:80]))
            if ci and (ci['source_name'] != src or ci['canonical_url'] != url or (ci['published_at'] or '')[:19] != pub.isoformat()[:19]):
                bad.append((it['case'], rid[:12], 'metadata_mismatch'))
print(json.dumps({'report': sys.argv[1], 'quotes_checked': rows, 'failures': bad}, ensure_ascii=False, indent=1))
