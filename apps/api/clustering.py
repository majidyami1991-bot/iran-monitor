"""Deterministic event clustering: groups items that plausibly cover the same
real-world event. No embedding model or ML library is used — the taxonomy and
the rest of this project's classification are keyword-rule based, and this
follows the same philosophy: explainable, reproducible, and defensible in a
membership_reason column rather than a black-box score.

The central design problem this solves: two articles can share only generic
domain words ("IDF", "terror", "military") and be about completely different
events, while two articles about the *same* event share a distinctive proper
noun (a person's name, a place, a specific operation). Distinguishing those is
the whole job — see `_distinctive_tokens`.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

ALGORITHM_VERSION = '1.0.0'
CLUSTER_THRESHOLD = 0.42
MAX_HOURS_APART = 96  # items further apart than this are never compared

# Acronyms and generic capitalized domain words common enough that sharing
# them proves nothing about two articles covering the same event.
_GENERIC_CAPITALIZED = frozenset((
    'the', 'a', 'an', 'and', 'or', 'but', 'for', 'with', 'from', 'to', 'in', 'on', 'of', 'at', 'by',
    'is', 'are', 'was', 'were', 'be', 'as', 'it', 'its', 'his', 'her', 'their', 'this', 'that',
    'idf', 'us', 'u.s', 'uk', 'un', 'eu', 'nato', 'ai', 'uav', 'uavs', 'ceo', 'gdp', 'vs',
    'israel', 'israeli', 'iran', 'iranian', 'gaza', 'hamas', 'military', 'terror', 'terrorist',
    'attack', 'war', 'defense', 'defence', 'news', 'report', 'reports', 'says', 'said',
    'new', 'first', 'after', 'over', 'amid', 'as', 'why', 'how', 'what', 'who', 'watch',
))
_STOPWORDS = _GENERIC_CAPITALIZED | frozenset((
    'has', 'have', 'had', 'will', 'would', 'could', 'should', 'not', 'no', 'yes',
))


def _words(text):
    return re.findall(r"[A-Za-z][A-Za-z'-]{1,}", text or '')


def _title_jaccard(a, b):
    wa = {w.casefold() for w in _words(a) if w.casefold() not in _STOPWORDS and len(w) > 2}
    wb = {w.casefold() for w in _words(b) if w.casefold() not in _STOPWORDS and len(w) > 2}
    if not wa or not wb:
        return 0.0, set()
    inter = wa & wb
    union = wa | wb
    return len(inter) / len(union), inter


def _distinctive_tokens(title, body):
    """Proper-noun-shaped words: capitalized, not sentence-initial-only
    common words, not a known generic/domain acronym. A crude but effective
    and fully explainable stand-in for named-entity recognition — no NER
    model is in the offline wheelhouse and one is not justified for this
    pilot's scale."""
    text = (title or '') + ' ' + (body or '')[:2000]
    tokens = set()
    for word in re.findall(r"[A-Z][a-zA-Z'-]{2,}", text):
        low = word.casefold()
        if low in _GENERIC_CAPITALIZED:
            continue
        tokens.add(low)
    return tokens


def _time_proximity(t1, t2):
    if not t1 or not t2:
        return 0.0
    hours = abs((t1 - t2).total_seconds()) / 3600
    if hours > MAX_HOURS_APART:
        return None  # signal "do not compare at all"
    if hours <= 6:
        return 1.0
    if hours <= 24:
        return 0.6
    if hours <= 48:
        return 0.3
    return 0.1


@dataclass
class ItemFeatures:
    item_id: str
    title: str
    text: str  # body or summary, whatever is available
    published_at: 'datetime | None'
    category_id: str | None
    canonical_url: str
    external_guid: str | None = None
    distinctive: set = field(default_factory=set)

    @staticmethod
    def build(item_id, title, text, published_at, category_id, canonical_url, external_guid=None):
        return ItemFeatures(item_id, title or '', text or '', published_at, category_id,
                             canonical_url, external_guid, _distinctive_tokens(title, text))


@dataclass
class PairScore:
    score: float
    reasons: dict


def score_pair(a: ItemFeatures, b: ItemFeatures) -> 'PairScore | None':
    if a.item_id == b.item_id:
        return None
    if a.canonical_url and a.canonical_url == b.canonical_url:
        return PairScore(1.0, {'exact_url_match': True})
    if a.external_guid and a.external_guid == b.external_guid:
        return PairScore(1.0, {'exact_guid_match': True})

    time_score = _time_proximity(a.published_at, b.published_at)
    if time_score is None:
        return None  # too far apart in time to ever be the same event

    jaccard, shared_title_words = _title_jaccard(a.title, b.title)
    shared_entities = a.distinctive & b.distinctive
    entity_score = min(1.0, 0.45 * len(shared_entities))
    topic_score = 1.0 if (a.category_id and a.category_id == b.category_id) else 0.0

    total = 0.5 * entity_score + 0.3 * jaccard + 0.1 * time_score + 0.1 * topic_score
    reasons = {
        'shared_entities': sorted(shared_entities), 'entity_score': round(entity_score, 2),
        'title_jaccard': round(jaccard, 2), 'shared_title_words': sorted(shared_title_words),
        'time_score': round(time_score, 2), 'same_category': bool(topic_score), 'total': round(total, 3),
    }
    return PairScore(round(total, 3), reasons)


class _UnionFind:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def cluster_items(items: list[ItemFeatures], threshold: float = CLUSTER_THRESHOLD):
    """Returns a list of clusters, each `{'members': [item_id, ...],
    'edges': [{'a':, 'b':, 'score':, 'reasons':}]}`. Deterministic: sorted
    input order and no randomness means the same items always produce the
    same clusters. Singletons (no edge above threshold) are omitted — every
    item stays independent by default; only genuine matches form a cluster.
    """
    items = sorted(items, key=lambda x: x.item_id)
    uf = _UnionFind([i.item_id for i in items])
    kept_edges = []
    for idx, a in enumerate(items):
        for b in items[idx + 1:]:
            pair = score_pair(a, b)
            if pair is None or pair.score < threshold:
                continue
            uf.union(a.item_id, b.item_id)
            kept_edges.append({'a': a.item_id, 'b': b.item_id, 'score': pair.score, 'reasons': pair.reasons})

    groups = {}
    for i in items:
        groups.setdefault(uf.find(i.item_id), []).append(i.item_id)

    clusters = []
    for root, members in groups.items():
        if len(members) < 2:
            continue
        member_set = set(members)
        edges = [e for e in kept_edges if e['a'] in member_set and e['b'] in member_set]
        clusters.append({'members': sorted(members), 'edges': edges})
    return clusters
