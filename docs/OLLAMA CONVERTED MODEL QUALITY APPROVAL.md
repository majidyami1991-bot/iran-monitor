# Ollama Converted Model — Quality Approval Record

**Decision 2026-10-08: NOT APPROVED** (`rejected_quality_gate`).

The artifact passed every technical, identity and stability check, but failed
the translation quality gate. It must not be used for stored translations or
assistant answers.

## Artifact

The artifact was proposed under option 3: treat Ollama's conversion as a new
model.

| | |
|---|---|
| Immutable tag | `gemma4:e2b-ollama0401-llamacpp-d1e84c607e13`. Created with `/api/copy`; no conversion and no new blobs. Its manifest-list file is byte-identical to the approved tag's (`e4b2053a…`). |
| Ollama | 0.40.1 |
| Runner | `llamacpp` (`lib\ollama\llama-server.exe`, `-c 4096 -np 1`, CPU, `size_vram=0`) |
| Runner manifest | `d1e84c607e134f00608a2d2f5ec8019222adad318851e70e749a62ac2470da2e` |
| Model blob (full SHA-256 of the file the runner loads) | `aed3339236b464c87de08a4ce3aa148f5a43be4717e92629b35e2642199896ff` |
| mmproj blob | `0012c271672236852cb98401c0f9710d71a57c14b552dbe2b31cf898e7bfbf8e` |
| Converted from archive | `d6ee2d62b561cf2f6dc95fd809d916fdba165f43db37bb319fd52964387639e9` |
| Runtime | temperature 0.1, seed 42, num_ctx 4096, num_thread 8, think off; translation ≤ 1536 output tokens, assistant ≤ 512; concurrency 1 |

## Identity guard (versioned contract)

The contract lives in `apps/api/model_approvals.json` (append-only approvals
and events) and is enforced by `apps/api/model_identity.py`. An artifact is
accepted only if all of the following hold:

1. `/api/version` equals the approved version.
2. The tag's `/api/tags` entries are exactly the approved runner manifest
   digests.
3. A host attestation (`scripts/attest_local_model.py`, mounted read-only)
   shows the approved runner process, the full SHA-256 of the model and
   mmproj files it actually loaded, and `size_vram=0`.
4. The runtime parameters equal the approved ones.
5. After every inference, `/api/ps` reports the approved manifest digest,
   on CPU, with no other model loaded.

The cache key includes a fingerprint over weights, runner, version, digests,
parameters and prompt versions. A metadata-only manifest change does not
alter the fingerprint.

The previous approval (`gemma4-e2b-archive-7fbdbf8f5e45`) is kept in the
history as `superseded`.

## Results

| Gate | Result |
|---|---|
| Host attestation, with unload/reload | **PASS**. Version, tag digests, served model, runner, model and mmproj SHA-256, loaded digest, CPU-only and single model all matched; identity was stable after reload. |
| Container pre-flight | **PASS** (version, tag entries, attestation, params; fingerprint `c9355c0b655e…`) |
| Technical | **PASS**: structured JSON; post-inference identity check; timeout enforced; streaming cancellation in 1.25 s with identity intact afterwards; no other model loaded |
| Stability (≈26 sequential inferences) | **PASS**. Latency 1.6–3.7 s (avg 2.1 s) for short fixtures. Total CPU peak 55 %, runner 33 %. Runner RSS 2,912 → 3,044 MB (no growth). One `llama-server`, no crash or reload. 3003 API 25/25 OK (max 105 ms), DB max 208 ms. |
| Simulated invalid outputs (9) | **PASS**: 9/9 rejected (broken JSON, Markdown, commentary, removed number, added number, changed URL, removed mention, untranslated sentence, added information with a number). One was rejected by `not_persian` instead of the expected flag. A purely semantic addition with no number or entity cannot be detected mechanically. |
| Schema validity (23 inference fixtures) | **PASS**: 23/23 |
| Translation quality (23 inference fixtures, validator + human review) | **FAIL**: 15/23 acceptable, 8/23 not |

### The eight failing fixtures

Failures are described here without the full model output; that output is in
`runtime/local-ai-evidence/quality-gate.json`, which is not committed.

| Fixture | Failure |
|---|---|
| person names | First name mangled into mixed Latin/Persian script; a second name rendered partly in **Korean and Hebrew characters** |
| acronyms | OSINT, NATO and CENTCOM were transliterated or translated instead of preserved (the criterion requires preservation) |
| hashtags | **English model commentary** appended after the translation, plus special-token debris (`<channel|>`); hashtags translated |
| emoji | Same commentary and debris pattern; output 4× the source length |
| simple title | Subject ("Navy") and object ("frigate") lost; for an empty summary the model **invented a sentence** (counted as an addition) |
| places | One English word left untranslated and corrupted |
| military term | "brigade" rendered as a word meaning "foundation"; the sentence meaning is broken |
| time | "launch" rendered in the sense of "start-up" instead of a missile launch |

The validator caught 4 of these (names, acronyms, hashtags, emoji). The
other 4 (simple title, places, military term, time) passed the mechanical
validator and were found only by human review.

Acceptable fixtures: multi-sentence summary, quotation, organizations, date,
percent, decimal, coordinates, equipment codes (MQ-9B, F-35A, S-400), URL,
mention, multilingual quote, uncertain claim, attributed claim, negation,
and title + summary with numbers. The Persian-source rule marks the text
not_required without an inference.

## Consequence

- `model_approvals.json` gains the event `rejected_quality_gate`. No
  approval is active, so `/api/v1/assistant/status` shows
  `no_approved_model_artifact`.
- Every translation batch and every assistant query fails closed. Verified
  after redeploy: the batch stops with `configuration`, the assistant saves
  no answer, and there were 0 new `ollama/local` translations or assistant
  inferences.
- No real content was translated or stored. No smoke test, batch or
  assistant run took place.

## What would be needed for a future approval

1. Another reviewed local model (a pull requires an owner decision), or a
   reviewed prompt change. Either one is a new artifact or prompt version
   and needs a new gate run.
2. The validator should additionally flag non-Persian, non-Latin scripts and
   short untranslated English words inside Persian. These are improvements,
   not a substitute for the human review that caught half of the failures.
