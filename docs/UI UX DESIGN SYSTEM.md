# Iran Monitor design system

Single source of design decisions for the redesigned interface. Tokens live in
code at `apps/web-next/app/design/tokens.css`; this document explains the
decisions behind them so they can be extended consistently rather than
rediscovered by reading CSS.

## Principles

- **Restrained, not decorative.** No neon glow, no gradient backgrounds behind
  text, no more than two shadow levels. Color carries meaning (status), not
  mood.
- **One component per concept.** A card, a status pill, a data table, an empty
  state — each has exactly one implementation, used everywhere that concept
  appears. The audit's most severe finding (`C1`, `H3`) was two unrelated
  visual languages for the same "news item" idea; the fix was structural, not
  cosmetic.
- **Never fabricate to look finished.** An empty or pending state is a
  designed state, not a placeholder for missing engineering. See §6.

## Color

Four surface levels (`--surface-0` through `--surface-3`), three border
strengths, four text strengths. Every other color reads from these — no
component defines its own gray.

### Semantic status — six states, no more, no fewer

| Token | Persian label | Meaning | Used for |
| --- | --- | --- | --- |
| `--status-healthy` | سالم | Working as expected | Source/collector health, successful cycles |
| `--status-fresh` | تازه | Reserved for genuine freshness signals | (available; not yet assigned a use — do not repurpose `healthy` for this) |
| `--status-attention` | نیازمند توجه | Degraded but not down | Delayed sources, partial cycles |
| `--status-stopped` | متوقف | Intentionally off | Scheduler disabled |
| `--status-error` | خطادار | Failing | Failed cycles, blocked sources |
| `--status-inactive` | غیرفعال | Never run / not applicable | `not_run` sources, X accounts |

**Rule that fixed a real defect (H6):** amber (`--status-attention`) is never
used for a healthy or neutral state. The pre-redesign analytics page opened
with an amber banner reporting a *healthy* scheduler — semantically wrong and
undermines trust in every other amber the user later sees. `toHealth()` in
`app/design/ui.tsx` is the single mapping from API health strings to these six
tokens; a call site should never invent a color decision inline.

### Accent

One accent color (`--accent-strong`, a restrained teal), used for primary
actions, active navigation state, and chart data series — never for pure
decoration. The pre-redesign palette used the same bright teal for glowing
box-shadows, KPI underlines, and chart lines simultaneously, which is what
reads as "neon." The redesign keeps `--shadow-sm` / `--shadow-md` as the only
elevation, both subtle grays with no color tint.

## Typography

Vazirmatn throughout, loaded via `@font-face` in `globals.css`. English titles
and URLs render `dir="ltr"` inline (`isPersian()` in `format.ts` detects which
direction a given string needs) so mixed Persian/English content — a Persian
label next to an English headline — doesn't reverse.

Scale: `--text-xs` (12px) through `--text-3xl` (38px), eight steps. The
pre-redesign stylesheet had panels as small as 8–9px; the floor here is 12px,
and most body copy sits at 13–14.5px.

## Spacing, radius, elevation

4px-based spacing scale (`--space-1` = 4px … `--space-9` = 56px). Three radii
(`sm` 6px, `md` 10px, `lg` 14px) — cards use `lg`, badges and buttons use `sm`
or `md`, nothing uses an ad hoc value. Two shadow levels only.

## Components

All in `apps/web-next/app/design/` (`ui.tsx`, `components.css`) and
`apps/web-next/app/components/` (news-specific):

| Component | Purpose |
| --- | --- |
| `Shell` | Sidebar + header chrome, used by every page. Collapsible desktop sidebar (state kept in `localStorage`, a per-viewer convenience only), mobile drawer, breadcrumb, search. |
| `StatusPill` | The six-state health indicator. |
| `FieldStatus` | Per-field content status (available/pending/unavailable/error/not_processed), replacing the pre-redesign "field_name: field_value" badge dump. |
| `NewsCard` | **The one news list item component.** Used on the dashboard feed, the news stream, and a source's "latest items." Shows a 2-line clamped excerpt — Persian if translated, English otherwise — never the full extracted body. |
| `NewsDetail` | The full article view: header, lead image with caption/attribution, four tabs (ترجمه فارسی / متن اصلی / تصاویر و اسناد / منشأ و شواهد), never printing the same text twice. |
| `EmptyState` / `ErrorState` / `StaleNotice` / `Skeleton` | The four required non-happy-path states, each with one implementation. |
| `Chip` / `Tabs` / `Badge` / `SourceMark` | Shared small primitives. |

### Why the card fix mattered structurally

The single largest defect found in the audit (`C1`) was that every news card
printed the complete extracted article body, unconditionally, in every list
context — a 30-item news stream rendered at 25,496px on desktop and 42,548px
on mobile. The fix was not a CSS truncation hack; `NewsCard` never receives
the full body at all — it consumes the list API's flattened summary fields,
while `NewsDetail` (a separate component, only ever used on the detail route)
consumes the nested `content.original_text`. The two cannot drift back into
each other because they read different, non-overlapping fields.

## Empty, error and stale states — the honesty rule

Every empty state names *why* the field is empty, using the field's real
status, never a generic "no data":

- `pending` → "در صف پردازش" — something will produce it once configured (e.g.
  translation, once a provider is set).
- `unavailable` → the source itself didn't provide it.
- `not_processed` → the record predates the pipeline that would produce it.
- `error` → an attempt was made and failed; the sanitized reason is shown when
  available.

No component in this system ever fills a gap with placeholder or generated
content to look more finished. This was a standing constraint from the
delivery brief and is enforced structurally: the API returns these four
statuses, and `FieldStatus` / `EmptyState` only ever render what the API says.

## Reference patterns (not copied)

- **ground.news** — dark canvas reserved for content, saturated color reserved
  for meaning (their bias indicator; here, the six health states), not
  decoration. [design.withfudge.com/share/ground.news-design](https://design.withfudge.com/share/ground.news-design)
- **Threat-intelligence dashboard patterns** (Recorded Future / Dataminr
  integration docs, cybersecurity dashboard surveys) — a dedicated pipeline
  status screen (pending/in-progress/complete/failed) separate from
  descriptive analytics. Directly informed building `/monitoring` as its own
  route rather than a section of `/analytics`.
- **VibeFarsi** (`vibefarsi.ir`) — reviewed for Persian-first component
  conventions (RTL spacing, status chip shapes, Persian-numeral handling).
  **Not installed**: its CLI requires Tailwind v4; this project is pinned to
  Tailwind 3.4.17, and the brief explicitly prohibits a major Tailwind upgrade
  without a documented, separately-approved need. Free and open-source per
  its own documentation, so no license blocks future adoption if the Tailwind
  version is deliberately upgraded later.

## Extending this system

- Adding a new page: wrap it in `<Shell title=... breadcrumb=...>`, compose
  from existing `.card`, `.stat-grid`, `.data-table` classes before adding a
  new one.
- Adding a new status concept: it must map to one of the six health tokens.
  If it genuinely doesn't fit any of the six, that is a signal to reconsider
  the status model, not to add a seventh color.
- Never hard-code a hex color, a pixel spacing value, or a font-size outside
  `tokens.css`. If a value is needed twice, it belongs in a token.
