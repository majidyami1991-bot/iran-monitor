"""Offline tests for the short/long summary kinds and real idempotency support
added to translate.py. No network access — a fake Provider stands in."""
import translate as t


class FakeProvider(t.Provider):
    name = 'fake'
    model = 'fake-1'

    def __init__(self, output):
        self._output = output

    def complete(self, system, user):
        self._last_system = system
        return self._output


def fa_words(n):
    return ' '.join(['کلمه'] * n)


def test_short_summary_uses_the_short_summary_prompt():
    provider = FakeProvider(fa_words(50))
    result = t.run_task(provider, 'short_summary', 'Some English source text.')
    assert provider._last_system == t.SHORT_SUMMARY_SYSTEM
    assert result['status'] == 'available'


def test_long_summary_uses_the_long_summary_prompt():
    provider = FakeProvider(fa_words(150))
    result = t.run_task(provider, 'long_summary', 'Some English source text.')
    assert provider._last_system == t.LONG_SUMMARY_SYSTEM


def test_short_summary_within_word_budget_is_ok_quality():
    provider = FakeProvider(fa_words(55))
    result = t.run_task(provider, 'short_summary', 'Source text.')
    assert result['quality_status'] == 'ok'


def test_short_summary_wildly_over_budget_is_flagged_suspect():
    provider = FakeProvider(fa_words(300))
    result = t.run_task(provider, 'short_summary', 'Source text.')
    assert result['quality_status'] == 'suspect'


def test_long_summary_far_too_short_is_flagged_suspect():
    provider = FakeProvider(fa_words(10))
    result = t.run_task(provider, 'long_summary', 'Source text.')
    assert result['quality_status'] == 'suspect'


def test_plain_translation_kind_has_no_word_budget_and_is_always_ok():
    provider = FakeProvider(fa_words(5))
    result = t.run_task(provider, 'translation', 'Source text.')
    assert result['quality_status'] == 'ok'


def test_input_hash_is_deterministic_and_content_addressed():
    a = t.input_hash('The quick brown fox')
    b = t.input_hash('The quick brown fox')
    c = t.input_hash('A different sentence')
    assert a == b
    assert a != c


def test_every_result_carries_the_input_hash_even_when_pending_or_unavailable():
    pending = t.run_task(t.NullProvider(), 'short_summary', 'Some text')
    assert pending['input_text_sha256'] == t.input_hash('Some text')
    unavailable = t.run_task(FakeProvider('x'), 'short_summary', '')
    assert unavailable['input_text_sha256'] == t.input_hash('')


def test_unchanged_input_yields_the_same_hash_so_a_caller_can_skip_reprocessing():
    text = 'The Air Force said on 12 March that three units deploy.'
    first = t.run_task(FakeProvider(fa_words(50)), 'short_summary', text)
    second = t.run_task(FakeProvider(fa_words(50)), 'short_summary', text)
    assert first['input_text_sha256'] == second['input_text_sha256']


def test_english_echo_is_still_rejected_for_summary_kinds():
    provider = FakeProvider('The Air Force said on 12 March.')
    result = t.run_task(provider, 'short_summary', 'The Air Force said on 12 March.')
    assert result['status'] == 'error'
    assert result['error'] == 'output_not_persian'
