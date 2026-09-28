# Event and Topic Model

## Topic taxonomy v3.0.0

File: `config/sources/classification-taxonomy-v3.json`. Classifier:
`apps/api/classify_v3.py`. Tests: `tests/monitoring/test_classify_v3.py`.

### Why v3

The live distribution under v2.1.0 on 2026-09-28 was security & defence
54.9%, "other" 23.8%, politics & geopolitics 12.5%, technology 4.4%, strategic
1.7%, economy & infrastructure 1.5%, social 1.2%. A review of the 278 "other"
items found two groups:

- genuinely off-mission items (recipes, celebrity, local crime, holiday
  items), mostly from one general-news source;
- on-mission items that v2 simply had no keywords for (Army procurement,
  Houthis, Knesset elections).

v2 also misfiled some items, for example a fuel-price story under security.

### Categories (fitted to the corpus)

| id | Label | Share on 2026-09-28 |
|---|---|---|
| security_defense | امنیت و دفاع | 54.8% |
| politics_governance | سیاست و حکمرانی | 9.3% |
| regional_geopolitics | منطقه و تحولات ژئوپلیتیکی | 8.9% |
| defense_industry | صنایع دفاعی و تسلیحات | 4.9% |
| aerospace_maritime | حمل‌ونقل، هوافضا و دریایی | 3.4% |
| technology_cyber_ai | فناوری، سایبری و هوش مصنوعی | 2.2% |
| diplomacy_international | دیپلماسی و روابط بین‌الملل | 1.9% |
| society_human_rights | جامعه و حقوق بشر | 1.1% |
| economy_trade_sanctions | اقتصاد، تجارت و تحریم | 0.9% |
| environment_crisis | محیط زیست و بحران | 0.8% |
| energy_infrastructure | انرژی و زیرساخت | 0.5% |
| other | سایر (with reason code) | 11.2% (dry run) → 11.3% (final) |

The brief's suggested list was adapted: defence industry became its own
category because procurement and production dominate the corpus, and
"strategic" was folded into security as a nuclear & deterrence subtopic.
Subtopics carry most of the specificity (air defence, missile, drone, navy,
Iran & axis, Gulf waterways, Russia–Ukraine, procurement…).

### Rules

- Title evidence scores 2; body or summary evidence scores 1. The primary
  category is the highest score, with ties broken by category order.
- Secondary topics are other categories with score ≥ 2 (up to 3). Subtopics
  come from all of these.
- Confidence = `min(0.95, 0.3 + 0.07·score + 0.2·margin)`. It describes the
  evidence; it is not a probability.
- **"Other" always carries a reason code**:
  - `off_mission_lifestyle` (44 items)
  - `local_incident` (36)
  - `event_listing` (8)
  - `weak_signal` (20, meaning body-only evidence below threshold)
  - `no_keyword_match` (23)

  These are dry-run counts on 1,168 items. A title-only reason check runs
  before body-only evidence can pull an off-mission headline into a category.

### Storage, history and override

`item_topic_assignments` is keyed by `(item_id, taxonomy_version)`, so taxonomy
versions coexist and v2 stays in `item_classifications`. The trigger
`log_item_topic_assignment` appends every insert and every material update to
`item_topic_assignment_history` (`assigned`, `reclassified`, or
`human_override`). `PATCH /api/v1/feed/{id}/topic?category_id=&note=` locks the
assignment with a note; locked rows are never reclassified. A new taxonomy
version is applied by bumping `version` in the JSON, which creates new rows
alongside the old ones.

## Event clustering v2.0.0

Module `apps/api/clustering_v2.py`, method `entity_idf_complete_linkage_v2`.
Tests are in `tests/monitoring/test_clustering_v2.py`.

**Why v2.** Run over the full corpus, v1 (tuned on 20 items) put 919 of
1,168 items into one "event": any shared capitalised word counted as an
entity, and single links chained unrelated stories together.

**Rules.**
- Items are compared only when published within 72 h of each other.
- **Distinctive names:** capitalised title words that are not ordinary
  vocabulary, and that appear in ≤ 1% of titles (minimum 4). A word counts as
  vocabulary if it appears in lowercase anywhere in the corpus.
- Adjacent capitalised words are one name ("Tel Aviv"), and possessives are
  normalised.
- **Pair qualifies** when it shares ≥ 2 distinct names, or 1 name plus
  IDF-weighted title overlap ≥ 0.22, and overlap is ≥ 0.1 in every case.
- **Score** = 0.5·names + 0.4·overlap + 0.1·time. The threshold is 0.45.
- **Complete linkage:** two groups merge only if every cross pair qualifies.
  Maximum size 40.
- **Event metadata:** title = earliest member's title; primary category =
  most common member category; confidence = mean pair score, with levels
  high ≥ 0.7 and medium ≥ 0.55.
- Membership reasons (shared names, words, hours apart, score) are stored per
  member and shown on the event page.

**Result on the live corpus (dry run, 2026-09-28):** 29 events, 64 items, 13
multi-source. A manual review judged about 27 of 30 to be the same real-world
event. Known false groupings remain (for example two unrelated Bnei Brak
incidents), and events show a confidence level for exactly this reason.

**Persistence:** event ids are `e2-` + a hash of the sorted members.
Re-running is idempotent. Only v2 memberships that disappear are removed;
the v1 pilot event is untouched.
