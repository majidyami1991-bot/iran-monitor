"""Offline tests for translation_worker_v2 pure helpers (no model, no database)."""
import model_identity as mi
import translation_worker_v2 as w


def test_summary_lead_keeps_whole_sentences():
    s = 'First sentence is here. Second one follows. ' + 'Third sentence is long ' * 40 + '.'
    lead = w.summary_lead(s, 60)
    assert lead == 'First sentence is here. Second one follows.'


def test_summary_lead_short_text_unchanged():
    assert w.summary_lead('  Short text.  ', 600) == 'Short text.'


def test_summary_lead_takes_first_sentence_even_if_long():
    s = ('word ' * 200).strip() + '. Next.'
    lead = w.summary_lead(s, 100)
    assert 50 <= len(lead) <= 150 and not lead.endswith('Next.')


def test_status_mapping_never_shows_rejected_as_translation():
    assert w.STATUS == {'ACCEPT': 'translated_auto', 'REJECT_UNCERTAIN': 'qc_warning', 'REJECT_CRITICAL': 'qc_failed'}


def test_pipeline_version_is_recorded():
    assert w.PV.endswith('+translation-pipeline-v2.1.0')


def test_lab_state_only_servable_in_lab_mode(monkeypatch):
    c = {'approvals': [{'id': 'a', 'tag': 'm:1', 'role': 'translation'}],
         'events': [{'approval': 'a', 'event': 'rejected_quality_gate'}, {'approval': 'a', 'event': 'lab_activated'}]}
    monkeypatch.setenv('LOCAL_AI_LAB_MODE', 'false')
    assert mi.active_approval(c, role='translation') is None
    monkeypatch.setenv('LOCAL_AI_LAB_MODE', 'true')
    assert mi.active_approval(c, role='translation')['id'] == 'a'
    c['events'].append({'approval': 'a', 'event': 'revoked'})
    assert mi.active_approval(c, role='translation') is None
