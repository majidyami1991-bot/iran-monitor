"""Read APIs for the news media pipeline v2 (additive; nothing here writes)."""
import os

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

import media_pipeline as mp

DSN = os.environ['DATABASE_URL']
USABLE = "COALESCE(m.validation_status, 'unknown') NOT IN ('rejected', 'blocked', 'unreachable')"


def _rows(sql, args=None):
    with psycopg.connect(DSN, row_factory=dict_row) as c:
        return c.execute(sql, args or {}).fetchall()


def register_media(app):
    @app.get('/api/v1/media/status')
    def status():
        last = _rows("SELECT max(updated_at) AS at FROM news_item_media WHERE policy_version IS NOT NULL")[0]['at']
        return {'policy_version': mp.POLICY_VERSION, 'article_fallback_enabled': mp.fallback_enabled(),
                'validation_mode': 'range_get', 'hotlink_strategy': 'original_url_with_fallback',
                'min_primary': {'width': mp.MIN_W, 'height': mp.MIN_H, 'aspect': [mp.AR_MIN, mp.AR_MAX]},
                'allowed_mime': sorted(mp.ALLOWED_MIME), 'trusted_declarations': sorted(mp.TRUSTED_DECLARATIONS),
                'last_policy_run_at': last}

    @app.get('/api/v1/media/stats')
    def stats():
        totals = _rows(f'''SELECT count(*) AS items,
            count(*) FILTER (WHERE EXISTS (SELECT 1 FROM news_item_media m WHERE m.item_id=n.item_id AND m.kind='image' AND m.is_primary AND {USABLE})) AS with_primary,
            count(*) FILTER (WHERE EXISTS (SELECT 1 FROM news_item_media m WHERE m.item_id=n.item_id AND m.kind='image' AND m.is_primary AND m.validation_status='valid')) AS with_validated_primary
            FROM news_items n''')[0]
        totals['without_primary'] = totals['items'] - totals['with_primary']
        totals['coverage_pct'] = round(100 * totals['with_primary'] / totals['items'], 1) if totals['items'] else None
        by_status = _rows("SELECT COALESCE(validation_status,'unset') AS status, count(*) AS n FROM news_item_media WHERE kind='image' GROUP BY 1 ORDER BY 2 DESC")
        by_reason = _rows("""SELECT COALESCE(policy_rejection_reason,'—') AS reason, count(*) AS n FROM news_item_media
            WHERE kind='image' AND validation_status='rejected' GROUP BY 1 ORDER BY 2 DESC""")
        classes = {'ad': 0, 'logo': 0, 'tracking_pixel': 0, 'icon_or_emoji': 0, 'too_small_or_shape': 0, 'other': 0}
        for r in by_reason:
            reason = r['reason'] or ''
            key = ('ad' if ('banner_ad' in reason or 'ad_or_tracking_host' in reason or 'advert' in reason) else
                   'logo' if 'logo' in reason else 'tracking_pixel' if ('tracking' in reason or 'pixel' in reason or 'spacer' in reason) else
                   'icon_or_emoji' if ('icon' in reason or 'emoji' in reason or 'chrome' in reason) else
                   'too_small_or_shape' if ('small' in reason or 'height' in reason or 'width' in reason or 'aspect' in reason) else 'other')
            classes[key] += r['n']
        by_source = _rows(f'''SELECT s.hostname, count(DISTINCT n.item_id) AS items,
            count(DISTINCT n.item_id) FILTER (WHERE m.is_primary AND {USABLE}) AS with_primary
            FROM news_items n JOIN sources s USING (source_id) LEFT JOIN news_item_media m ON m.item_id=n.item_id AND m.kind='image'
            GROUP BY 1 ORDER BY 1''')
        for r in by_source:
            r['coverage_pct'] = round(100 * r['with_primary'] / r['items'], 1) if r['items'] else None
        by_method = _rows(f"""SELECT COALESCE(source_method,'unset') AS method, count(*) AS n,
            count(*) FILTER (WHERE is_primary AND {USABLE.replace('m.', '')}) AS primary_n
            FROM news_item_media WHERE kind='image' GROUP BY 1 ORDER BY 2 DESC""")
        http = _rows("SELECT http_status, count(*) AS n FROM news_item_media WHERE http_status IS NOT NULL GROUP BY 1 ORDER BY 1")
        return {'totals': totals, 'by_validation_status': by_status, 'rejections_by_class': classes,
                'rejections_by_reason': by_reason[:30], 'by_source': by_source, 'by_method': by_method, 'http_status': http,
                'hotlink_403': sum(r['n'] for r in http if r['http_status'] == 403), 'policy_version': mp.POLICY_VERSION}

    @app.get('/api/v1/news/{item_id}/media')
    def item_media(item_id: str, include_rejected: bool = False):
        if not _rows('SELECT 1 AS x FROM news_items WHERE item_id=%(i)s', {'i': item_id}):
            raise HTTPException(404, 'news_item_not_found')
        cond = '' if include_rejected else f'AND {USABLE}'
        media = _rows(f'''SELECT m.media_id AS id, m.media_type AS type, COALESCE(m.canonical_url, m.url) AS url, m.original_url,
            m.thumbnail_url, COALESCE(m.width, m.verified_width, m.declared_width) AS width,
            COALESCE(m.height, m.verified_height, m.declared_height) AS height, m.mime_type, m.file_size_bytes, m.alt_text,
            m.caption, m.credit, m.source_method, m.source_field, m.source_hostname, m.is_primary, m.validation_status,
            m.policy_rejection_reason AS rejection_reason, m.http_status, m.policy_score, m.policy_version, m.discovered_at, m.validated_at
            FROM news_item_media m WHERE m.item_id=%(i)s AND m.kind='image' {cond}
            ORDER BY m.is_primary DESC, m.policy_score DESC NULLS LAST, m.position NULLS LAST''', {'i': item_id})
        primary = next((m for m in media if m['is_primary']), None)
        return {'item_id': item_id, 'primary_media': primary, 'media': media, 'media_count': len(media),
                'policy_version': mp.POLICY_VERSION}

    return app
