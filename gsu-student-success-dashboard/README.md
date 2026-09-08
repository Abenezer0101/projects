# GSU Student Success Trends

A time-series dashboard on Georgia State University enrollment and six-year graduation rates, 2010–2024. Built as a deliberate exercise in chart *correctness*, not just chart output.

**[▶ Open the dashboard](https://abenezer0101.github.io/projects/gsu-student-success-dashboard/)**

## The finding

Two separate stories live in this data, and conflating them would be the easy mistake:

**Graduation gaps closed, then inverted.** In 2010 Black students graduated 4.0 points below the overall rate and Pell-eligible students 5.0 points below. By 2024 both sit level with or slightly above it — the overall-vs-Black gap is **−0.5 points**. The overall rate rose 8.0 points (48.0% → 56.0%) *while* the gaps closed, which is the harder achievement: rates usually rise by improving outcomes for students who were already succeeding.

**The 2016 enrollment jump is not growth.** Headcount leaps from 32,000 to 51,100 in a single year — the Georgia Perimeter College consolidation. It is a structural break in the series. Fitting a trend line through it, or citing "64% enrollment growth," would be straightforwardly wrong, so the chart annotates it.

## Chart decisions

The dashboard follows a stated method rather than taste:

- **Two charts, never one.** A percentage and a headcount share no scale. A dual-axis chart would let you slide one series over the other until they appear to correlate — the single most common way charts lie. They are separate figures with separate y-axes.
- **Palette validated, not eyeballed.** The four series use fixed categorical slots, checked with a CVD validator in both modes: worst adjacent colour-blind separation ΔE 9.1 (light) / 8.4 (dark) against a ≥8 target, normal-vision ΔE 22.9 / 19.8 against a ≥15 floor.
- **The contrast warning is answered, not ignored.** Two light-mode steps fall below 3:1 against the surface. That obligates relief, so every series carries a **direct end-label** and both charts have a **table view** — identity never depends on colour alone.
- **Dark mode is selected, not flipped.** It uses its own steps (`#3987e5`, `#d95926`, `#199e70`, `#c98500`) validated against the dark surface.
- **Legend rules follow series count.** Four series get a legend plus direct labels; the single-series enrolment chart gets none — its title names it.
- Thin 2px marks, recessive grid, no point markers until hover, index-mode tooltips.

## Verification

Rendered in headless Chromium at 1100px in both colour schemes:

| Check | Result |
|---|---|
| Series & colours | 4 series; light `#2a78d6/#eb6834/#1baf7a/#eda100`, dark steps swap correctly |
| Axes on rates chart | 2 scales (x + y) — single axis confirmed, no dual-axis |
| Legend logic | on for 4 series, off for the 1-series chart |
| Table view | 15 rows × 5 cols; toggle flips chart↔table both ways |
| Horizontal overflow | none, both themes |
| Page errors | none |

**Not verified:** the Chart.js CDN is blocked by this sandbox's egress policy, so the canvases themselves could not be visually inspected here — the library was stubbed to exercise the surrounding logic. Chart geometry and label placement should be eyeballed once loaded in a normal browser.

## Data

`data/gsu_trends.csv` — 15 rows: year, total enrollment, and six-year graduation rate for overall, Black, Hispanic, and Pell-eligible students.

Figures are **illustrative approximations** of publicly reported Georgia State trends, assembled for a portfolio analysis. They reflect the documented direction and rough magnitude of GSU's student-success results and the 2016 consolidation; they are not official institutional statistics and should not be cited as such.

## Run

Static, no build:

```bash
python3 -m http.server 8000    # then open localhost:8000
```

## Skills

Time-series design, structural breaks, gap analysis, categorical palette validation and CVD safety, accessible chart relief (direct labels + table views), theme-aware visualization, Chart.js.
