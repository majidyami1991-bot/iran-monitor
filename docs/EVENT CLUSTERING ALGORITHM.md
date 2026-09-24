# Deterministic Event Clustering

`apps/api/clustering.py`, algorithm version `1.0.0`. Groups items that
plausibly cover the same real-world event. No embedding model or ML library —
consistent with the rest of this phase's classification, which is keyword-rule
based: explainable, reproducible, and defensible via a stored
`membership_reason`, not a black-box similarity score.

## The core problem

Two articles can share only generic domain words ("IDF", "terror",
"military", "Netanyahu", "reporter") and be about completely different
events, while two articles about the *same* event share a distinctive proper
noun — a person's name, a place, a specific operation. Distinguishing those is
the entire job.

## Pairwise scoring

```
total = 0.5 * entity_score + 0.3 * title_jaccard + 0.1 * time_score + 0.1 * topic_score
```

- **entity_score** — `min(1.0, 0.6 * |shared distinctive tokens|)`. A
  "distinctive token" is a capitalized title word that is not a known generic
  acronym/domain word (`_GENERIC_CAPITALIZED`: articles, common prepositions,
  `idf`, `israel`, `hamas`, `military`, `terror`, `netanyahu`, `reporter`,
  `correspondent`, `spokesman`, `minister`, `president`, …). **Title only,
  deliberately** — see "Real defects found" below.
- **title_jaccard** — Jaccard similarity of non-stopword title words.
- **time_score** — 1.0 within 6h, 0.6 within 24h, 0.3 within 48h, 0.1 beyond
  that up to `MAX_HOURS_APART` (96h); items further apart are never compared
  (`score_pair` returns `None`, not a low score).
- **topic_score** — 1.0 if both items share the same classified category, else
  0.0. Weighted low (0.1) deliberately — see below.

An exact `canonical_url` or `external_guid` match short-circuits to `1.0`
(syndication/duplicate detection, not similarity).

## Clustering

Union-Find over every pair scoring `>= CLUSTER_THRESHOLD` (0.42). Deterministic
because input is sorted by `item_id` before comparison and no randomness is
used anywhere — the same items in any order always produce the same clusters
(tested: `test_clustering_is_deterministic_across_runs`).

## Real defects found running against production data (not synthetic fixtures)

**1. Publisher-boilerplate false clustering.** Entity extraction originally
scanned title + body text. A repeated author byline or site-credit line (e.g.
"Dylan Malyasov", "NewsAviation") that two unrelated articles from the same
outlet both carry was read as a "shared entity," chaining 17 of the pilot's 20
items into one supercluster through Union-Find's transitivity. Root-caused by
inspecting `membership_reason->'shared_entities'` on the live bad cluster.
Fixed by making entity extraction title-only — titles are short,
purpose-written, and essentially boilerplate-free.

**2. Generic-word false clustering.** After fix #1, a 3-member cluster still
chained in an unrelated story: "Channel 12 Reporter Mocks Netanyahu Over
Injured Terror Victim Neriyah Leiter" (correctly matched a follow-up about the
same victim's condition, sharing the surname "Leiter") had *also* matched "Reporter
Slams Netanyahu: He Thinks We're All Idiots" — a same-morning story from a
*different* reporter on a *different* outlet about an unrelated Netanyahu
scheduling remark, sharing only "netanyahu" and "reporter." Root-caused by
pulling the full article text for all three items and reading them. Fixed by
adding both words (and other recurring names/role-words) to
`_GENERIC_CAPITALIZED`.

**3. Category-agreement dependency.** After fixes #1–2, the pilot's one
genuine true positive (the two Leiter articles) scored 0.355 — just below
threshold — in production, even though it passed in the offline calibration
test. Cause: the multi-level classifier (v2) put the two articles in different
categories (`defense_security` vs `foreign_policy` — a legitimate,
independent disagreement between two closely-related but differently-framed
articles), and `topic_score` no longer contributed. The offline test had
hardcoded matching categories, masking this. Fixed by raising the per-entity
weight (0.45 → 0.6) so a single strong distinctive-entity match, combined with
same-day timing, no longer depends on an unrelated system (the classifier)
agreeing. Verified: the pair now scores 0.43 with `same_category: false`.

Each of these has a regression test in `tests/monitoring/test_clustering.py`
reproducing the real (anonymized) failure.

## Idempotency

`event_id = sha256('|'.join(sorted(member_item_ids)))[:24]` — a re-cluster of
unchanged input always produces the same event row (`ON CONFLICT DO UPDATE`,
not a new insert). When a re-cluster changes an item's grouping (e.g. after an
algorithm fix), the item's *old* membership row is deleted for exactly the
item_ids being reprocessed, and — new in this phase — any `news_events` row
left with zero members afterward is pruned in the same transaction. This
closes a real gap found while verifying fix #2 above: the stale 3-member event
row survived with a wrong `member_count` after its members were correctly
reassigned, because nothing had ever deleted the orphaned event row itself.

## Pilot result

1 event identified across the 20-item pilot: the 2 Leiter articles, correctly
distinguishing them from the 18 other unrelated items (including a
Hamas-finance-chief story sharing only "IDF"/"terror" with one of the Leiter
articles, and the unrelated Netanyahu-scheduling story above) —
`FALSE_CLUSTER_COUNT = 0` in the final, verified state.
