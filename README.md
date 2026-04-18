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
compiler. New categories, new consumers, and new target assets are picked
up automatically and appear in the filter bar and composite scorecard
without any code changes. The compiler will refuse to include an
indicator whose filename does not match its `id`, or which is missing a
required field, or which uses an invalid status or direction value.

## Extending the dashboard

Rendering logic lives entirely in `template.html`. The compiler embeds
the payload between two sentinel comments and does not generate any HTML
of its own. To change how a card looks, edit the `renderIndicator`
function in the template and rerun the compiler. To change the composite
scoring, edit `summarise()` in `compile.py`.

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

## Named regime label

The dashboard renders a named regime label at the top of the page,
derived deterministically from the firing set: the dominant category,
the net direction, the majority confidence, and whether coverage is
complete (no unknowns) or partial. The label is the handle for the
current read, not the forecast itself. For the current seven seeds it
reads "Post-stress recovery — volatility-led, medium conviction,
incomplete coverage".

## Flip criteria

Every indicator may carry an optional `flips_if` field: a one-line,
plain-English inversion of the trigger criterion. The dashboard lists
the `flips_if` line for every firing indicator in a dedicated "What
would flip this" panel directly under the regime label. Missing
`flips_if` entries on firing indicators are surfaced as a footnote
rather than silently skipped, so the gap stays visible.

## Signal age

If an indicator carries `current_state.triggered_on`, the dashboard
renders a "firing for N days" badge on the card, anchored on the
compile timestamp. Useful for distinguishing fresh triggers from
long-running regimes. Leave the field null if the trigger date is not
known or the indicator is off or unknown.

## Horizon-stratified composites

The per-asset scorecard is split into 1m / 3m / 6m horizon panels, each
aggregating only the firing indicators whose primary `horizon` field
matches. The combined all-horizons view is retained as a fallback row
below, so the full-catalogue composite stays one glance away.

## What this library is not

It is not a trading system. It is not a backtester. It does not generate
orders. It is a machine-readable record of what regime indicators exist,
what they say right now, and what caveats apply. Decisions belong
downstream.

## Writing conventions

British and Singapore English. No contractions. Plain prose in free-text
fields. Dates in ISO format (YYYY-MM-DD). Decimal places consistent with
the source (do not invent precision).
