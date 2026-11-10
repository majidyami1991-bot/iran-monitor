# Local Ollama X Translation — QA Report (2026-10-06)

**Status: `READY_NO_REAL_X_POSTS`.** The feature is built, tested and deployed
to the preview (`127.0.0.1:3002`). The main database holds **0 X posts** (36
accounts registered, no post registered yet), so no real post has been
translated and no translation, synthetic or real, has been written to the
main database. Real-model behaviour was measured on labelled synthetic posts
in the throwaway database `defence_monitor_xtrtest`. Production (`:3001`) is
unchanged.

## Baseline

| Item | Value |
|---|---|
| Branch / HEAD before | `feature/news-media-pipeline` @ `7c6c339` |
| X posts / with text / Persian / translatable | 0 / 0 / 0 / 0 |
| Translations before | 0 (no table existed; legacy `x_posts.translated_text_fa` was empty everywhere) |
| Ollama | 0.35.1, listening on `127.0.0.1:11434` only; reachable from containers via `host.docker.internal` (Docker Desktop), no socket mount, host network or privilege |
| Model | `gemma4:e2b`, digest `7fbdbf8f5e45…`, Q4_K_M, 5.1B parameters; the only model installed |
| Hardware | i7-13700K (16 cores / 24 threads), 64 GB RAM, Intel UHD iGPU (unused); `/api/ps` reports `size_vram: 0`, so inference is CPU only |
| Server settings applied | `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1` as user environment variables, server restarted; `OLLAMA_HOST` left unset (127.0.0.1) |

## Offline tests (no database, no external network)

`tests/monitoring/test_x_translation.py`: **48 passed**. The Docker test stage
runs these with the rest of the suite: **407 passed** on the final code.

| # | Case | Covered by |
|---|---|---|
| 1–9 | simple text, URL, mention, hashtag, number/percent, date/time, organisation, military acronym, emoji | `test_good_translations_pass[*]` |
| 10 | Persian source | `test_persian_source_is_not_required`, `test_decide_not_required_only_for_persian_source` |
| 11 | invalid JSON | `test_invalid_json_is_invalid_response` |
| 12 | commentary / label / Markdown | `test_bad_translations_need_review[commentary_label, markdown]` |
| 13 | added number | `…[number_added]` |
| 14 | removed number | `…[number_removed]` |
| 15 | untranslated English | `…[untranslated_english]` |
| 16 | timeout | `test_timeout_is_transient_and_retryable` |
| 17 | Ollama unavailable | `test_ollama_unavailable_stops_batch` |
| 18 | model mismatch (name, digest, served model) | `test_model_missing_or_mismatched_fails_closed`, `test_unapproved_model_never_called` |
| — | URL/mention/hashtag/code/time dropped or added; identical; too short; template debris; invisible characters | `test_bad_translations_need_review[*]` |
| — | adapter refuses non-local hosts; CPU-bounded request body; cost 0; cache hit; free-only guard does not block local | adapter/gateway tests |

## Database integration (throwaway `defence_monitor_xtrtest`, fake model)

`tests/integration/test_x_translation_db.py`: **14 passed**. The test refuses
to run unless the database name ends in `_xtrtest`.

| # | Case | Result |
|---|---|---|
| 19 | duplicate job | second worker gets `worker_already_running`, 0 calls |
| 20 | restart / resume | `limit 1` then a full run; resumes at the first pending row |
| 21 | stuck job recovery | an orphaned `processing` row returns to `pending` and is then translated |
| 22 | DB rollback | `rollback-x-translation.sql` removes only the new objects; `x_posts` count unchanged; re-apply restores them |
| 23 | history append-only | `UPDATE` / `DELETE` on history raise; row count unchanged |
| 24 | source hash changed | row goes `stale`, is re-translated, both outputs stay in history |
| 25 | cache hit | the same text on another post: `cache_hits=1`, `provider_calls=0`; `ai_requests_log` shows `ollama/local`, cost 0 |
| — | migration idempotent; status CHECK; transient error retried once; twice → `failed` (never left `processing`); Ollama down → post back to `pending`, batch stops, originals intact; `--stop-on-review` | pass |

## Real-model smoke test (synthetic posts, test database)

Three posts (short, medium, and one with a mention, URL, numbers, time and
date), concurrency 1, 8 threads, `think=false`.

| Run | Attempted | Available | Needs review | Failed | Avg ms | Max ms |
|---|---|---|---|---|---|---|
| 1 (new) | 3 | 3 | 0 | 0 | 5,466 | 6,535 (includes model load) |
| 2 (all `stale` after a text edit) | 3 | 3 | 0 | 0 | 4,587 | 5,761 |
| 3 (re-run) | 0 | — | — | — | 0 provider calls | — |

Thread benchmark on the same text: 8 threads 7.8 s, 12 threads 7.8 s, 6
threads 8.3 s. Inference is memory-bound, so 8 threads (a third of the
logical cores) was chosen.

During run 2 the peak was 36.5 % total CPU (runner 33.4 %) and 3.2 GB runner
RSS. `/api/ps` reports the model as 6.7 GB, memory-mapped. PostgreSQL
answered a query in 1.3 ms during the run.

### Output quality — reviewed by hand, not only by the validator

| Output | Validator at run time | Current validator | Human review |
|---|---|---|---|
| short, run 1 | pass | pass | accurate |
| medium, run 1 | pass | pass | **grammar error in the second sentence; "overnight" rendered as habitual «شب‌ها»** |
| entities, run 1 | pass | pass | accurate; all numbers, time, MQ-9, @mention, URL and #hashtag preserved |
| short, run 2 | pass | pass | **certainty shift: "were seen leaving" → «خارج شدند» (left)** |
| medium, run 2 | pass | pass | acceptable |
| entities, run 2 | pass | **needs_review** | **output ended in `"} %}` + U+200B**. The validator gained `stray_markup` and `invisible_characters` because of this. |

Result: of 6 real outputs, 3 were fully clean, 1 is now caught automatically,
and 2 have semantic defects that no deterministic check detects. This is why
every `available` translation carries «ترجمه ماشینی محلی» and «بازبینی
انسانی نشده», and why the original text is always one click away. Before a
promotion decision, someone should review a larger sample of real posts by
hand.

## API (preview `:3002`)

| Check | Result |
|---|---|
| Migration `2026.10.06-01` applied at preview startup (additive) | yes; 0 rows |
| `GET /social/translation/status`, `/social/translations/stats`, `/social/posts/{id}/translation` | 200, contract keys present; unknown post → 404 |
| Ollama view from the preview API and the worker container | reachable, model found, digest `7fbdbf8f5e45` |
| Admin write without a token / wrong token / foreign origin / missing CSRF | 403 / 403 / 403 / 403 |
| `run-batch` with token and CSRF while disabled | 409 `x_translation_disabled` |
| Extra body fields (`prompt`, `url`) | 422 `extra_forbidden` |
| `needs_review` text in any API response | never (only `available` text is returned) |
| Legacy on-demand `translate` action (external provider) | closed: 422 `translation_is_local_batch_only` |

## Browser (isolated QA stack `:3004`, synthetic data in every state)

`tests/ui/x-translation-qa.cjs` was run at 1920×1080, 1440×900, 1024×768 and
390×844. Routes: `/social`, an account with posts, an empty account, and post
detail pages for available, needs_review and not_required.

| Run | Result |
|---|---|
| Ollama reachable | **41/41** |
| Ollama offline (QA API pointed at a dead port) | **41/41**; panel shows «مدل محلی خاموش است», posts render with their original text |

In both runs: console errors 0, unexpected failed requests 0, horizontal
overflow 0, translation requests on page load or reload 0, requests to Ollama
or a cloud AI host from the browser 0, external requests 0. Every state text
is shown. RTL translation and LTR original pass; the toggle works both ways;
provenance shows `gemma4:e2b`, local run, time and review state.

A defect found by looking at the screenshots: URLs and mentions inside the
RTL translation were reordered by the bidi algorithm. They are now isolated
as LTR runs (`<bdi dir="ltr">`) and re-verified.

## Not done (by design or blocked)

- No real-post smoke test or batch: there are 0 real X posts.
- No scheduler; nothing runs automatically.
- Production `:3001` is untouched and awaits a separate promotion decision.
  The preview shares the main database, so the two new (empty) tables exist
  there; the production API ignores them.
