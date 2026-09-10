# Population and GDP: does size make a country rich?

A two-scatter dashboard over 54 countries testing whether population predicts wealth. It is the global counterpart to the [US state analysis](../us-population-income-dashboard/) — and it reaches a sharper answer.

**[▶ Open the dashboard](https://abenezer0101.github.io/projects/world-population-gdp/)**

```bash
python3 analyze.py          # correlations, region rollups
```

## The finding

| Relationship | Pearson r (log-log) |
|---|---|
| Population ↔ **total** GDP | **+0.378** |
| Population ↔ GDP **per capita** | **−0.419** |

More people produce more output — that's the positive term, and it's unsurprising. But output *per person* moves the other way: in this sample, larger-population countries are **poorer per head**, not richer.

The spread is the real story. GDP per capita runs from roughly $333 to $103,774 — a **311×** gap between the extremes. Regional averages: Oceania $63,141 and North America $62,410 at the top, Africa $2,353 at the bottom, despite Africa holding 950M of the sample's people.

Both axes are logarithmic. Population spans 5 million to 1.4 billion and GDP spans $14B to $27T; on linear axes every country except China, India and the US collapses into a corner.

## What this does *not* show

The dashboard carries these caveats on the page itself, because a −0.42 is easy to quote and easy to misread:

- **The negative sign is not "large populations cause poverty."** It is produced by which countries occupy the extremes — small wealthy financial and resource economies (Ireland, Switzerland, Norway, Singapore) against large low-income ones (DR Congo, Ethiopia, Afghanistan).
- **Ireland's top rank is a known statistical artifact.** Multinational profit-shifting inflates Irish GDP far past domestic activity — Ireland's own statistics office publishes GNI\* precisely because GDP overstates it. It leads on accounting, not living standards.
- **54 countries is not the world.** The sample skews to large and well-documented economies, so these coefficients describe the sample.

Compare the US-state result: within one country, population and median income are essentially unrelated (r = 0.13). Across countries the relationship is *negative*, but confounded. Same question, two scales, two different answers — which is the point of running it twice.

## Chart decisions

- **One hue for all points, region as a filter.** A scatter compares every point against every other, so a categorical palette must clear the all-pairs colour-blindness test — and past three colours none does. Six regions coloured six ways would fail, so region moved into a filter and the marks stay a single hue. Filtering changes which countries are plotted, never their colour.
- **No legend on either chart** — one series each; the axis titles name it.
- **Two charts, not one.** Total GDP and GDP per capita are different measures; overlaying them on twin axes would invite a correlation that isn't there.

## Verification

The page's JavaScript recomputes the correlations client-side so the region filter can update them live. That risks drifting from the analysis — so both were run over the same 54 rows and compared in headless Chromium, both themes:

| Check | Python | Browser |
|---|---|---|
| r population↔per-capita | −0.419 | −0.419 |
| r population↔total GDP | +0.378 | +0.378 |
| Total population | 6,871M | 6,871M |
| Combined GDP | $95,219B | $95,219B |

Also confirmed: 2 charts, exactly **1** colour in use, no legends, both axes logarithmic, 54 points and 54 table rows, filtering to Africa yields 12 of each, marks keep their hue after filtering, dark mode swaps to its own validated step, no overflow, no page errors.

## Files

| File | Purpose |
|---|---|
| `index.html` | Dashboard — scatters, filter, sortable table |
| `analyze.py` | Reference correlations and region rollups |
| `data/countries.csv` | 54 countries: region, population, nominal GDP |
| `data/countries.js` | Same rows as a script tag, so the page works from `file://` |

Population and GDP figures are illustrative approximations of recent published values, assembled for a portfolio analysis — not an official dataset.

## Skills

Correlation analysis, log-scale reasoning, confounding and selection effects, all-pairs colour constraints in scatter plots, cross-implementation verification, honest caveating.
