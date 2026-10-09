# QC v2.2 — pre-registered evaluation (written before any held-out output exists)

- Code frozen in this commit: `apps/api/translation_v22.py` (sha256 recorded in runtime/qc-v22/frozen.sha256).
- Design set: 219 fields translated by 27B before 2026-10-09 18:58:34 UTC (used to find and fix defects D1–D9).
- Held-out set H: every title/summary field the running worker (v2.1 decisions) finishes AFTER the freeze time
  recorded in runtime/qc-v22/freeze-time.txt, until at least 120 fields. Nobody inspects H before the freeze.
- Labels: every H field accepted by v2.1 OR v2.2 is labelled by AI audit (Claude, NOT a human review) as
  `critical` (wrong entity, number, role, weapon/equipment type, event, negation, relation, date relation or an
  added/removed claim), `minor` (wording, small omission) or `ok`, from source + output only, in a shuffled list
  that does not show which pipeline accepted it.
- Deploy v2.2 only if BOTH:
  (a) acceptance rate on H is higher for v2.2 than for v2.1, and
  (b) critical-error rate among v2.2-accepted <= critical-error rate among v2.1-accepted + 5 percentage points.
- Otherwise keep v2.1 and report. Criteria are not changed after seeing H.
