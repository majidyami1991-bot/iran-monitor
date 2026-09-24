"""Offline tests for the v2 multi-level classifier. Uses the real shipped
taxonomy file (not a mock) so a taxonomy edit that breaks matching is caught
here, not only in production."""
import classify_v2 as cv


def test_subtopic_evidence_alone_selects_the_parent_category():
    # Real defect found while building this: a subtopic match (e.g. "missile")
    # was discarded unless the parent category's own generic words ("military",
    # "defense") also appeared verbatim, which "a guided missile test" never
    # says. The subtopic match must be sufficient on its own.
    r = cv.classify('North Korea Tests a Guided Rocket',
                     'State media said the missile was a ballistic missile test.')
    assert r.category_id == 'defense_security'
    assert any(s['id'] == 'missile' for s in r.subtopics)


def test_air_subtopic_from_fighter_jet_language():
    r = cv.classify('Russia delivers upgraded Su-57', 'The Russian air force received an upgraded fighter jet.')
    assert r.category_id == 'defense_security'
    assert any(s['id'] == 'air' for s in r.subtopics)


def test_nuclear_category_with_multiple_evidence_gets_higher_confidence_than_single_hit():
    strong = cv.classify('Iran nuclear talks resume', 'Diplomats discussed uranium enrichment and IAEA inspections of the nuclear program.')
    weak = cv.classify('A story mentioning nuclear once', 'This story just says nuclear and nothing else related.')
    assert strong.category_id == 'nuclear'
    assert strong.confidence > weak.confidence


def test_unrelated_text_falls_back_to_other_with_zero_confidence():
    r = cv.classify('Recipe of the week', 'This article describes how to bake a chocolate cake.')
    assert r.category_id == 'other'
    assert r.confidence == 0.0
    assert r.evidence == []


def test_confidence_is_capped_below_one():
    r = cv.classify('Missile air defense drone cyber naval ground army',
                     'missile ballistic air defense sam drone uav fighter jet navy destroyer tank artillery cyberattack malware')
    assert r.confidence <= 0.95


def test_empty_text_is_other_and_does_not_raise():
    r = cv.classify('', '')
    assert r.category_id == 'other'


def test_taxonomy_version_and_method_are_carried_on_the_result():
    r = cv.classify('Iran sanctions', 'New sanctions were imposed on the central bank.')
    assert r.taxonomy_version == '2.0.0'
    assert r.method


def test_evidence_list_has_no_duplicate_entries():
    r = cv.classify('missile missile missile', 'missile missile ballistic ballistic')
    assert len(r.evidence) == len(set(e.casefold() for e in r.evidence))


def test_short_ascii_keyword_matches_as_a_whole_word_not_a_substring():
    taxonomy = {
        'version': 'test', 'method': 'test',
        'fallback': {'id': 'other', 'label': 'سایر'},
        'categories': [{'id': 'x', 'label': 'X', 'keywords_en': ['gas'], 'keywords_fa': []}],
    }
    c = cv.Classifier(taxonomy)
    inside_a_longer_word = c.classify('', 'Gasoline prices and diagnostics rose this week.')
    assert inside_a_longer_word.category_id == 'other'
    standalone_word = c.classify('', 'Egypt increased its gas exports this month.')
    assert standalone_word.category_id == 'x'
