"""Multi-level, versioned, confidence-scored classification.

Additive alongside the existing rule-based classify() in ops.py (taxonomy
v1.0.0), which keeps running unchanged on every RSS-collected item. This
module is v2.0.0: adds subtopics under "دفاعی و امنیتی" and a confidence
score. Both are deterministic keyword matching — no embeddings or ML model
was added; "confidence" here means how much and how specific the matched
evidence was, not a calibrated probability.
"""
import json, os, re
from dataclasses import dataclass, field
from pathlib import Path

# Matches ops.py's COLLECTOR_METADATA_DIR convention exactly, including its
# own default of /app/sources for the deployed image.
TAXONOMY_PATH = Path(os.getenv('COLLECTOR_METADATA_DIR', '/app/sources')) / 'classification-taxonomy-v2.json'
if not TAXONOMY_PATH.is_file():
    _local = Path('config/sources/classification-taxonomy-v2.json')
    if _local.is_file():
        TAXONOMY_PATH = _local


def _load_taxonomy(path=None):
    p = path or TAXONOMY_PATH
    return json.loads(p.read_text(encoding='utf-8-sig'))


@dataclass
class ClassificationResult:
    category_id: str
    category_label: str
    subtopics: list = field(default_factory=list)   # [{'id':, 'label':}]
    confidence: float = 0.0
    evidence: list = field(default_factory=list)     # matched keyword strings
    taxonomy_version: str = '2.0.0'
    method: str = ''


def _normalize(text):
    return (text or '').casefold().replace('‌', ' ')


def _match_keywords(text, keywords_en, keywords_fa):
    hits = []
    for word in (keywords_en or []) + (keywords_fa or []):
        needle = word.casefold()
        stripped = needle.strip()
        if not stripped:
            continue
        # Multi-word or non-ASCII phrases match as a substring; short ASCII
        # single words match on a word boundary so "ad" doesn't match "cadre".
        if len(stripped) > 4 and any(ord(ch) > 127 for ch in stripped):
            found = stripped in text
        elif ' ' in stripped:
            found = stripped in text
        else:
            found = re.search(r'(?<![a-z0-9])' + re.escape(stripped) + r'(?![a-z0-9])', text) is not None
        if found:
            hits.append(word.strip())
    return hits


class Classifier:
    def __init__(self, taxonomy=None):
        self.taxonomy = taxonomy or _load_taxonomy()
        self.version = self.taxonomy.get('version', '2.0.0')
        self.method = self.taxonomy.get('method', '')
        self.fallback = self.taxonomy.get('fallback', {'id': 'other', 'label': 'سایر'})

    def classify(self, title, body_text):
        """`body_text` should be whatever real text is available — the
        extracted article body when present, else the RSS summary. Never
        infers from anything not actually in the supplied text."""
        text = ' ' + _normalize((title or '') + ' ' + (body_text or '')) + ' '
        best = None
        for category in self.taxonomy.get('categories', []):
            hits = _match_keywords(text, category.get('keywords_en'), category.get('keywords_fa'))
            subtopic_hits = []
            for sub in category.get('subtopics', []) or []:
                sub_hits = _match_keywords(text, sub.get('keywords_en'), sub.get('keywords_fa'))
                if sub_hits:
                    subtopic_hits.append((sub, sub_hits))
            # A subtopic match is itself evidence for the parent category —
            # "guided missile test" never says "military" or "defense" in so
            # many words, but it unambiguously belongs under دفاعی و امنیتی
            # via its موشکی subtopic. Requiring a *direct* parent-keyword hit
            # in addition would silently drop exactly the specific, high-value
            # matches subtopics exist to catch.
            if not hits and not subtopic_hits:
                continue
            score = len(set(h.casefold() for h in hits)) + sum(len(set(h.casefold() for h in sh)) for _, sh in subtopic_hits)
            if best is None or score > best[0]:
                best = (score, category, hits, subtopic_hits)

        if best is None:
            return ClassificationResult(self.fallback['id'], self.fallback['label'],
                                         confidence=0.0, evidence=[], taxonomy_version=self.version, method=self.method)

        score, category, hits, subtopic_hits = best
        evidence = list(dict.fromkeys(hits + [h for _, sh in subtopic_hits for h in sh]))
        subtopics = [{'id': sub['id'], 'label': sub['label']} for sub, _ in subtopic_hits]
        # Confidence: saturating function of distinct evidence count — 1 hit
        # is a weak signal, 4+ distinct hits is treated as strong. Capped at
        # 0.95 because keyword matching is never proof of the true topic.
        confidence = min(0.95, 0.35 + 0.15 * len(evidence))
        return ClassificationResult(category['id'], category['label'], subtopics=subtopics,
                                     confidence=round(confidence, 2), evidence=evidence,
                                     taxonomy_version=self.version, method=self.method)


_default = None


def get_classifier():
    global _default
    if _default is None:
        _default = Classifier()
    return _default


def classify(title, body_text):
    return get_classifier().classify(title, body_text)
