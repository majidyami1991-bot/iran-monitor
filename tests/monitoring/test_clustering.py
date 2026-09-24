"""Offline event-clustering tests. The core positive/negative pair below is
real data (anonymized IDs) found in the live database while building this
phase — not a synthetic strawman — and is what the threshold was calibrated
against: two articles sharing only generic domain words ("IDF", "terror")
must not cluster, while two articles sharing a distinctive surname must."""
from datetime import datetime, timezone

import clustering as cl

T0 = datetime(2026, 9, 24, 6, 0, 0, tzinfo=timezone.utc)


def mk(item_id, title, hours_offset=0, category='security', url=None, text='', guid=None):
    from datetime import timedelta
    return cl.ItemFeatures.build(item_id, title, text, T0 + timedelta(hours=hours_offset),
                                  category, url or f'https://example.com/{item_id}', guid)


def test_shared_surname_clusters_two_articles_about_the_same_person():
    a = mk('leiter1', 'IDF Reservist Neriya Leiter Fighting for His Life After Terror Attack', hours_offset=0, category='diplomacy')
    b = mk('leiter2', 'Channel 12 Reporter Mocks Netanyahu Over Injured Terror Victim Neriyah Leiter', hours_offset=-1, category='diplomacy')
    pair = cl.score_pair(a, b)
    assert pair.score >= cl.CLUSTER_THRESHOLD
    assert 'leiter' in pair.reasons['shared_entities']


def test_shared_generic_domain_words_alone_do_not_cluster():
    a = mk('leiter1', 'IDF Reservist Neriya Leiter Fighting for His Life After Terror Attack', hours_offset=0, category='diplomacy')
    c = mk('hamas1', 'IDF Eliminates Hamas Finance Chief Who Funneled Over $1 Billion to Terror', hours_offset=-0.15, category='security')
    pair = cl.score_pair(a, c)
    assert pair.score < cl.CLUSTER_THRESHOLD
    assert pair.reasons['shared_entities'] == []


def test_full_pipeline_clusters_only_the_true_positive_pair():
    a = mk('leiter1', 'IDF Reservist Neriya Leiter Fighting for His Life After Terror Attack', 0, 'diplomacy')
    b = mk('hamas1', 'IDF Eliminates Hamas Finance Chief Who Funneled Over $1 Billion to Terror', -0.15, 'security')
    c = mk('leiter2', 'Channel 12 Reporter Mocks Netanyahu Over Injured Terror Victim Neriyah Leiter', -0.9, 'diplomacy')
    clusters = cl.cluster_items([a, b, c])
    assert len(clusters) == 1
    assert set(clusters[0]['members']) == {'leiter1', 'leiter2'}
    assert 'hamas1' not in clusters[0]['members']


def test_identical_canonical_url_always_clusters_regardless_of_text():
    a = mk('dup1', 'Completely different headline one', url='https://example.com/same-story')
    b = mk('dup2', 'Totally unrelated headline two', url='https://example.com/same-story')
    pair = cl.score_pair(a, b)
    assert pair.score == 1.0
    assert pair.reasons.get('exact_url_match')


def test_items_far_apart_in_time_are_never_compared():
    a = mk('old', 'A story about a naval exercise', hours_offset=0)
    b = mk('new', 'A story about a naval exercise', hours_offset=cl.MAX_HOURS_APART + 10)
    assert cl.score_pair(a, b) is None


def test_no_false_cluster_from_a_single_shared_common_word():
    a = mk('a1', 'Iran announces new missile test near border')
    b = mk('a2', 'Israel conducts naval exercise near coast', hours_offset=-2)
    pair = cl.score_pair(a, b)
    assert pair.score < cl.CLUSTER_THRESHOLD


def test_clustering_is_deterministic_across_runs():
    items = [mk('c', 'Neriya Leiter update three', 0, 'diplomacy'),
             mk('a', 'Neriya Leiter update one', -1, 'diplomacy'),
             mk('b', 'Neriya Leiter update two', -2, 'diplomacy')]
    r1 = cl.cluster_items(list(items))
    r2 = cl.cluster_items(list(reversed(items)))
    assert r1 == r2


def test_rerunning_clustering_on_the_same_items_produces_the_same_clusters():
    items = [mk('leiter1', 'Neriya Leiter injured in attack', 0, 'diplomacy'),
             mk('leiter2', 'Neriya Leiter recovering in hospital', -3, 'diplomacy')]
    first = cl.cluster_items(items)
    second = cl.cluster_items(items)
    assert first == second


def test_three_articles_about_the_same_event_form_one_cluster_not_pairs():
    items = [mk('x1', 'Neriya Leiter attacked near checkpoint', 0, 'diplomacy'),
             mk('x2', 'Neriya Leiter condition improves say doctors', -2, 'diplomacy'),
             mk('x3', 'Officials visit injured Neriya Leiter in hospital', -4, 'diplomacy')]
    clusters = cl.cluster_items(items)
    assert len(clusters) == 1
    assert set(clusters[0]['members']) == {'x1', 'x2', 'x3'}


def test_singleton_items_with_no_match_are_not_returned_as_clusters():
    items = [mk('solo1', 'A unique story about wheat prices'),
             mk('solo2', 'A unique story about coral reefs', -1)]
    assert cl.cluster_items(items) == []
