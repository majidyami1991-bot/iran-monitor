"""Offline tests for scripts/news_sync.py (no Docker, no database)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('news_sync', ROOT / 'scripts' / 'news_sync.py')
ns = importlib.util.module_from_spec(spec)
sys.modules['news_sync'] = ns
spec.loader.exec_module(ns)


def _fake_copy_out(layouts):
    def copy_out(container, query, *, read_only):
        assert read_only, 'guard queries must be read-only'
        rows = layouts[container]
        return 't,cols\n' + ''.join(f'{t},"{c}"\n' for t, c in rows.items())
    return copy_out


def _layout(extra=None):
    base = {t: f'{t}_id:text,payload:jsonb' for t, *_ in ns.TABLES}
    base.update(extra or {})
    return base


def test_schema_guard_passes_on_identical_layouts(monkeypatch):
    monkeypatch.setattr(ns, 'copy_out', _fake_copy_out({ns.PROD: _layout(), ns.LOCAL: _layout()}))
    assert set(ns.schema_guard()) == {t for t, *_ in ns.TABLES}


def test_schema_guard_stops_on_added_column(monkeypatch):
    prod = _layout({'news_items': 'news_items_id:text,payload:jsonb,new_col:text'})
    monkeypatch.setattr(ns, 'copy_out', _fake_copy_out({ns.PROD: prod, ns.LOCAL: _layout()}))
    with pytest.raises(RuntimeError, match='schema guard.*news_items'):
        ns.schema_guard()


def test_schema_guard_stops_on_type_change(monkeypatch):
    prod = _layout({'sources': 'sources_id:text,payload:text'})
    monkeypatch.setattr(ns, 'copy_out', _fake_copy_out({ns.PROD: prod, ns.LOCAL: _layout()}))
    with pytest.raises(RuntimeError, match='sources'):
        ns.schema_guard()


def test_cap_new_keeps_oldest_and_defers_rest(monkeypatch):
    order = ['a', 'b', 'c', 'd']  # Production collected_at order

    def copy_out(container, query, *, read_only):
        assert read_only and container == ns.PROD
        if query.startswith('SELECT item_id FROM news_items'):
            return 'item_id\n' + '\n'.join(order) + '\n'
        return 'k,item_id\n' + ''.join(f'{i}|x,{i}\n' for i in order) + 'old|x,old\n'
    monkeypatch.setattr(ns, 'copy_out', copy_out)
    p = {t: {'new': [], 'changed': [], 'changed_not_applied': [], 'local_only': []} for t, *_ in ns.TABLES}
    p['news_items']['new'] = ['b', 'c', 'd']
    p['news_item_content']['new'] = ['b|x', 'c|x', 'd|x', 'old|x']
    p['news_items']['changed'] = ['z']
    chosen, deferred = ns._cap_new(p, 2)
    assert chosen == {'b', 'c'} and deferred == 1
    assert p['news_items']['new'] == ['b', 'c']
    assert sorted(p['news_item_content']['new']) == ['b|x', 'c|x', 'old|x']   # deferred item's row waits; existing item's row goes in
    assert p['news_items']['changed'] == ['z']                                 # changes are never dropped by the cap


def test_limit_and_max_are_exclusive():
    with pytest.raises(SystemExit):
        sys.argv = ['news_sync.py', 'apply', '--limit-new', '1', '--max-new', '2']
        ns.main()


def test_failed_apply_is_recorded_and_reported(monkeypatch, tmp_path):
    """An apply that fails (here: the 3003 transaction raises) is recorded as 'failed' and exits 1."""
    calls = []
    monkeypatch.setattr(ns, 'RUNS', tmp_path)
    monkeypatch.setattr(ns, 'contract_hash', lambda: 'h')
    monkeypatch.setattr(ns, 'schema_guard', lambda: {})
    monkeypatch.setattr(ns, 'fingerprint', lambda tables: {})
    p = {t: {'new': ['k'] if t == 'news_items' else [], 'changed': [], 'changed_not_applied': [], 'local_only': []} for t, *_ in ns.TABLES}
    monkeypatch.setattr(ns, 'plan', lambda *a, **k: (p, []))
    monkeypatch.setattr(ns, 'pre_images', lambda p: '')
    monkeypatch.setattr(ns, 'build_apply_sql', lambda p, run_id, mode: ('SQL', {'news_items': {'inserted': 1, 'updated': 0}}))

    def psql(container, sql, *, read_only):
        if sql == 'SQL':
            raise RuntimeError('protected Local AI data changed inside the sync transaction — rolled back')
        calls.append((container, read_only, sql))
        return ''
    monkeypatch.setattr(ns, 'psql', psql)
    sys.argv = ['news_sync.py', 'apply', '--max-new', '5']
    with pytest.raises(SystemExit) as e:
        ns.main()
    assert e.value.code == 1
    recorded = [c for c in calls if "'failed'" in c[2]]
    assert len(recorded) == 1 and recorded[0][0] == ns.LOCAL and recorded[0][1] is False   # written to 3003 only, never Production
    run = json.loads(next(tmp_path.glob('*/run.json')).read_text(encoding='utf-8'))
    assert run['status'] == 'failed' and 'rolled back' in run['error']
