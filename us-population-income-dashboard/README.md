# US Population & Income Correlations

Interactive dashboard exploring the relationship between state population and median household income across the 50 US states + DC. A modern rebuild of a *CIS 2010 — Data Analysis & Visualization* project, originally delivered as Tableau dashboards and stories.

**[▶ Open the live dashboard](https://abenezer0101.github.io/tableau-dashboard-project/us-population-income-dashboard/)** *(GitHub Pages)*

## What it shows

- **KPI band** — states in view, total population, population-weighted median income, and the live Pearson correlation (r) between population and income.
- **Scatter (bubble)** — population (log scale) vs. median household income, bubble size = population, colored by region.
- **Top 12 states by median income** — ranked bar.
- **Regional averages** — population-weighted median income by Census region.
- **Sortable detail table** — every state, click any header to sort.
- **Region filter** — one click re-computes every view.

## Key finding

Population and income are **weakly correlated** at the state level. The largest states (California, Texas, Florida) span nearly the full income range, so size does not predict wealth. Income clusters far more tightly by **region** — Northeast and West states dominate the top of the income distribution while the South holds most of the lowest values — which is why the regional view is more explanatory than raw population.

## Method

1. **Collect** — state population (2020 Decennial Census) and median household income (American Community Survey estimates).
2. **Clean & transform** — standardized state names, added region and 2-letter code fields, validated ranges, removed formatting artifacts (Excel workflow in the original; encoded directly here).
3. **Visualize** — correlation scatter, ranked bars, and regional roll-ups with a shared region filter, mirroring a Tableau dashboard/story.

## Data

`data/us_state_population_income.csv` — one row per state: `State, StateCode, Region, Population2020, MedianHouseholdIncome`.

Source: US Census Bureau (2020 Decennial Census + ACS median household income estimates). Figures are illustrative for a portfolio analysis.

## Run locally

Pure static files — no build. Open `index.html`, or:

```bash
python3 -m http.server 8000   # then visit localhost:8000
```

## Stack

Vanilla HTML/CSS/JS + [Chart.js](https://www.chartjs.org/). Skills demonstrated: data cleaning & transformation, correlation analysis, dashboard/story design, KPI reporting.
