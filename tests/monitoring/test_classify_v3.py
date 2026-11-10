"""Offline tests for taxonomy v3, using the real shipped taxonomy file.
Cases are real headlines from the corpus reviewed on 2026-09-28."""
import classify_v3 as c3


def test_v2_misclassification_fuel_prices_is_now_economy_or_energy():
    # v2 filed this under security & defence.
    r = c3.classify('Israel Fuel Prices Will Jump 25-40 Agorot Per Liter This Week',
                    'Israeli drivers are bracing for another sharp hike at the pump.')
    assert r.category_id in ('economy_trade_sanctions', 'energy_infrastructure')
    ids = {r.category_id} | {s['id'] for s in r.secondary}
    assert {'economy_trade_sanctions', 'energy_infrastructure'} <= ids


def test_procurement_story_is_defence_industry():
    r = c3.classify('Romania gets its first South Korean K9 howitzers',
                    'Hanwha delivered the first howitzers under the procurement contract.')
    assert r.category_id in ('defense_industry', 'security_defense')
    assert any(s['id'] == 'ground_forces' for s in r.subtopics)


def test_regional_story_carries_iran_axis_subtopic():
    r = c3.classify('Houthi Official Threatens Turkey and Pakistan Over Support for Saudi Arabia', '')
    assert r.category_id == 'regional_geopolitics'
    assert any(s['id'] == 'iran_axis' for s in r.subtopics)


def test_other_always_has_a_reason_code():
    r = c3.classify('10 easy dairy dinner ideas for Sukkos guests', 'Serve with olive oil and fresh bread.')
    assert r.category_id == 'other'
    assert r.other_reason_code == 'off_mission_lifestyle'
    r2 = c3.classify('Zzz qqq', 'Nothing here matches any rule at all.')
    assert r2.category_id == 'other' and r2.other_reason_code == 'no_keyword_match'


def test_body_only_mention_does_not_pull_a_local_incident_into_a_category():
    r = c3.classify('30-Year-Old Killed in Head-On Crash on Route 232',
                    'Emergency services said the driver was killed in the collision near a military base.')
    assert r.category_id == 'other' and r.other_reason_code == 'local_incident'


def test_title_evidence_outweighs_body_evidence():
    r = c3.classify('Knesset election committee disqualifies party',
                    'The military and defence establishment reacted to the vote.')
    assert r.category_id == 'politics_governance'
    assert any(s['id'] == 'security_defense' for s in r.secondary)


def test_confidence_bounded_and_deterministic():
    a = c3.classify('US clears $24B F-35 sale for Saudi Arabia', 'The State Department approved the foreign military sale.')
    b = c3.classify('US clears $24B F-35 sale for Saudi Arabia', 'The State Department approved the foreign military sale.')
    assert a == b
    assert 0 < a.confidence <= 0.95


def test_every_reason_code_has_a_label_and_taxonomy_is_versioned():
    clf = c3.get()
    assert clf.version == '3.0.0'
    for r in clf.reasons:
        assert clf.reason_label(r['id']) and clf.reason_label(r['id']) != r['id']
    ids = [c['id'] for c in clf.tax['categories']]
    subs = [s['id'] for c in clf.tax['categories'] for s in c.get('subtopics', [])]
    assert len(ids) == len(set(ids)) and len(subs) == len(set(subs)) and not set(ids) & set(subs)
