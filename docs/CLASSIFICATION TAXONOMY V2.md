# Classification Taxonomy v2

Additive alongside the original v1 rule-based classifier (`apps/api/ops.py:classify`),
which keeps running unchanged on every RSS-collected item. v2
(`apps/api/classify_v2.py`, taxonomy `config/sources/classification-taxonomy-v2.json`)
adds a confidence score and, for one category, a second classification level
(subtopics). Both are deterministic keyword matching — no embeddings, no ML
model. "Confidence" means how much and how specific the matched evidence was,
not a calibrated probability.

## Categories (taxonomy version 2.0.0)

| id | label | subtopics |
|---|---|---|
| `defense_security` | دفاعی و امنیتی | `missile`, `air_defense`, `drone`, `air`, `naval`, `ground`, `cyber` |
| `foreign_policy` | سیاست خارجی | — |
| `regional_developments` | تحولات منطقه‌ای | — |
| `technology_ai` | فناوری و هوش مصنوعی | — |
| `nuclear` | هسته‌ای | — |
| `sanctions_economy` | تحریم و اقتصاد | — |
| `energy` | انرژی | — |
| `defense_industry` | صنایع دفاعی | — |
| `exercises_operations` | رزمایش و عملیات | — |
| `official_documents` | اسناد و گزارش‌های رسمی | — |
| `other` (fallback) | سایر | — |

Each category and subtopic carries its own `keywords_en` / `keywords_fa` list.
A word longer than 4 characters containing non-ASCII text matches as a
substring; a short ASCII word matches on a word boundary (`\b`) so `"ad"`
never matches inside `"cadre"`.

## Matching rule

```
for each category:
    hits = keywords matched directly against (title + body text)
    subtopic_hits = for each subtopic, keywords matched the same way
    if no hits AND no subtopic_hits: skip this category
    score = distinct(hits) + distinct(all subtopic hit keywords)
pick the category with the highest score; ties keep the first encountered
if nothing matched at all: fallback to "other", confidence 0.0
```

A subtopic match alone is sufficient to select its parent category — this was
a deliberate fix during this phase. "North Korea tests a guided missile" never
says "military" or "defense" in so many words, but it unambiguously belongs
under دفاعی و امنیتی via the `missile` subtopic. The original rule required a
direct parent-category keyword hit even when a subtopic matched, which
silently dropped exactly the specific, high-value matches subtopics exist to
catch — found and fixed by testing 5 real pilot-style headlines and observing
every defense story fall through to "سایر".

## Confidence

```
confidence = min(0.95, 0.35 + 0.15 * distinct_evidence_count)
```

1 matched keyword → 0.50, 2 → 0.65, 3 → 0.80, 4+ → capped at 0.95. Never 1.0 —
keyword matching is never treated as proof of the true topic. The fallback
("other", no evidence) is 0.0, not a small positive number, so a confidence
value can always be trusted at face value rather than needing a separate
"was this even classified" check.

## Rerun persistence and human correction

`item_classifications.human_locked` (set via `PATCH
/api/v1/news/{item_id}/classification`) blocks every future automatic write to
that item's category — both the v2 worker's own re-classification and the
older v1 backfill that runs at API startup. This is checked with a `WHERE
human_locked IS NOT TRUE` clause on every relevant `UPDATE`/`ON CONFLICT DO
UPDATE`, not just at the call site, so it cannot be bypassed by a different
code path later.

**Real defect found and fixed in this phase**: the v1 backfill
(`ops.py:migrate()`, which runs on *every* API container startup, not just on
schema changes) reclassified every single item — including ones already
classified by the newer v2 pipeline — with the old single-label classifier,
unconditionally overwriting `taxonomy_version`, `category_id`, and `topics`
back to v1 values. This was not a hypothetical: two routine container restarts
during this phase actually reverted the pilot's 20-item v2 classification data
back to v1 in the live database, discovered by re-querying `item_classifications`
mid-verification. Fixed by having the backfill skip any item whose
`taxonomy_version` already starts with `'2.'`. Restored the pilot's v2
classification afterward and confirmed it survives a subsequent restart.

## Pilot result

20/20 pilot items classified: 15 `defense_security`, 3 `foreign_policy`, 2
`other`. Average confidence 0.71 (min 0.0, max 0.95).
