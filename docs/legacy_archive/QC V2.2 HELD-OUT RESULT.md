# QC v2.2 — held-out result (rule from `QC V2.2 PREREGISTRATION.md`, unchanged)

- Freeze 2026-10-09 19:06:10 UTC (v22 sha256 1ff349d3…, verified identical in the running container).
- H = 120 fields (60 titles, 60 summaries) finished by the worker between freeze and 20:30:31 UTC, taken from the append-only history.
- Labels: AI audit (Claude), **not human review**. 33 fields (union of v2.1- and v2.2-accepted) were labelled from source + output only,
  in a seeded shuffled list without pipeline information, before unblinding. Evidence: `runtime/qc-v22/heldout/` (H.json, blind-list.txt, blind-key.json, labels.json, result.json).

| | accepted / 120 | critical among accepted | minor |
|---|---|---|---|
| v2.1 | 17 (14.2%) | 2 / 17 (11.8%) | 6 |
| v2.2 | 33 (27.5%) | 4 / 33 (12.1%) | 14 |

- (a) acceptance higher: PASS. (b) 12.1% <= 11.8% + 5 pp: PASS. Sensitivity (borderline "by 25%" -> «تا ۲۵ درصد» counted critical): 15.2%, still PASS.
- Decision: **DEPLOY_V2.2** — `LOCAL_TRANSLATION_QC=v2.2` for ai-translator only; `requalify --apply` on 354 stored outputs:
  qc_warning->translated_auto 40, qc_failed->qc_warning 42, qc_failed->translated_auto 15, qc_warning->qc_failed 2 (history rows appended; nothing deleted).
- Critical errors that pass QC (all versions): an added claim («با موفقیت»), a changed concept (acquisition), an equipment type (drone rendered as missile), a dropped quantity ("doubles").
  QC has no semantic coverage: about 1 in 8 accepted translations still has a critical error. That is why the display label «ترجمه خودکار ـ تأیید انسانی نشده» stays, and the English original is always shown.
- Small sample (33 labelled): the difference in critical rates is not statistically meaningful; the rule only bounds degradation.
- This is lab-use only. The earlier official `AUTO_GATE_FAIL` for 27B stands; the owner's acceptance is lab-use authorisation, not proof of quality.
