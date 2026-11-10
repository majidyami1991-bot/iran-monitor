"""Event clustering v2: corpus-aware, chaining-resistant.

Why v2 exists: v1 (clustering.py) was tuned on a 20-item pilot. Run over the
full corpus (1,168 items, 2026-09-28) its union-find merged 919 items into a
single "event", because any capitalised word shared by two titles ("Ukraine",
"Pentagon", "Army") counted as a distinctive entity and single links chained
unrelated stories together. v1 is left untouched for the pilot records; v2 is
a separate, versioned method.

Two changes, both explainable in membership_reason:

1. Distinctiveness is measured against the corpus, not a hand-kept stoplist.
   A title token that appears in more than DF_LIMIT of titles is common
   vocabulary for this corpus and proves nothing about two articles covering
   the same event.
2. Merging is complete-linkage: two groups join only when *every* cross pair
   is itself a qualifying match. A chain A~B~C where A and C share nothing
   stays two events. This trades recall for precision on purpose — a missed
   grouping leaves two honest standalone items; a false grouping asserts a
   relationship that does not exist.

Deterministic: sorted inputs, no randomness, no model.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

ALGORITHM_VERSION = '2.0.0'
METHOD = 'entity_idf_complete_linkage_v2'
MAX_HOURS_APART = 72
DF_LIMIT = 0.01          # share of titles above which a token is "common"
DF_FLOOR = 4             # ...but never treat a token seen <= 4 times as common
MIN_PAIR_SCORE = 0.45
MAX_CLUSTER = 40

_STOP = frozenset('''
the a an and or but for with from to in on of at by is are was were be as it its his her their this that
these those has have had will would could should not no yes new first after over amid why how what who
watch video says said report reports than more most into about up down out off against between during
while under via per just only also still now then there here when where which whose all any some one two
three four five six seven eight nine ten can may might must do does did get gets got make makes made
episode podcast webinar recording conference interview live update updates breaking exclusive
'''.split())


def _norm(title):
    """Curly apostrophes and possessives normalised so "Nasrallah's" and
    "Nasrallah" are the same name."""
    t = (title or '').replace('’', "'")
    return re.sub(r"'s(?![A-Za-z])", '', t)


def _tokens(title):
    """Content words of a title, casefolded, stopwords removed."""
    return {w.casefold() for w in re.findall(r"[A-Za-z][A-Za-z0-9'\-]{2,}", _norm(title))
            if w.casefold() not in _STOP}


def _capitalised(title):
    """Proper-noun-shaped tokens mapped to a run id: adjacent capitalised
    words ("Tel Aviv", "Sami Abu Shehadeh") belong to one run, so one
    multi-word name counts once. The first word is skipped because English
    headlines capitalise it regardless of what it is."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9'\-]*", _norm(title))
    out = {}
    run, prev_cap = 0, False
    for i, w in enumerate(words):
        cap = i > 0 and w[0].isupper()
        if cap and not prev_cap:
            run += 1
        prev_cap = cap
        if cap and len(w) >= 3 and w.casefold() not in _STOP:
            out.setdefault(w.casefold(), run)
    return out


@dataclass
class Item:
    item_id: str
    title: str
    published_at: 'datetime | None'
    source_id: str
    category_id: 'str | None' = None
    text: str = ''
    words: set = field(default_factory=set)
    entities: set = field(default_factory=set)
    runs: dict = field(default_factory=dict)


class Corpus:
    def __init__(self, items):
        self.items = sorted(items, key=lambda x: x.item_id)
        for it in self.items:
            it.words = _tokens(it.title)
            it.runs = _capitalised(it.title)
            it.entities = set(it.runs)
        # A word written in lowercase anywhere in running text (titles or RSS
        # summaries, which are sentence case) is ordinary vocabulary, not a
        # name, however a Title Case headline happens to capitalise it.
        lower_seen = set()
        for it in self.items:
            for m in re.finditer(r"(?<![A-Za-z0-9'\-])([a-z][a-z0-9'\-]{2,})", (it.text or '') + ' ' + (it.title or '')):
                lower_seen.add(m.group(1))
        for it in self.items:
            it.entities = {e for e in it.entities if e not in lower_seen}
        self.lower_seen = lower_seen
        df = Counter()
        for it in self.items:
            df.update(it.words | it.entities)
        n = max(len(self.items), 1)
        self.limit = max(DF_FLOOR, int(math.ceil(DF_LIMIT * n)))
        self.df = df
        self.n = n

    def distinctive(self, it):
        return {t for t in it.entities if self.df[t] <= self.limit}

    def idf(self, token):
        return math.log((self.n + 1) / (self.df[token] + 1)) + 1.0


def _hours(a, b):
    if not a or not b:
        return None
    return abs((a - b).total_seconds()) / 3600


def score_pair(corpus, a, b):
    """Returns (score, reasons) or None when the pair can never qualify."""
    if a.item_id == b.item_id:
        return None
    h = _hours(a.published_at, b.published_at)
    if h is None or h > MAX_HOURS_APART:
        return None
    shared_entities = corpus.distinctive(a) & corpus.distinctive(b)
    if not shared_entities:
        return None
    # A multi-word name is one piece of evidence, not several.
    names = min(len({a.runs[t] for t in shared_entities}), len({b.runs[t] for t in shared_entities}))
    wa, wb = a.words, b.words
    inter = wa & wb
    union = wa | wb
    # IDF-weighted Jaccard: sharing a rare word counts for more than sharing
    # a word every third title uses.
    wj = (sum(corpus.idf(t) for t in inter) / sum(corpus.idf(t) for t in union)) if union else 0.0
    entity_part = min(1.0, names / 2)
    time_part = 1.0 if h <= 24 else 0.5 if h <= 48 else 0.2
    score = 0.5 * entity_part + 0.4 * wj + 0.1 * time_part
    # One shared rare name is not enough on its own; it must come with real
    # word overlap. Two shared rare names are.
    if (names < 2 and wj < 0.22) or wj < 0.1:
        return None
    reasons = {
        'shared_entities': sorted(shared_entities),
        'distinct_names': names,
        'shared_words': sorted(inter),
        'weighted_jaccard': round(wj, 3),
        'hours_apart': round(h, 1),
        'same_source': a.source_id == b.source_id,
        'total': round(score, 3),
        'algorithm': METHOD,
    }
    return round(score, 3), reasons


def cluster(items):
    """[{'members': [...], 'edges': [...]}], clusters of size >= 2 only."""
    corpus = Corpus(items)
    its = corpus.items
    edges = {}
    by_id = {it.item_id: it for it in its}
    for i, a in enumerate(its):
        for b in its[i + 1:]:
            r = score_pair(corpus, a, b)
            if r and r[0] >= MIN_PAIR_SCORE:
                edges[(a.item_id, b.item_id)] = r

    def ok(x, y):
        k = (x, y) if x < y else (y, x)
        return k in edges

    groups = {it.item_id: [it.item_id] for it in its}
    owner = {it.item_id: it.item_id for it in its}
    for (x, y), (score, _) in sorted(edges.items(), key=lambda kv: (-kv[1][0], kv[0])):
        gx, gy = owner[x], owner[y]
        if gx == gy:
            continue
        A, B = groups[gx], groups[gy]
        if len(A) + len(B) > MAX_CLUSTER:
            continue
        if all(ok(p, q) for p in A for q in B):
            A.extend(B)
            for m in B:
                owner[m] = gx
            del groups[gy]

    out = []
    for root, members in groups.items():
        if len(members) < 2:
            continue
        ms = sorted(members)
        es = [{'a': a, 'b': b, 'score': s, 'reasons': r}
              for (a, b), (s, r) in edges.items() if a in ms and b in ms]
        out.append({'members': ms, 'edges': es})
    out.sort(key=lambda c: (-len(c['members']), c['members'][0]))
    return out


def event_title(members):
    """The earliest-published member's title names the event: it is the
    first report, not a later follow-up, and it is real publisher text."""
    ms = sorted(members, key=lambda m: (m.published_at is None,
                                        m.published_at.timestamp() if m.published_at else 0.0, m.item_id))
    return ms[0].title if ms else 'رویداد بدون عنوان'
