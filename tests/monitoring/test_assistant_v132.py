"""Relevance gate v1.1.0 (assistant v1.3.2): rare-anchor link for reports the
clusterer left apart. Every other same-event condition stays mandatory."""
import assistant_relevance as ar
from test_assistant_v13 import R

FP7 = [R('a', 'Ukraine Says FP-7 Ballistic Missile Saw First Combat Use', 'Zelenskyy announced the first combat use of the FP-7 ballistic missile by Ukraine.',
         'TWZ', '2026-10-01T22:36:00+00:00'),
       R('b', 'Ukraine confirms first combat use of FP-7 missile', 'Ukraine has confirmed the first combat use of its FP-7 ballistic missile.',
         'Defence Industry Europe', '2026-10-04T15:50:00+00:00')]
RARE = {'FP-7': 2}


def test_rare_shared_code_links_unclustered_reports():
    groups = ar.verified_groups(FP7, None, RARE)
    assert len(groups) == 1 and len(groups[0]['members']) == 2
    assert groups[0]['pairs'][0]['link'] == 'rare_anchor' and groups[0]['pairs'][0]['rare_anchor'] == ['FP-7']


def test_without_rarity_data_nothing_changes():
    assert ar.verified_groups(FP7, None, None) == []


def test_common_code_does_not_link():
    assert ar.verified_groups(FP7, None, {'FP-7': ar.RARE_TITLE_MAX + 1}) == []


def test_rare_code_but_different_event_type_does_not_link():
    other = [FP7[0], R('c', 'Ukraine test-fires FP-7 missile at range', 'Ukraine conducted a test launch of the FP-7 missile.', 'X', '2026-10-02T10:00:00+00:00')]
    assert ar.verified_groups(other, None, RARE) == []


def test_rare_code_but_more_than_72h_does_not_link():
    late = [FP7[0], {**FP7[1], 'published_at': '2026-10-06T10:00:00+00:00'}]
    assert ar.verified_groups(late, None, RARE) == []


def test_rare_code_but_place_conflict_does_not_link():
    # Michigan (United States) and Spangdahlem (Germany) share no place or parent: a real geographic conflict.
    a = R('d', 'F-16 crash in Michigan', 'An F-16 crashed in Michigan; the jet carried pod XQ-9.', 'A', '2026-10-01T10:00:00+00:00')
    b = R('e', 'F-16 crash at Spangdahlem', 'An F-16 crashed at Spangdahlem; the jet carried pod XQ-9.', 'B', '2026-10-01T12:00:00+00:00')
    ok, why = ar.same_event(a, b, None, {'XQ-9': 2, 'F-16': 2})
    assert why['rare_anchor'] == ['F-16', 'XQ-9'] and why['time_ok'] and why['event_type_ok'] and why['entities_ok']
    assert why['place_conflict'] is True
    assert ok is False                      # every other condition holds: only the place conflict blocks the link
    ok2, why2 = ar.same_event(a, {**b, 'title': 'F-16 crash in Michigan', 'title_original': 'F-16 crash in Michigan',
                                     'excerpt': 'An F-16 crashed in Michigan; the jet carried pod XQ-9.'}, None, {'XQ-9': 2, 'F-16': 2})
    assert why2['place_conflict'] is False and ok2 is True   # control: same place -> linked


def test_cluster_link_still_works_and_is_labelled():
    a, b = ({**r, 'event_id': 'ev-1'} for r in FP7)
    ok, why = ar.same_event(a, b, None, None)
    assert ok and why['link'] == 'cluster'


def _lookup_records():
    return [R(x, f'Rheinmetall news {x}', f'Rheinmetall reported item {x} with a value of €750 million.', 'S' + x,
              f'2026-10-0{i + 1}T10:00:00+00:00') for i, x in enumerate('abc')]


class _Seq:
    """Fake adapter returning a scripted sequence of model payloads."""
    json_schema = None

    def __init__(self, payloads):
        self.payloads, self.calls = list(payloads), 0

    def stream_complete(self, system, user, should_cancel=lambda: False):
        import json as _j
        import types as _t
        self.calls += 1
        return _t.SimpleNamespace(raw_text=_j.dumps(self.payloads.pop(0)), tokens_in=0, tokens_out=0)


def test_entity_lookup_altered_quote_discards_extraction_and_retries_without_it():
    import assistant_v13 as v13
    recs = _lookup_records()
    bad = {'facts': [{'evidence_id': 'E1', 'quote': 'Rheinmetall reported item a with a value of €750 million.'},
                     {'evidence_id': 'E2', 'quote': 'Rheinmetall reported item b with a value of €75,000 million.'}], 'insufficient': False}
    good = {'facts': [{'evidence_id': 'E1', 'quote': 'Rheinmetall reported item a with a value of €750 million.'},
                      {'evidence_id': 'E2', 'quote': 'Rheinmetall reported item c with a value of €750 million.'}], 'insufficient': False}
    ad = _Seq([bad, good])
    out, problems, _, trace = v13.run(ad, 'اخبار مرتبط با راینمتال', recs, lambda s: s)
    assert ad.calls == 2 and out['kind'] == 'answer'
    assert trace['retry_without_altered'] == ['rec-b'] and out['set_aside_altered'] == ['rec-b']
    assert {c['record_id'] for c in out['citations']} == {'rec-a', 'rec-c'}          # the altered record is never cited
    assert '75,000' not in out['answer'] and 'کنار گذاشته شد' in out['answer']       # disclosed, fabricated text never shown


def test_entity_lookup_retry_must_itself_be_fully_verbatim():
    import assistant_v13 as v13
    recs = _lookup_records()
    bad = {'facts': [{'evidence_id': 'E2', 'quote': 'Rheinmetall reported item b with a value of €75,000 million.'}], 'insufficient': False}
    still_bad = {'facts': [{'evidence_id': 'E1', 'quote': 'Rheinmetall reported item a with a value of €7 billion.'}], 'insufficient': False}
    ad = _Seq([bad, still_bad])
    out, problems, _, _ = v13.run(ad, 'اخبار مرتبط با راینمتال', recs, lambda s: s)
    assert ad.calls == 2 and out['refusal_reason'] == 'no_valid_quote' and 'extraction_rejected' in problems


def test_event_intents_never_retry_after_altered_quote():
    import assistant_v13 as v13
    from test_assistant_v13 import MICH
    bad = {'facts': [{'evidence_id': 'E1', 'quote': 'An Air National Guard F-16 crashed in Ohio on Wednesday.'}], 'insufficient': False}
    ad = _Seq([bad])
    out, problems, _, _ = v13.run(ad, 'درباره سقوط F-16 در میشیگان چه گزارش شده است؟', MICH, lambda s: s)
    assert ad.calls == 1 and out['refusal_reason'] == 'no_valid_quote'


def test_version():
    assert ar.RELEVANCE_VERSION == 'relevance-gate-v1.1.0' and ar.RARE_TITLE_MAX == 5
