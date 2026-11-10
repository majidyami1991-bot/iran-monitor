"""Read-only probe: score given item pairs with the production clustering
method (clustering_v2) over the whole stored corpus, to explain why two
reports were or were not clustered. Nothing is written.

  python /harness/assistant_v13_cluster_probe.py <item_prefix_a>:<item_prefix_b> ...
"""
import json
import os
import sys

import psycopg

import clustering_v2 as c2

with psycopg.connect(os.environ['DATABASE_URL']) as c:
    c.execute('SET TRANSACTION READ ONLY')
    rows = c.execute('''SELECT item_id, title, COALESCE(published_at, fetched_at, collected_at), source_id,
        COALESCE(NULLIF(btrim(summary_text), ''), summary, '') FROM news_items''').fetchall()
items = [c2.Item(r[0], r[1] or '', r[2], r[3], None, r[4]) for r in rows]
corpus = c2.Corpus(items)
by = {it.item_id[:12]: it for it in corpus.items}
out = []
for pair in sys.argv[1:]:
    a, b = (by[x[:12]] for x in pair.split(':'))
    res = c2.score_pair(corpus, a, b)
    out.append({'pair': pair, 'hours': round(c2._hours(a.published_at, b.published_at), 1),
                'distinctive_a': sorted(corpus.distinctive(a)), 'distinctive_b': sorted(corpus.distinctive(b)),
                'score': res[0] if res else None, 'reasons': res[1] if res else 'no qualifying pair (rule cut-off)',
                'min_pair_score': c2.MIN_PAIR_SCORE})
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
