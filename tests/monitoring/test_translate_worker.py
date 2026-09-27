"""Offline tests for translate_worker.py's source-text selection — no
database, no network access.

Regression coverage for a real defect found while preparing the Stage B
translation pilot: `source_text()` for the 'summary' field originally
preferred the extracted article body over the source's own summary field
(`(item['body'] or item['summary'] or '')`), so a call labelled
translated_summary_fa could silently be an AI-composed rewrite of the full
article rather than a faithful translation of original_summary — violating
the project's own rule that translation must never be mixed with
summarization. Fixed to read the source summary only, never the body.
"""
import translate_worker as tw


def _item(body=None, summary=None, title='Some Title'):
    return {'title': title, 'body': body, 'summary': summary}


def test_source_text_title_returns_title():
    assert tw.source_text(_item(title='Hello'), 'title') == 'Hello'


def test_source_text_summary_prefers_the_real_summary_never_the_body():
    item = _item(body='Full extracted article text ' * 50, summary='Real short summary.')
    assert tw.source_text(item, 'summary') == 'Real short summary.'


def test_source_text_summary_is_none_when_source_has_no_summary_even_if_body_exists():
    item = _item(body='Full extracted article text ' * 50, summary=None)
    assert tw.source_text(item, 'summary') is None


def test_source_text_summary_empty_string_treated_as_missing():
    item = _item(body='Full extracted article text', summary='')
    assert tw.source_text(item, 'summary') is None


def test_source_text_body_field_still_uses_body():
    item = _item(body='Full extracted article text', summary='short summary')
    assert tw.source_text(item, 'body') == 'Full extracted article text'
