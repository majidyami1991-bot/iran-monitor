"""Builds the human review pack for Assistant v1.3.x from gate reports.

Read-only: gate JSON files + the stored ORIGINAL text of every record
involved (exactly the title and excerpt the pipeline sees). Every human
review field is left empty.

  python /harness/assistant_v13_review_pack.py /evidence/phase5/v131-gate-real-A.json \
      /evidence/phase5/v131-gate-real-B.json /evidence/phase5/out.md
"""
import json
import os
import sys

import psycopg

import retrieval

A = {i['case']: i for i in json.load(open(sys.argv[1], encoding='utf-8'))['items']}
RA = json.load(open(sys.argv[1], encoding='utf-8'))
B = {i['case']: i for i in json.load(open(sys.argv[2], encoding='utf-8'))['items']}
OUT = sys.argv[3]

REASON_TEXT = {
    'ambiguous_event': 'more than one distinct event matches every anchor; the assistant does not choose or merge',
    'same_event_not_established': 'the records could not be proven to be one event',
    'single_source': 'only one independent outlet remains after removing duplicates',
    'no_relevant_record': 'no record contains every anchor and the event type in its original text',
    'unresolved_conflict': 'sources of one event report different numbers or a denial',
    'no_valid_quote': 'no verbatim, relevant quote survived validation',
    'out_of_contract_prediction': 'prediction is outside the v1.3 contract (refused before retrieval)',
    'out_of_contract_analysis': 'independent analysis / motive / uncertainty judgement is outside the contract (refused before retrieval)',
    'out_of_contract_ranking': 'importance ranking is outside the contract (refused before retrieval)',
    'record_not_found': 'no record with that id',
}
PROBLEM_TEXT = {
    'title_fallback': "the model did not quote this member of the verified event; its verbatim title is shown so no outlet is hidden",
    'core_quote_title': "the model's sentence did not name every entity of the question; the record's verbatim title (which does) was used instead",
    'quote_irrelevant': "a model sentence that names no anchor/event of the question was dropped",
    'quote_case_normalised': "the model capitalised the first letter of a mid-sentence quote; the exact source text is shown",
    'unsafe_quote_dropped': "a sentence carrying instructions or a link was dropped",
}


def fetch(c, ids):
    out = {}
    for rid in ids:
        r = c.execute('''SELECT n.item_id, n.title, COALESCE(NULLIF(btrim(n.summary_text), ''), n.summary), n.canonical_url,
            COALESCE(n.published_at, n.fetched_at, n.collected_at), COALESCE(NULLIF(s.display_name, ''), s.hostname), n.source_id,
            (SELECT string_agg(em.event_id, ', ') FROM news_event_members em WHERE em.item_id = n.item_id)
            FROM news_items n JOIN sources s USING (source_id) WHERE n.item_id = %s''', (rid,)).fetchone()
        if r:
            title, excerpt, _ = retrieval._excerpt({'title': r[1], 'summary': r[2], 'title_fa': None, 'summary_fa': None}, use_translations=False)
            out[rid] = {'id': r[0], 'title': title, 'excerpt': excerpt, 'url': r[3], 'published_at': r[4].isoformat() if r[4] else None,
                        'source': r[5], 'source_id': r[6], 'events': r[7] or '—'}
    return out


def record_block(rec, tag=''):
    return (f"- **{rec['source']}** (source id `{rec['source_id']}`) — {rec['published_at'][:16] if rec['published_at'] else '—'} UTC{tag}  \n"
            f"  news id `{rec['id']}` · event (cluster) `{rec['events']}` · {rec['url']}  \n"
            f"  > **{rec['title']}**  \n  > {rec['excerpt'] or '(no summary text stored)'}\n")


def explain_problems(problems):
    lines = []
    for p in problems or []:
        key, _, eid = p.partition(':')
        if key in PROBLEM_TEXT:
            lines.append(f'  - `{p}` — {PROBLEM_TEXT[key]}')
    return lines


with psycopg.connect(os.environ['DATABASE_URL']) as c:
    c.execute('SET TRANSACTION READ ONLY')
    md = []
    for case, it in A.items():
        ids = [r['record_id'] for r in it.get('records_given') or []]
        relevant = [x['record_id'] for x in it.get('relevance') or [] if x.get('ok')]
        excluded = it.get('excluded_unverified') or []
        recs = fetch(c, list(dict.fromkeys(ids + relevant[:8] + excluded[:6])))
        p = it['plan']
        md.append(f"\n---\n\n## {case}\n")
        md.append(f"**Question:** {it['question']}\n")
        md.append(f"**Analysis:**")
        md.append(f"- intent `{p['intent']}`")
        md.append(f"- anchors {', '.join(a['canonical'] + ' (' + a['from'] + ')' for a in p['anchors']) or '—'}")
        md.append(f"- event types {', '.join(p['event_types']) or '—'}")
        md.append(f"- window `{p['window'] or 'all'}`; quantity question: {p['quantity']}")
        if p['out_of_contract']:
            md.append(f"- out of contract: `{p['out_of_contract']}`")
        md.append('')
        md.append(f"**Retrieval:** {it['retrieved_count']} candidate records; {it['relevant_count'] if it['relevant_count'] is not None else '—'} passed the relevance gate "
                  f"(every anchor + event type in the original title/excerpt).")
        if it.get('verified_groups'):
            md.append(f"**Verified same-event groups:** " + '; '.join('[' + ', '.join(f'`{m[:12]}`' for m in g['members']) + ']' for g in it['verified_groups'][:6]) +
                      (f" (+{len(it['verified_groups']) - 6} more)" if len(it['verified_groups']) > 6 else ''))
        if it.get('primary_events') and len(it['primary_events']) > 1:
            md.append(f"**Primary-matching events (all anchors in a member's title):** " + '; '.join('[' + ', '.join(f'`{m[:12]}`' for m in e) + ']' for e in it['primary_events']))
        md.append('')
        if ids:
            md.append('**Evidence given to the model (full original text as seen by the pipeline):**\n')
            for rid in ids:
                md.append(record_block(recs[rid]))
        elif relevant:
            md.append('**Records that passed the relevance gate (not sent to the model; reason below):**\n')
            for rid in relevant[:8]:
                md.append(record_block(recs[rid]))
        if excluded:
            md.append(f'**Related records excluded as not verified to be the same event ({len(excluded)}):**\n')
            for rid in excluded[:6]:
                md.append(record_block(recs[rid], ' — *excluded, not cited*'))
        md.append(f"**Assistant answer (run A):**\n\n```\n{it['answer']}\n```\n")
        if it['kind'] != 'answer':
            md.append(f"**Why refused:** `{it['refusal_reason']}` — {REASON_TEXT.get(it['refusal_reason'], '')}. "
                      f"Shown to the user: «{it.get('refusal_reason_fa') or ''}»\n")
        ex = explain_problems(it['problems'])
        if ex:
            md.append('**Evidence selection notes (deterministic rules applied):**')
            md += ex
            md.append('')
        b = B.get(case)
        if b and b['answer'] != it['answer']:
            md.append(f"**Run B (after a model unload/reload) gave a different answer — review both:**\n\n```\n{b['answer']}\n```\n")
            md += explain_problems(b['problems'])
            md.append('')
        elif b:
            md.append('Run B (after a model unload/reload): identical answer.\n')
        md.append(f"**Machine result:** {it['machine_decision']} — " + ', '.join(f"{k}={'✔' if v else '✘'}" for k, v in it['machine_checks'].items()) + '\n')
        md.append('**Human review:**\n')
        md.append('| Check | Yes | No | Note |\n|---|---|---|---|')
        for q in ('Every cited record is about what the question asks', 'Each quote is faithful in context (not misleading)',
                  'Nothing relevant and verifiable is wrongly left out', 'A refusal (if any) is justified',
                  'Decision: accept this item'):
            md.append(f'| {q} | ☐ | ☐ |  |')
        md.append('\nReviewer: ______________  Date: __________\n')

    head = [f"# Assistant v1.3.1 — human review pack",
            '',
            f"Contract `{RA['approval']}`, fingerprint `{RA['fingerprint'][:16]}…`.",
            f"Prompt `{RA['prompt_version']}`, validator `{RA['validator_version']}`, lexicon `{RA['lexicon_version']}`, relevance `{RA['relevance_version']}`.",
            '',
            f"Source reports: `{os.path.basename(sys.argv[1])}` (run A) and `{os.path.basename(sys.argv[2])}` (run B, after a model unload/reload).",
            'Both are gitignored, in `runtime/local-ai-evidence/phase5/`. This pack is generated from them by `scripts/assistant_v13_review_pack.py`.',
            '',
            'The evidence text is the **original** title and excerpt exactly as the pipeline sees it. Stored machine translations are never used.',
            '**No human-review box is pre-filled.** The machine result is not a human decision.',
            '',
            '## How to review',
            '',
            '1. For each item, read the question, then the evidence text, then the answer.',
            '2. For an answer, check:',
            '   - every cited record is about the question;',
            '   - each quote means in context what the answer suggests;',
            '   - no relevant, verifiable record shown under the item was wrongly left out.',
            '3. For a refusal: is it justified given the records shown?',
            '4. Tick Yes or No for each check, and add a note where needed.',
            '5. A single *No* on relevance or faithfulness is a critical finding. It keeps the assistant `BLOCKED_MODEL_QUALITY`.',
            '']
    open(OUT, 'w', encoding='utf-8').write('\n'.join(head + md) + '\n')
    print('written', OUT, len(A), 'items')
