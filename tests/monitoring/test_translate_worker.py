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


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    """Stands in for a psycopg connection so pending_items()'s SQL-shaping
    and manifest-ordering logic can be tested without a real database. Two
    query shapes are distinguished by a substring already unique to each in
    the real code — brittle only if that SQL text changes, in which case
    this test should be updated alongside it."""

    def __init__(self, item_rows, translated_pairs=()):
        self._item_rows = item_rows
        self._translated_pairs = list(translated_pairs)

    def execute(self, sql, args=None):
        if 'FROM news_item_translations WHERE target_language' in sql:
            return _FakeResult(self._translated_pairs)
        return _FakeResult(self._item_rows)


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


# --------------------------------------------------------------------------- pending_items manifest ordering
def _row(item_id, title='T', summary='S'):
    return (item_id, title, summary, None, 'summary_only', 1)


def test_pending_items_without_manifest_preserves_query_order():
    conn = _FakeConn([_row('a'), _row('b'), _row('c')])
    out = tw.pending_items(conn, limit=10, fields=('title', 'summary'))
    assert [i['item_id'] for i in out] == ['a', 'b', 'c']


def test_pending_items_with_manifest_reorders_to_manifest_order_not_db_order():
    # DB returns them in a different order than the manifest specifies —
    # a deterministic, reviewed selection must win over incidental DB order.
    conn = _FakeConn([_row('c'), _row('a'), _row('b')])
    out = tw.pending_items(conn, limit=10, fields=('title', 'summary'), manifest_item_ids=['a', 'b', 'c'])
    assert [i['item_id'] for i in out] == ['a', 'b', 'c']


def test_pending_items_manifest_limit_matches_manifest_size_not_default():
    conn = _FakeConn([_row('a'), _row('b')])
    out = tw.pending_items(conn, limit=2, fields=('title', 'summary'), manifest_item_ids=['a', 'b'])
    assert len(out) == 2


def test_main_rejects_a_manifest_larger_than_the_pilot_cap(tmp_path, capsys):
    import json as _json
    manifest_path = tmp_path / 'too-big.json'
    manifest_path.write_text(_json.dumps({'items': [{'item_id': str(i)} for i in range(21)]}), encoding='utf-8')
    rc = tw.main(['--manifest', str(manifest_path)])
    assert rc == 2
    out = _json.loads(capsys.readouterr().out)
    assert out['error'] == 'manifest_exceeds_pilot_cap_of_20'
