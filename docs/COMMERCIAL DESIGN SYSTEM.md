# Commercial Design System (v2)

The Persian, RTL, dark "editorial intelligence" system used by the redesigned
newsroom. Source of truth: `apps/web-next/app/design/tokens.css` (tokens),
`system.css` (components), `ui.tsx` (primitives), `charts.tsx` (chart kit).

## Principles

1. **Newsroom, not dashboard.** Hierarchy comes from editorial weight: a lead
   story, secondary stories, rows and compact items. There is no wall of
   same-sized KPI cards.
2. **Every value has provenance.** Source, time, rule or model version travel
   with the value. The labels "قاعده‌محور" (rule-based), "ترجمه ماشینی"
   (machine translation) and "تولیدشده با هوش مصنوعی" (AI-generated) are part
   of the system, not decoration.
3. **Absence is explicit.** Empty, not-configured, pending, unavailable and
   error are distinct, labelled states. No placeholder numbers, sample posts
   or stock images.
4. **Restraint.** One brand accent, no glassmorphism, no glow, no decorative
   charts.

## Colour

| Role | Token | Value | Use |
|---|---|---|---|
| Page / raised / panel | `--bg` `--bg-raised` `--panel` `--panel-2/3` | #0a0f15 → #1c2835 | Four surface steps |
| Ink | `--ink` … `--ink-4` | #edf2f7 → #5d7285 | Primary → disabled text |
| Brand | `--brand` | #e3b341 | Logo, active nav, primary action, section markers |
| Urgent | `--urgent` | #ef5a4f | Breaking only |
| Warning / OK / Error | `--warn` `--ok` `--error` | | Health and deltas, always with a label |
| Uncertain | `--uncertain` | #9aa7b4 | Pending, unknown, "other", not configured |
| AI | `--ai` | #a78bfa | Machine translation, AI output |
| Info / rule | `--info` | #4ea1ff | Rule-based derivations, event links |

Category identity hues (`--cat-*`, 12 values) are used **only** for category
artwork and small category markers, never as chart series.

## Chart palette (validated)

The categorical order `#3987e5, #d95926, #199e70, #c98500, #d55181, #008300,
#9085e9, #e66767` was run through the dataviz validator on this surface
(`--mode dark --surface #111820`): **all checks pass**. Worst adjacent CVD
ΔE is 8.4, worst normal-vision ΔE is 19.3, and every colour clears 3:1
contrast. Single-series charts use one hue (`--series-1`). Magnitude uses the
single-hue blue ramp `--seq-100…700`. No chart in the product uses more than
three series.

## Typography

Vazirmatn (local, `public/fonts/Vazirmatn.woff2`, OFL) for Persian UI. English
publisher text (`[dir=ltr]`, `[lang=en]`) uses a Latin system face so Latin
digits stay Latin (Vazirmatn renders them as Persian digits). Scale: 11 / 12 /
13 / 14.5 (base) / 16 / 18 / 22 / 28 / 36 px. Weights: 400, 550, 720, 850.
Persian line-height is 1.75 for body text and 1.4 for headings.

## Space, radius, elevation, motion

- **Space:** a 4 px scale (`--s1`…`--s9`). Gutter is 24 px on desktop, 16 px on phones.
- **Radius:** 4 / 6 / 10 / 14 px. Elevation has three shadows, used for the popover, drawer and story viewer only.
- **Motion:** 120 / 200 / 320 ms with one easing curve. All motion is disabled under `prefers-reduced-motion`, and the ticker then stops auto-advancing.

## Components

| Component | Where | Notes |
|---|---|---|
| Masthead | `Shell.tsx` | Live collection status, search, clock, language, notifications, grouped nav, mobile drawer |
| Tag / CategoryTag / ImportanceTag / TranslationTag / AiTag / RuleTag | `ui.tsx` | Semantic tags; category tags link to `/topics/{id}` |
| NewsCard (lead, standard, row, compact) | `components/NewsCard.tsx` | The same data in four hierarchy levels |
| ItemImage / CategoryArt | `components/Visual.tsx` | Publisher image with credit, or generated category artwork |
| BreakingTicker | `components/BreakingTicker.tsx` | Rule-driven, accessible, no marquee |
| StoriesRail / StoryViewer | `components/Stories.tsx` | Modal dialog, focus trap, progress, keyboard and touch |
| BriefingCard | `components/Briefing.tsx` | Freshness, rule label, AI status |
| EventTimeline / Pulse / ConfidenceTag | `components/EventTimeline.tsx` | Coverage-intensity ticks on the event's own span |
| IntegrationNotice | `ui.tsx` | The one pattern for "data source not connected" |
| Empty / Failure / Bone / CardBones | `ui.tsx` | Empty, error, and skeleton loading states |
| Figure / Columns / Bars / Matrix / ShareBar / Sparkline | `design/charts.tsx` | Title, question, unit, range, source, legend, table view |

## Charts

Each chart states a question, a unit, a time range and a source, and has a
"نمایش جدول داده" table view. Hover tooltips exist on every mark. Time runs
left→right inside the plot (`dir=ltr`) with labelled ends. Grid and axes are
kept recessive. There are no dual axes.

## Patterns borrowed (and adapted) from VibeFarsi

Card, Badge (as Tag), Tabs (as Segmented radio group), Alert (as Failure and
note), Accordion (details and summary), Search, Empty State and Data Table.
Each was reimplemented with this system's tokens; none of the library's code
or styling is used.

## Accessibility baseline

- Skip link, then one `h1` per page and `main`/`nav` landmarks.
- Every button and field has a name.
- Focus is visible (2 px amber).
- Dialogs trap focus and return it to the trigger.
- Radio-group semantics for segmented controls.
- `lang="fa" dir="rtl"` on the document; `dir="ltr"` isolates every English title.
- The automated smoke in `tests/ui/redesign-qa.cjs` checks these on every route.
