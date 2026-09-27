# 35-Day Build Roadmap

A curated, escalating arc of real portfolio projects — SQL/databases → data analysis & visualization → applications → systems, correctness and inference. The daily build job picks the next unchecked day, builds it in its own folder with a README, and checks it off.

Rule: every project must be genuine and self-contained (real dataset or real logic, a README with method + findings, runnable). No filler. If a day's scope is thin, deepen it rather than padding with a throwaway.

## Week 1 — SQL & Databases
- [x] **Day 1** — Instagram DB system + Excel KPI analysis + US population/income dashboard *(done)*
- [x] **Day 2** — Library management DB: schema, seed, checkout/overdue queries + a SQL quick-reference doc *(done)*
- [x] **Day 3** — E-commerce DB: orders/products/customers schema + revenue & AOV analytics queries *(done)*
- [x] **Day 4** — SQL window-functions playground: running totals, rankings, cohort retention on a sample sales set *(done)*
- [x] **Day 5** — Movie ratings DB: schema + "users who liked X also liked" recommendation queries *(done)*
- [x] **Day 6** — HR/payroll DB: tables + views + a stored procedure + headcount/payroll KPIs *(done)*
- [x] **Day 7** — Normalization case study: a denormalized table walked 1NF → 2NF → 3NF with before/after schemas *(done)*

## Week 2 — Data Analysis & Visualization
- [x] **Day 8** — GSU student success dashboard: enrollment & graduation-rate time series *(done)*
- [x] **Day 9** — Personal-finance/budget analyzer: CSV in, category charts + savings-rate KPI out *(done)*
- [x] **Day 10** — World population vs. GDP scatter dashboard (global analogue of Day 1) *(done)*
- [x] **Day 11** — Sales-funnel dashboard with conversion-rate KPIs *(done)*
- [x] **Day 12** — Excel financial model: loan amortization / ROI workbook with live formulas *(done)*
- [x] **Day 13** — Python data-analysis script: clean a messy dataset, output static matplotlib charts + findings *(done)*
- [x] **Day 14** — Interactive US choropleth (population by state), inline SVG + JS *(done)*

## Week 3 — Applications & End-to-End
- [x] **Day 15** — Expense tracker web app (localStorage, charts) *(done)*
- [x] **Day 16** — Weather app (Open-Meteo, keyless; key-handling pattern demonstrated for an optional provider) *(done)*
- [x] **Day 17** — Markdown notes app with live preview *(done)*
- [x] **Day 18** — Data-driven quiz app *(done)*
- [x] **Day 19** — Pomodoro / focus timer with session stats *(done)*
- [x] **Day 20** — URL shortener (Flask + SQLite) — real backend *(done)*
- [x] **Day 21** — Capstone: small full-stack CRUD (Flask + SQLite + dashboard) tying DB + analytics + UI together, plus a portfolio landing page linking every project *(done)*

## Week 4 — Systems, Correctness & Measurement
- [ ] **Day 22** — Query planner lab: run EXPLAIN QUERY PLAN on the Day 3 e-commerce DB, add indexes, and time the same queries before and after. Find and document at least one query the index makes *slower*, and say why.
- [ ] **Day 23** — SQLite under concurrent writers: a script that provokes real lock contention, then compares rollback-journal against WAL mode. Report measured throughput and the error each mode actually raises.
- [ ] **Day 24** — Rate limiter, three ways: fixed window, sliding window, token bucket. Demonstrate the boundary burst a fixed window permits (up to 2x the nominal limit across a window edge) with a test that fails on the naive implementation.
- [ ] **Day 25** — Search from scratch: an inverted index with BM25 ranking over a real text corpus, scored against a `LIKE '%term%'` baseline on hand-labelled relevance. Report precision@10 for both.
- [ ] **Day 26** — A regex engine: Thompson NFA simulation, differentially tested against Python's `re` on generated patterns. Include the input where `re` backtracks catastrophically and the NFA does not, with both timings.
- [ ] **Day 27** — The CSV parser nobody writes: quoted commas, embedded newlines, BOMs, CRLF, ragged rows. Adjudicated against the `csv` module on adversarial generated input, with a table of exactly which cases `line.split(',')` gets wrong.
- [ ] **Day 28** — A/B test calculator that refuses to lie: simulate peeking at results daily and measure how far the false-positive rate climbs above the nominal 5%. Implement a sequential test that holds the rate.

## Week 5 — Inference & Judgement
- [ ] **Day 29** — Forecasting with honest baselines: naive and seasonal-naive against a fitted model, walk-forward on a real series. Report the case where the baseline wins, if it does.
- [ ] **Day 30** — Nearest neighbours on real geography: haversine distance over a city coordinate set, brute force against a k-d tree, with the crossover size where the tree starts paying measured rather than assumed.
- [ ] **Day 31** — Recommender evaluation: a popularity baseline against collaborative filtering, scored under both a random split and a temporal split. Quantify how much the random split inflates the result.
- [ ] **Day 32** — Anomaly detection on a real metric: z-score, MAD, and seasonal decomposition side by side. Show the single outlier that breaks the z-score by inflating its own standard deviation.
- [ ] **Day 33** — Record linkage: dedupe a messy name-and-address set with blocking plus Jaro-Winkler, scored on a hand-labelled truth set. Report precision and recall, and the threshold trade-off between them.
- [ ] **Day 34** — Constrained optimisation: pick a cheapest configuration under integer constraints, with the LP relaxation compared against the exact answer and the gap between them reported.
- [ ] **Day 35** — Capstone II: one CLI that re-derives every number claimed in every README in this repository and exits non-zero if any claim no longer reproduces. A portfolio that checks itself.

_All figures/data in these projects are illustrative for a portfolio unless a source is cited._
