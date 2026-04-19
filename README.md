# Regime Library

A small, portable catalogue of market-state indicators used to describe the
current regime across volatility, trend, breadth, credit, sentiment,
positioning, liquidity and macro. This library is the observation layer.
Downstream tools such as the Equity Defence Dashboard (EDD) and the Portfolio
Command Centre (PCC) are the response layer. They consume this library; they
do not own the definitions.

## Why this exists

Indicators describe the world. A defence dashboard describes your reaction to
the world. Keeping these separate means a new indicator does not force a
schema change in EDD, and a new portfolio stance does not perturb the
indicator catalogue. It also lets qualitative caveats (for example, "the
quant signal is on, but the recent rally has already pulled forward some
upside") live beside the signal without contaminating the deterministic
rules.

The longer-term ambition is to compile many event-based studies and
aggregate them into meaningful signals for forward returns on key assets.
The schema is therefore designed so that indicators can be grouped by
category, horizon, and target asset, and summed into composite views.

## Layout

```
regime-library/
  README.md             This file.
  schema.yaml           Annotated template describing every field.
  compile.py            Validates YAMLs, computes summary, writes outputs.
  template.html         Dashboard template. Edit this to change the UI.
  indicators/           Source of truth. One YAML per indicator.
    <slug>.yaml         ...
  index.html            Generated. Open in a browser, or let GitHub Pages
                        serve it. Do not edit by hand.
  regime-library.json   Generated. Flattened payload for EDD, PCC, etc.
```

## Viewing the dashboard

```
python regime-library/compile.py
```

This reads every `indicators/*.yaml`, validates them, recomputes the
per-asset composite scores, and regenerates `index.html` and
`regime-library.json`. Open `index.html` directly in a browser; it is
self-contained with the data embedded, so no server or network access is
required.

To add an indicator, drop a new YAML into `indicators/` and rerun the
compiler. New categories, new target assets, and new horizons are
picked up automatically — they appear as new rows on the heatmap, new
rows on the category breadth chart, and new tiles in the digest
without any code changes. The compiler will refuse to include an
indicator whose filename does not match its `id`, or which is missing
a required field, or which uses an invalid status or direction value.

## Extending the dashboard

Rendering logic lives entirely in `template.html`. The compiler embeds
the payload between two sentinel comments and does not generate any
HTML of its own. Each panel is a separate render function in the
script block (`renderRegimeStrip`, `renderHeatmap`, `renderBreadth`,
`renderStatusGrid`, `renderFlipsPanel`, `renderTimeline`,
`renderDigest`). To change how a panel looks, edit the corresponding
function and rerun the compiler. To change the composite scoring of
the summary, edit `summarise()` in `compile.py`.

## How to add an indicator

Copy `schema.yaml` into `indicators/<slug>.yaml`, fill in the fields, and
commit. Keep the slug short and kebab-cased. If you are cribbing from a
research note, put the note title, date and source in the `source` block so
the provenance is recoverable later. Leave `historical_base_rates` as
`null` if you have not verified the numbers; do not paste statistics you
have not sanity-checked.

## How downstream consumers read it

Two patterns. For now, consumers can glob `indicators/*.yaml` directly and
filter by `consumers:` tag (for example, `EDD` or `PCC`). When the library
grows past ten or so, add a small compile step that flattens every YAML
into a single `regime-library.json` which consumers read instead. That
avoids each consumer re-implementing a YAML parser and gives a single point
at which to validate records against the schema.

## The qualitative overlay

Every indicator has a `qualitative_note` field. It is advisory only. It
never silently changes the `current_state.status`. It exists so that a
human caveat (for example, a pattern the quant model cannot see) shows up
next to the signal in any UI that renders it, and is preserved across
sessions. Treat it as a flag, not a gate.

## Dashboard layout

The dashboard is structured as an asset-allocator brief rather than a
terminal: light palette, generous whitespace, editorial typography,
HTML tables rather than dense SVG cells. It reads top-to-bottom from
executive summary to supporting evidence.

Ribbon. A slim light header carrying the as-of date, total indicator
count, firing count, and unknown count.

Executive summary. The hero section. Displays the derived regime
label as a display-size headline (for example "Post-stress
recovery"), a one-line strap describing the dominant category,
firing count, horizon span, conviction and coverage, and three
takeaway cards: directional bias, dominant evidence, and principal
caveat. The caveat text is pulled from the firing indicators'
`qualitative_note.text` fields, preferring any sentence that mentions
pull-forward, V-shaped, false-positive, consolidation, correlation
or rhyming facets.

Conditional forward returns table. Target assets down the rows,
horizons (1m / 3m / 6m / 12m) across the columns. Each cell
aggregates numeric base rates from every firing indicator with
populated `historical_base_rates.returns` at that horizon whose
`target_assets` covers the row, equal-weighted across contributors.
Cell content shows the aggregated return (median where any
contributor supplied a median, else mean), the hit rate, and the
combined sample size. Cell background tints escalate in steps of
0-3% / 3-10% / over 10% for each direction. Where a firing
indicator exists at the cell's horizon but no verified base rate is
populated, the cell falls back to "—" with a "N firing, no verified
base rate" footnote so the gap is explicit. A source-attribution
line below the table identifies which published studies contributed.

Base rates are applied to every asset in the indicator's
`target_assets` list on a read-across assumption for correlated
large-cap indices. The source asset (typically SPX) is noted in the
colophon.

Active signals. One row per firing indicator, sorted by confidence
then name. Columns: signal name with status dot, category chip and
target asset list; trigger date (explicit ISO date plus "N days
ago"); a per-horizon conditional-return breakdown with the primary
horizon marked by a star; and the distilled source claim
(`historical_base_rates.verbal_summary`) attributed to its source.
Indicators without numeric base rates show their qualitative bias
label and a "no verified base rate yet" footnote in the returns
column.

Watch conditions. Two-column table pairing each firing indicator
with its `flips_if` criterion. Rows without a populated criterion
render as italic grey placeholders so the gap is visible.

Trigger timeline. Horizontal SVG timeline anchored by a NOW line on
the right, with a dot per firing indicator at its `triggered_on`
date, the date rendered in bold adjacent to the dot, and the signal
name plus "N days ago" right-aligned to NOW.

Pending and inactive. A compact table listing every indicator whose
status is not firing, with the current-state note truncated to 240
characters. Kept for coverage visibility; the forecast surface
deliberately does not speak about these.

Colophon. Prose caveats about the observation-layer posture and the
read-across assumption, plus the regeneration command.

## What this library is not

It is not a trading system. It is not a backtester. It does not generate
orders. It is a machine-readable record of what regime indicators exist,
what they say right now, and what caveats apply. Decisions belong
downstream.

## Writing conventions

British and Singapore English. No contractions. Plain prose in free-text
fields. Dates in ISO format (YYYY-MM-DD). Decimal places consistent with
the source (do not invent precision).
