"""Build config/sources/x-free-readiness.json from the project's own source
files — never from memory or guesswork.

Inputs (both derived earlier from the immutable sites.docx):
  config/sources/source-registry.json     one row per unique source
  config/sources/source-occurrences.csv   one row per raw occurrence

Every X account is marked manual-only: no official API, no collector, no
scraping. Run from the repository root:

    python scripts/build_x_free_readiness.py
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'config/sources/source-registry.json'
OCCURRENCES = ROOT / 'config/sources/source-occurrences.csv'
OUT = ROOT / 'config/sources/x-free-readiness.json'
VERSION = '1.0.0'


def build():
    registry = json.loads(REGISTRY.read_text(encoding='utf-8-sig'))
    accounts = [e for e in registry if e.get('source_type') == 'x_account']
    with OCCURRENCES.open(encoding='utf-8-sig', newline='') as f:
        raw = [r for r in csv.DictReader(f) if r['original_column'] == 'x']
    raw_counts = Counter(r['extracted_value'].strip().lower() for r in raw)

    rows = []
    for e in sorted(accounts, key=lambda e: e['original_order']):
        handle = e['x_handle'].strip()
        if not handle.startswith('@') or len(handle) < 2:
            raise SystemExit(f'unexpected handle in registry: {handle!r}')
        rows.append({
            'source_id': e['source_id'],
            'handle': handle,
            'handle_key': e['canonical_key'],
            # x.com/<handle> is the platform's own canonical profile address;
            # derived from the registry handle, not looked up.
            'canonical_profile_url': 'https://x.com/' + handle[1:],
            'enabled': False,
            'collection_mode': 'manual',
            'collection_status': 'manual_monitoring',
            'official_api_enabled': False,
            'occurrence_count': e['occurrence_count'],
            'duplicate_status': e['duplicate_status'],
            'review_status': e.get('review_status') or 'not_reviewed',
            'provenance': e['provenance'],
        })

    duplicates = sorted(r['handle'] for r in rows if r['occurrence_count'] > 1)
    summary = {
        'raw_occurrences': len(raw),
        'unique_accounts': len(rows),
        'duplicate_handles': duplicates,
        'registry_occurrence_total': sum(r['occurrence_count'] for r in rows),
    }
    # The registry and the raw occurrence file must agree, or the manifest
    # would be built on an inconsistent record.
    if summary['raw_occurrences'] != summary['registry_occurrence_total'] or len(raw_counts) != len(rows):
        raise SystemExit(f'registry/occurrence mismatch: {summary}')
    return {
        'version': VERSION,
        'generated_from': ['config/sources/source-registry.json', 'config/sources/source-occurrences.csv'],
        'policy': {
            'official_api': False, 'scraping': False, 'scheduler': False,
            'collection': 'Manual only: an analyst registers the URL of a specific post; nothing is fetched from X.',
        },
        'summary': summary,
        'accounts': rows,
    }


if __name__ == '__main__':
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    json.dump(data['summary'], sys.stdout, ensure_ascii=False)
    print()
