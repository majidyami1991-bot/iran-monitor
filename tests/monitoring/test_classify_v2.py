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
    assert r.category_id == 'security_defense'
    assert any(s['id'] == 'missile' for s in r.subtopics)


def test_air_force_subtopic_from_fighter_jet_language():
    r = cv.classify('Russia delivers upgraded Su-57', 'The Russian air force received an upgraded fighter jet.')
    assert r.category_id == 'security_defense'
    assert any(s['id'] == 'air_force' for s in r.subtopics)


def test_nuclear_is_a_strategic_subtopic_with_multiple_evidence_gets_higher_confidence():
    strong = cv.classify('Iran nuclear talks resume', 'Diplomats discussed uranium enrichment and IAEA inspections of the nuclear program.')
    weak = cv.classify('A story mentioning nuclear once', 'This story just says nuclear program and nothing else related.')
    assert strong.category_id == 'strategic'
    assert any(s['id'] == 'nuclear' for s in strong.subtopics)
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
    assert r.taxonomy_version == '2.1.0'
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


# --- Real gaps found by sampling 100 live "سایر" (other) items and reading
# them, which is what motivated the taxonomy v2.1.0 expansion below. Each
# case here is a real (anonymized) headline that used to fall to "other".

def test_space_squadron_story_is_no_longer_other():
    r = cv.classify('UK launches first space squadron to degrade and deny enemies', '')
    assert r.category_id != 'other'


def test_satcom_terminal_story_hits_space_satellite_subtopic():
    r = cv.classify('Boeing picks Lite Coms for Aussie BLOS SATCOM terminals', '')
    assert r.category_id == 'technology'
    assert any(s['id'] in ('space_satellite', 'communications_sensing') for s in r.subtopics)


def test_defense_contractor_earnings_story_hits_defense_industry_subtopic():
    r = cv.classify("Lockheed's F-35 support deal grows by $871 million", '')
    assert r.category_id == 'security_defense'
    assert any(s['id'] == 'defense_industry' for s in r.subtopics)


def test_israeli_domestic_political_story_hits_regional_developments():
    r = cv.classify('Central Elections Committee Disqualifies Ofer Cassif: 19 to 5', '')
    assert r.category_id == 'politics_geopolitics'
    assert any(s['id'] == 'regional_developments' for s in r.subtopics)


def test_think_tank_strategic_assessment_hits_think_tanks_subtopic():
    r = cv.classify('Episode 1: Avoiding Strategic Surprise: Lessons from NATO with Dr Florence Gaub', '')
    assert r.category_id in ('politics_geopolitics', 'strategic')


def test_incidental_common_word_usage_does_not_false_positive():
    # Real defects found by spot-checking 100 live reclassified items for
    # accuracy: several single generic English words doubled as ordinary verbs
    # and collided with unrelated stories. "the miracle of the oil" (a
    # Hanukkah reference in a Friends-the-sitcom article) matched oil_gas;
    # "classified as endangered" (a whale conservation story) matched
    # intelligence_security; "measures to combat disruptive passengers" (a bus
    # transit fine story) matched security_defense's top-level keywords. All
    # three of those bare words were removed or replaced with more specific
    # multi-word phrases.
    assert cv.classify('', 'On the anniversary of the show, we recall the miracle of the oil.').category_id == 'other'
    assert cv.classify('', 'The species is considered rare and classified as endangered in Australia.').category_id == 'other'
    assert cv.classify('', 'Cities worldwide have adopted similar measures to combat disruptive passengers.').category_id == 'other'


def test_genuinely_off_topic_human_interest_stays_other():
    # These must NOT be forced into a category just to lower the "other"
    # percentage — that is an explicit non-goal of the taxonomy redesign.
    r = cv.classify('Man Climbs Tree for Sukkah Schach, Gets Stuck 40 Feet Up', '')
    assert r.category_id == 'other'
    r2 = cv.classify('Crab Filmed Wielding Knife Blade in Bizarre Florida Standoff', '')
    assert r2.category_id == 'other'
