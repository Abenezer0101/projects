# Sales Funnel & Conversion Dashboard

Six months of pipeline across four acquisition channels: where prospects are lost, and which channel actually pays.

**[▶ Open the dashboard](https://abenezer0101.github.io/projects/sales-funnel-dashboard/)**

```bash
python3 analyze.py          # funnel totals, step rates, channel breakdown
```

## The funnel

| Stage | Count | Conversion from previous |
|---|---:|---:|
| Visitors | 264,300 | — |
| Leads | 20,066 | 7.59% |
| Qualified | 7,299 | 36.37% |
| Opportunity | 2,825 | 38.70% |
| Closed Won | 822 | 29.10% |

Overall visitor→won: **0.311%**. Revenue $4,520,000 across 822 deals, average deal size **$5,499**.

## The finding

**The biggest drop is at the top, and that is not an insight.** Visitors → Leads converts at 7.59%, far below every later step — but every funnel looks like this, because the top stage is by definition the least qualified population. Reporting it as "the problem" is the beginner's read, and this dashboard says so on the page.

**The real finding is channel mix.**

| Channel | Visitors | Visitor→won | Avg deal | Revenue |
|---|---:|---:|---:|---:|
| Referral | 21,300 | **1.117%** | $6,000 | $1,428,000 |
| Organic | 83,000 | 0.353% | $5,500 | $1,611,500 |
| Paid Search | 124,200 | 0.196% | $4,923 | $1,201,300 |
| Outbound | 35,800 | 0.131% | $5,940 | $279,200 |

Referral converts **5.7× better than Paid Search** and closes the largest deals. Yet it takes **8.1% of traffic while producing 31.6% of revenue**, and Paid Search takes **47.0% of traffic to produce 26.6%**. Spend is pointed at the weaker channel.

The caveat is on the page too: referral volume is rarely elastic to spend the way paid search is, so "shift the budget" is an argument, not a conclusion. A dashboard that hides that is selling something.

## Chart decisions

- **Bars, not a funnel shape.** The classic tapering trapezoid encodes magnitude as *area* while the eye reads *width* — it misrepresents by construction. Ordered horizontal bars carry the same sequence without the distortion.
- **The stage chart uses an ordinal ramp**, not one flat colour and not a rainbow: these are ordered categories, so a single hue running light→dark encodes the sequence. Validated with the ordinal checks in both modes — monotone lightness, adjacent ΔL ≥ 0.06, light end clearing 2:1 against the surface.
- **A log x-axis on the stages.** Visitors to Closed Won spans 264,300 → 822; on a linear axis the last three stages are invisible slivers.
- **Step conversion is a percentage, so it gets its own chart** rather than sharing the count axis.
- **Traffic share vs. revenue share share one axis** — both are percentages of the same whole, which is exactly when a shared scale is honest.

> The first ordinal ramp I tried **failed validation** in both modes: adjacent steps were 0.047 apart in lightness against a 0.06 minimum, so neighbouring stages would have been hard to tell apart. Widening the steps fixed it, and the funnel dropped from six stages to five — a normal funnel shape, and a better one than six near-identical blues.

## Verification

Python reference and browser JavaScript run over the same 24 rows and agree exactly:

| | Python | Browser |
|---|---|---|
| Stage totals | 264,300 / 20,066 / 7,299 / 2,825 / 822 | identical |
| Step rates | 7.59 / 36.37 / 38.70 / 29.10 | identical |
| Visitor→won | 0.311% | 0.311% |
| Average deal | $5,499 | $5,499 |

Also confirmed in headless Chromium, both themes: 3 charts, the ordinal ramp renders its 5 validated steps and swaps correctly for dark mode, no legend on the single-series charts and a legend on the two-series one, 4 channel rows, no overflow, no page errors.

## Files

| File | Purpose |
|---|---|
| `index.html` | Dashboard — funnel, step rates, channel comparison, filter |
| `analyze.py` | Reference implementation |
| `data/funnel.csv` | 24 rows: month × channel × stage counts + revenue |
| `data/funnel.js` | Same rows as a script tag so the page works from `file://` |

Synthetic pipeline data, plausible for a mid-market B2B motion.

## Skills

Funnel analysis, step-conversion vs. end-to-end rates, channel attribution and efficiency, ordinal colour ramps, log scales for wide-range magnitudes, distinguishing structural artifacts from findings.
