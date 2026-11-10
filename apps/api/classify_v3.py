"""Taxonomy v3: primary category, secondary topics, evidence and an explicit
reason code whenever an item lands in "other".

Same philosophy as classify_v2 (deterministic keyword rules, explainable
evidence, no model), with three changes driven by the live corpus:

- title matches weigh twice body matches, so a passing mention deep in a
  summary does not outvote what the headline is about;
- every category that scores at least SECONDARY_MIN becomes a secondary topic
  instead of being discarded;
- "other" always carries a reason code (off-mission, event listing, local
  incident, or no rule matched), so it is never a silent bucket.

v2 stays in the tree unchanged; history of every reclassification is kept by
the database trigger defined in redesign_schema.py.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from classify_v2 import _match_keywords, _normalize

TAXONOMY_PATH = Path(os.getenv('COLLECTOR_METADATA_DIR', '/app/sources')) / 'classification-taxonomy-v3.json'
if not TAXONOMY_PATH.is_file():
    _local = Path(__file__).resolve().parents[2] / 'config' / 'sources' / 'classification-taxonomy-v3.json'
    if _local.is_file():
        TAXONOMY_PATH = _local

SECONDARY_MIN = 2
MAX_SECONDARY = 3
WEAK_MIN = 2


@dataclass
class Result:
    category_id: str
    category_label: str
    confidence: float
    evidence: list = field(default_factory=list)
    secondary: list = field(default_factory=list)   # [{'id','label','score'}]
    subtopics: list = field(default_factory=list)   # [{'id','label','parent'}]
    other_reason_code: 'str | None' = None
    scores: dict = field(default_factory=dict)
    taxonomy_version: str = '3.0.0'
    method: str = ''


def _hits(text_title, text_body, en, fa):
    t = _match_keywords(text_title, en, fa)
    b = [h for h in _match_keywords(text_body, en, fa) if h not in t]
    return t, b


class Classifier:
    def __init__(self, taxonomy=None):
        self.tax = taxonomy or json.loads(TAXONOMY_PATH.read_text(encoding='utf-8-sig'))
        self.version = self.tax['version']
        self.method = self.tax['method']
        self.fallback = self.tax['fallback']
        self.reasons = self.tax.get('other_reason_codes', [])
        self.labels = {c['id']: c['label'] for c in self.tax['categories']}

    def classify(self, title, body):
        tt = ' ' + _normalize(title) + ' '
        bt = ' ' + _normalize(body) + ' '
        scored = []
        for order, cat in enumerate(self.tax['categories']):
            t, b = _hits(tt, bt, cat.get('keywords_en'), cat.get('keywords_fa'))
            subs = []
            for sub in cat.get('subtopics', []) or []:
                st, sb = _hits(tt, bt, sub.get('keywords_en'), sub.get('keywords_fa'))
                if st or sb:
                    subs.append((sub, st, sb))
            sub_t = {h.casefold() for _, st, _ in subs for h in st} - {h.casefold() for h in t}
            sub_b = {h.casefold() for _, _, sb in subs for h in sb} - {h.casefold() for h in b} - sub_t
            title_n = len({h.casefold() for h in t} | sub_t)
            body_n = len({h.casefold() for h in b} | sub_b)
            score = 2 * title_n + body_n
            if score:
                ev = list(dict.fromkeys(t + [h for _, st, _ in subs for h in st] + b + [h for _, _, sb in subs for h in sb]))
                scored.append((score, -order, cat, ev, subs, title_n))
        if not scored:
            return self._other(tt, bt)
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        score, _, cat, ev, subs, title_n = scored[0]
        # Body-only evidence is weak: an off-mission or local-incident
        # headline whose category words appear only deeper in the text (a
        # recipe mentioning "oil", a road crash mentioning "emergency") is
        # not reclassified into that category on the strength of the body.
        if title_n == 0:
            reason = self._title_reason(tt)
            if reason:
                return reason
            if score < WEAK_MIN:
                return Result(self.fallback['id'], self.fallback['label'], 0.0, ev[:8], [], [], 'weak_signal',
                              {}, self.version, self.method)
        runner = scored[1][0] if len(scored) > 1 else 0
        # Evidence volume and the margin over the runner-up both matter: a
        # 3-vs-3 tie is not a confident call however much text matched.
        margin = (score - runner) / score
        confidence = min(0.95, 0.3 + 0.07 * score + 0.2 * margin)
        secondary = [{'id': c['id'], 'label': c['label'], 'score': s}
                     for s, _, c, _, _, _ in scored[1:] if s >= SECONDARY_MIN][:MAX_SECONDARY]
        subtopics = [{'id': s['id'], 'label': s['label'], 'parent': cat['id']} for s, _, _ in subs]
        for s, _, c, _, ss, _ in scored[1:]:
            if s >= SECONDARY_MIN:
                subtopics += [{'id': x['id'], 'label': x['label'], 'parent': c['id']} for x, _, _ in ss]
        return Result(cat['id'], cat['label'], round(confidence, 2), ev[:12], secondary, subtopics, None,
                      {c['id']: s for s, _, c, _, _, _ in scored}, self.version, self.method)

    def _title_reason(self, tt):
        for r in self.reasons:
            if r['id'] in ('off_mission_lifestyle', 'local_incident', 'event_listing'):
                t = _match_keywords(tt, r.get('keywords_en'), r.get('keywords_fa'))
                if t:
                    return Result(self.fallback['id'], self.fallback['label'], 0.0, t[:8], [], [], r['id'],
                                  {}, self.version, self.method)
        return None

    def _other(self, tt, bt):
        for r in self.reasons:
            t, b = _hits(tt, bt, r.get('keywords_en'), r.get('keywords_fa'))
            if t or b:
                return Result(self.fallback['id'], self.fallback['label'], 0.0, (t + b)[:8], [], [], r['id'],
                              {}, self.version, self.method)
        return Result(self.fallback['id'], self.fallback['label'], 0.0, [], [], [], 'no_keyword_match',
                      {}, self.version, self.method)

    def reason_label(self, code):
        return next((r['label'] for r in self.reasons if r['id'] == code), code)


_default = None


def get():
    global _default
    if _default is None:
        _default = Classifier()
    return _default


def classify(title, body):
    return get().classify(title, body)
