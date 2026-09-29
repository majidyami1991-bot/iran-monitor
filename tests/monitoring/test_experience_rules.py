"""Offline tests for the auditable importance / breaking rules and the
migration registry. No database: pure functions only."""
from datetime import datetime, timedelta, timezone

import experience as ex
import redesign_schema as rs


def test_importance_levels():
    assert ex.level(9) == 'high' and ex.level(6) == 'high'
    assert ex.level(5) == 'medium' and ex.level(3) == 'medium'
    assert ex.level(2) == 'low' and ex.level(None) == 'low'


def test_breaking_rule_requires_recency_and_a_reason():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    fresh = now - timedelta(hours=2)
    assert ex.is_breaking({'published_at': fresh, 'importance': 6, 'title': 'x'}, now)
    assert ex.is_breaking({'published_at': fresh, 'importance': 1, 'event_sources': 2, 'title': 'x'}, now)
    assert ex.is_breaking({'published_at': fresh, 'importance': 1, 'title': 'BREAKING: Terror Ramming Attack'}, now)
    assert not ex.is_breaking({'published_at': fresh, 'importance': 2, 'event_sources': 1, 'title': 'x'}, now)
    assert not ex.is_breaking({'published_at': now - timedelta(hours=30), 'importance': 9, 'title': 'x'}, now)
    # A future-dated item (publisher clock error) is not breaking.
    assert not ex.is_breaking({'published_at': now + timedelta(hours=3), 'importance': 9, 'title': 'x'}, now)


def test_card_never_exposes_non_available_translation_text():
    r = ex.card({'title': 'T', 'title_fa_status': 'error', 'title_fa': 'garbage', 'summary_fa_status': None,
                 'summary_fa': None, 'importance': 1, 'published_at': None})
    assert r['title_fa'] is None and r['title_fa_status'] == 'error'
    assert r['summary_fa_status'] == 'pending' and r['machine_translated'] is False


def test_card_hides_translations_that_failed_validation():
    r = ex.card({'title': 'T', 'title_fa_status': 'available', 'title_fa': 'ت', 'title_fa_review': 'needs_review',
                 'summary_fa_status': 'available', 'summary_fa': 'خ', 'summary_fa_review': 'pending_review',
                 'importance': 1, 'published_at': None})
    assert r['title_fa'] is None and r['title_fa_status'] == 'needs_review'
    assert r['summary_fa'] == 'خ' and r['machine_translated'] is True


def test_migrations_are_additive_and_uniquely_versioned():
    versions = [m[0] for m in rs.MIGRATIONS]
    assert versions == sorted(versions) and len(versions) == len(set(versions))
    for _, _, sql in rs.MIGRATIONS:
        upper = sql.upper()
        for forbidden in ('DROP TABLE', 'DROP COLUMN', 'ALTER COLUMN', 'TRUNCATE', 'DELETE FROM', 'RENAME'):
            assert forbidden not in upper, forbidden


def test_integration_registry_never_claims_unbuilt_sources_active():
    active = {i[0] for i in rs.INTEGRATIONS if i[3] == 'active'}
    assert active == {'rss_collector'}
