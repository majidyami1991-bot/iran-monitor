"""Content Intelligence — the orchestration layer for language detection,
translation, summarization, and key-point extraction. Every generative task
routes through the AI Gateway (ai_gateway.py); no call site here or in any
caller talks to a vendor SDK or endpoint directly.

Persistence (writing to news_item_translations / news_item_translation_history
/ content_key_points) stays in the caller (enrichment_worker.py), matching
this project's existing separation: this module computes and validates a
result, the caller decides how and where to store it.
"""
import ai_gateway as gw
import content_validator as cv

# --------------------------------------------------------------------------- language detection
# Deterministic — a solved problem for the two scripts this product actually
# distinguishes (Persian vs. English), so it never needs a paid AI call, and
# runs identically regardless of AI_PROVIDER / mode.
_PERSIAN_LO, _PERSIAN_HI = '؀', 'ۿ'


def detect_language(text):
    """Returns {'language': 'fa'|'en'|'unknown', 'confidence': 0.0-1.0,
    'method': 'deterministic_unicode_range'}. Never calls the AI Gateway —
    this is real, immediately-usable capability with zero credential
    dependency, not a placeholder for a future AI call."""
    text = text or ''
    persian_chars = sum(1 for ch in text if _PERSIAN_LO <= ch <= _PERSIAN_HI)
    latin_chars = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    total = persian_chars + latin_chars
    if total == 0:
        return {'language': 'unknown', 'confidence': 0.0, 'method': 'deterministic_unicode_range'}
    if persian_chars >= latin_chars:
        return {'language': 'fa', 'confidence': round(persian_chars / total, 3), 'method': 'deterministic_unicode_range'}
    return {'language': 'en', 'confidence': round(latin_chars / total, 3), 'method': 'deterministic_unicode_range'}


# --------------------------------------------------------------------------- generative tasks
def _run_validated(gateway, task_type, text, validator, *, prompt_version=None, validator_kwargs=None):
    """Shared plumbing: call the Gateway, and if it returned real text, run
    content_validator over it too. The Gateway's schema check and the
    validator's fault checks are independent layers — a response can be
    well-formed JSON (Gateway-valid) and still be a bad translation
    (validator-invalid), and both facts are preserved in the result."""
    result = gateway.run(gw.GatewayRequest(task_type, text or '', prompt_version=prompt_version))
    out = {
        'status': result.status, 'text': result.payload.get('text') if result.payload else None,
        'provider': result.provider, 'model': result.model, 'prompt_version': result.prompt_version,
        'content_hash': result.content_hash, 'latency_ms': result.latency_ms,
        'tokens_in': result.tokens_in, 'tokens_out': result.tokens_out,
        'estimated_cost_usd': result.estimated_cost_usd, 'cache_hit': result.cache_hit,
        'error': result.error, 'validation': None,
        'response_model': getattr(result, 'response_model', None),
        'reported_cost_usd': getattr(result, 'reported_cost_usd', None),
    }
    if result.status in ('available', 'cached') and out['text'] is not None:
        validation = validator(text, out['text'], **(validator_kwargs or {}))
        out['validation'] = validation.to_dict()
        # A Gateway-available result that fails independent validation is
        # never silently treated as publishable — the caller must see this
        # in `validation.passed`, not have it hidden behind status=available.
    return out


def translate_to_persian(text, *, gateway):
    """task=translation_en_to_fa (ai_gateway task_type: 'translation')."""
    return _run_validated(gateway, 'translation', text, cv.validate_translation)


def summarize_news(text, *, gateway):
    """task=news_summary: 2-4 sentence Persian summary (ai_gateway task_type:
    'summary', default prompt version)."""
    return _run_validated(gateway, 'summary', text, cv.validate_summary)


def generate_executive_summary(text, *, gateway):
    """task=executive_summary: one-line Persian summary (same task_type and
    schema as news_summary, a distinct prompt version)."""
    return _run_validated(gateway, 'summary', text, cv.validate_summary,
                           prompt_version=gw.EXECUTIVE_SUMMARY_PROMPT_VERSION)


def generate_why_it_matters(text, *, gateway):
    """One short Persian sentence answering "why does this matter?" — same
    task_type/schema as news_summary, a distinct prompt version."""
    return _run_validated(gateway, 'summary', text, cv.validate_summary,
                           prompt_version=gw.WHY_IT_MATTERS_PROMPT_VERSION)


def extract_key_points(text, *, gateway, max_points=5):
    """task=key_point_extraction. Every returned point is independently
    checked against the source text for a real evidence span — a point
    whose evidence doesn't literally appear in `text` is marked invalid
    (and must not be published) even though the Gateway's own schema check
    already passed (it only checks shape, not truthfulness)."""
    result = gateway.run(gw.GatewayRequest('key_point_extraction', text or ''))
    out = {
        'status': result.status, 'points': [], 'provider': result.provider, 'model': result.model,
        'prompt_version': result.prompt_version, 'content_hash': result.content_hash,
        'latency_ms': result.latency_ms, 'tokens_in': result.tokens_in, 'tokens_out': result.tokens_out,
        'estimated_cost_usd': result.estimated_cost_usd, 'cache_hit': result.cache_hit, 'error': result.error,
    }
    if result.status in ('available', 'cached') and result.payload:
        raw_points = (result.payload.get('points') or [])[:max_points]
        for i, point in enumerate(raw_points):
            point_text = point.get('text') if isinstance(point, dict) else None
            evidence = point.get('evidence_span') if isinstance(point, dict) else None
            validation = cv.validate_key_point(point_text, evidence, text)
            out['points'].append({
                'index': i, 'text': point_text, 'evidence_span': evidence,
                'evidence_verified': validation.passed, 'validation': validation.to_dict(),
            })
    return out
