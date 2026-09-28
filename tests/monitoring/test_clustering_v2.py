"""Offline tests for event clustering v2. Titles are real corpus headlines."""
from datetime import datetime, timedelta, timezone

import clustering_v2 as cl

T0 = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def item(i, title, hours=0, source='s1', text=''):
    return cl.Item(f'id{i:03d}', title, T0 + timedelta(hours=hours), source, None, text)


# Enough unrelated items that corpus document frequency behaves as it does
# on the real corpus (a 3-item corpus makes every word "common").
FILLER = [item(100 + k, f'Unrelated filler headline number {k} about Budget Reform', hours=k, source=f'f{k}',
               text='the budget and the reform were discussed') for k in range(40)]


def run(items):
    return cl.cluster(items + FILLER)


def test_same_event_from_three_sources_clusters():
    got = run([item(1, 'USAF F-16 Crashes At Spangdahlem Air Base In Germany', 0, 'twz'),
               item(2, 'US F-16 Crashes at Spangdahlem Air Base, Pilot Ejects Safely', 2, 'jfeed'),
               item(3, 'F-16 Crashes in Germany; Pilot Successfully Ejects at Spangdahlem', 3, 'afm')])
    assert [c['members'] for c in got] == [['id001', 'id002', 'id003']]


def test_title_case_phrases_are_not_entities():
    # The v2 prototype merged these on "Goes Viral"; lowercase use in running
    # text marks them as ordinary words.
    got = run([item(1, 'Gantz Loses His Last Mandate After Coffee Post Goes Viral', 0, text='the post goes viral quickly'),
               item(2, 'Zelensky Bizarre Behavior at Meeting Goes Viral', 1, text='a clip that goes viral')])
    assert got == []


def test_complete_linkage_blocks_chaining():
    # A~B share "Anduril Barracuda", B~C share "Latvia"; A and C share nothing.
    a = item(1, 'Air Force Certifies Anduril Barracuda Missile', 0, 'x')
    b = item(2, 'Latvia To Order Anduril Barracuda Missile', 1, 'y')
    c = item(3, 'Latvia Opens Tallinn Border Crossing Talks', 2, 'z')
    for cluster in run([a, b, c]):
        assert not {'id001', 'id003'} <= set(cluster['members'])


def test_far_apart_in_time_never_merge():
    got = run([item(1, 'Navantia completes S-83 AIP trials', 0, 'a'),
               item(2, 'Navantia completes S-83 AIP trials', 24 * 10, 'b')])
    assert got == []


def test_multiword_name_counts_once():
    got = run([item(1, 'Turkey Ally Calls to Destroy Tel Aviv', 0), item(2, 'Boy George Announces Tel Aviv Concert', 1)])
    assert got == []


def test_possessive_normalised_and_deterministic():
    x = [item(1, "Two Years Since Nasrallah's Elimination Broke Axis", 0),
         item(2, 'Lebanon Marks Two Years Since Nasrallah Elimination', 1)]
    assert run(x) == run(list(reversed(x)))
    assert run(x)[0]['members'] == ['id001', 'id002']


def test_event_title_is_earliest_member():
    a, b = item(1, 'Later report', 5), item(2, 'First report', 1)
    assert cl.event_title([a, b]) == 'First report'
