# US State Tile Map

An interactive choropleth of US state population and median household income — built as a **tile grid**, in hand-written inline SVG with no charting library.

**[▶ Open the map](https://abenezer0101.github.io/projects/us-choropleth/)**


## Why a tile grid instead of a real map

On a geographic choropleth, a state's visual weight is its land area. That is almost exactly wrong for population data: Alaska is the largest shape on the map and holds 733,000 people, while New Jersey is nearly invisible and holds 9.3 million. The reader's eye integrates area, so the map argues the opposite of the data.

A tile grid gives every state an equal square and keeps rough geographic position — New England stays top-right, the West Coast stays left, Texas stays bottom-centre. You lose exact shape; you gain an encoding where colour is the only variable carrying meaning. For state-level *rates and counts*, that trade is worth making.

## Design decisions

- **Quantile bins, not equal-width.** Population spans 577K to 39.5M — a **68.5×** range. Equal-width bins would put 48 states in the lightest bucket and California alone in the darkest, which encodes almost nothing. Six quantiles give six equal-count groups, so the colour actually separates states.
- **One hue, light to dark.** Magnitude is sequential, so it takes a single-hue ramp. A rainbow would imply categories that don't exist.
- **A scale legend is mandatory** for sequential encoding and is always present, with the range endpoints labelled.
- **Label ink flips on the dark half of the ramp** so state codes stay readable at both ends — white on the dark steps, near-black on the light ones.
- **Dark mode reverses the ramp** rather than reusing it: against a dark surface, the *light* steps are the high-contrast end, so the ramp runs dark→light to keep "more" reading as "more prominent."
- **Every tile is keyboard-focusable** with an `aria-label` carrying its value, and a sortable table duplicates the whole dataset — colour is never the only channel.

## Findings

| Metric | Highest | Lowest | Ratio |
|---|---|---|---|
| Population | California 39,538,223 | Wyoming 576,851 | **68.5×** |
| Median household income | DC $101,722 | Mississippi $52,719 | **1.93×** |

The two metrics behave completely differently, and switching between them is the point of the toggle. Population is extraordinarily concentrated — a 68× spread, with the top four states holding roughly a third of the country. Income is nearly flat by comparison: under 2× from richest to poorest. The same fifty squares, two entirely different pictures.

This reinforces the [population vs. income finding](../us-population-income-dashboard/) from the same dataset: state size and state wealth are close to unrelated (r = 0.13).

## Verification

Rendered in headless Chromium, both colour schemes:

| Check | Result |
|---|---|
| Tiles drawn | 51 (50 states + DC), no grid collisions |
| Distinct fills in use | 6 — matches the 6 legend swatches |
| Tooltip on hover | fires; California shows 39,538,223 people · $91,905 |
| Metric toggle | switches population → income and redraws |
| Table rows | 51 |
| Horizontal overflow | none |
| Page errors | none, both themes |

The grid layout is asserted at build time — every state must have a cell and no two states may share one, so a typo in the layout fails loudly instead of silently hiding a state.

## Files

| File | Purpose |
|---|---|
| `index.html` | Map, legend, tooltip, table — inline SVG, zero dependencies |
| `data/states.js` | 51 states with population, income, region, grid position |
| `data/us_state_population_income.csv` | Source data, shared with the Day 1 dashboard |

Data: US Census Bureau 2020 Decennial population and ACS median household income — illustrative approximations for a portfolio analysis.

## Skills

Choropleth design, cartogram trade-offs, quantile vs. equal-width classification, sequential colour encoding, hand-written SVG, keyboard accessibility, theme-aware ramp inversion.
