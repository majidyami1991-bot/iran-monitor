# Incident Report — API Key Exposed in Assistant Session Output

**Date**: 2026-09-27. **Severity**: High (real credential exposure).
**Status**: Contained — key revoked and rotated by the project owner;
process and code changes below prevent recurrence. No further action
required from the reader beyond what's already been done.

This report intentionally contains **no fragment, prefix, suffix, length,
hash, or any other derivable characteristic of either the old or the new
key**. Nothing below could be used to reconstruct or narrow down either
value.

## What happened

While wiring OpenRouter configuration into `.env` (Stage B-OR), a
verification command combined `grep -n` (which prefixes each matched line
with a line number, e.g. `43:AI_API_KEY=...`) with a `sed` redaction pattern
anchored to the start of the line (`^AI_API_KEY=`). Because the line no
longer started with `AI_API_KEY=` after `grep -n`'s own prefix was added,
the anchor never matched, the intended redaction silently did nothing, and
the full real key value was printed into the assistant's tool output
(visible in the conversation transcript). A separate, smaller mistake
moments earlier printed a 3-character prefix (`sk-`) of the value while
comparing two candidate secrets by hash — trivial in isolation, but part of
the same pattern of carelessness and disclosed here for completeness.

## Why it happened

Any command whose job is "verify a secret is present/correct without
revealing it" is inherently risky if it constructs output by
string-transforming the secret's own line, because a small formatting
change elsewhere in the pipeline (like `grep -n`'s prefix) can silently
break the redaction step without erroring. The safe pattern is: never let a
line containing the secret enter the output stream at all — check
presence/shape via a value the secret was never derived from (e.g. a
boolean the application computes internally), never via a text
transformation of the secret's own line.

## Impact

The exposed value was visible only in this interactive assistant session's
own output — it was not committed to git (verified: `.env` was gitignored
throughout, `git log -- .env` is empty for all commits), not written to any
application log, not included in any file this project persists in
`runtime/evidence/`, and not part of any test fixture or screenshot. The
project owner treated the exposure as a real compromise regardless (the
correct call for any credential that has left its intended storage,
however briefly) and:

1. Revoked the exposed key at the provider.
2. Generated a new key and placed it directly into the local, gitignored
   `.env` file themselves — the assistant never saw, requested, or handled
   the new key's value in chat.

## Corrective actions taken

1. The local `.env` backup file created immediately before the mistake
   (`.env.backup-before-openrouter-wiring-2026-09-27`) — which held the
   now-revoked key — was deleted without being read.
2. `.env` and every `.env.*` variant were re-confirmed gitignored.
3. This report.
4. New regression tests (`tests/monitoring/test_ai_gateway.py`) asserting
   that no `Authorization` header value, no `AI_API_KEY`-shaped string, and
   no key material of any kind can appear in: a `GatewayResult.error`
   string, anything the `PostgresLogger` would write, or the
   `/api/v1/ai/provider-status` response — see
   `docs/AI GATEWAY.md`'s Security section for the updated guarantee list.
5. Going forward (documented in `docs/AI PROVIDER CONFIGURATION.md` and
   `docs/OPENROUTER PROVIDER ADAPTER.md`): secret presence is checked
   **only** via `GET /api/v1/ai/provider-status`'s `api_key_configured`
   boolean — never via `grep`/`Select-String`/`Get-Content`/`cat`/`type`/
   `env`/`printenv`/`docker inspect`/`docker compose config` against `.env`
   or a running container's environment. If a value's presence must be
   confirmed programmatically, compare only its **byte length**, never any
   substring, prefix, suffix, or hash of it in any output a person or a
   transcript will see.

## What did not happen

- The key was not committed to git at any point.
- The key was not written to any test fixture, screenshot, or file under
  `runtime/`.
- No provider call was made with either the old or the new key before this
  report was written.
