"""Assistant v1.3 dry run: question analysis, read-only retrieval and the
deterministic selection (relevance gate, same-event verification) on the real
isolated DB. No model call, nothing written.

  python /harness/assistant_v13_dryrun.py "question" ["question" ...]
"""
import json
import os
import sys

import assistant_relevance as ar
import assistant_v13 as v13
import retrieval


def dry(q):
    plan = ar.analyse(q)
    pre = ar.precheck(plan)
    v = plan.view()
    row = {'question': q, 'plan': f"{v['intent']} anchors={[a['canonical'] for a in v['anchors']]} ev={v['event_types']} "
                                  f"qty={v['quantity']} ooc={v['out_of_contract']} unres={v['unresolved']}", 'precheck': pre}
    if pre:
        return row
    found = retrieval.search_v13(os.environ['DATABASE_URL'], plan)
    cands = found['records']
    row['candidates'] = len(cands)
    if plan.intent == 'common_coverage' and not plan.anchors and not plan.event_types:
        groups = ar.verified_groups(v13._renumber(cands), plan)
        row['verified_groups'] = [[(m['record_id'][:12], m['source_name'], m['title'][:70]) for m in g['members']] for g in groups]
        return row
    recs, group, copies, reason, trace = v13.select(plan, cands)
    row.update(reason=reason, relevant=trace.get('relevant'), distinct_events=trace.get('distinct_events'),
               verified_groups=[[m[:12] for m in g['members']] for g in trace.get('verified_groups') or []],
               primary_events=[[m[:12] for m in e] for e in trace.get('primary_events') or []],
               relevant_records=[(x['record_id'][:12]) for x in trace['relevance'] if x['ok']],
               selected=[(r['evidence_id'], r['record_id'][:12], r['event_id'], r['source_name'], r['title'][:90]) for r in recs],
               copies=sorted(copies))
    return row


if __name__ == '__main__':
    out = [dry(q) for q in sys.argv[1:]]
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
