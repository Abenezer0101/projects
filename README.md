# Portfolio Projects

Data, analytics, and application builds.

| Project | Stack | What it is |
|---|---|---|
| [US Population & Income Correlations](./us-population-income-dashboard/) | Chart.js, JS | Interactive dashboard on state population vs. median household income — a rebuild of a CIS 2010 Tableau data-visualization project. |
| [Instagram Database System](./instagram-database-system/) | MySQL, UML | 3NF relational schema, seed data, and analytical SQL (self-joins, correlated subqueries, window functions) for a photo-sharing platform. |
| [Library Management Database](./library-management-db/) | MySQL | Members/books/copies/loans schema with overdue detection and availability queries, plus a SQL quick-reference. |
| [E-commerce Analytics Database](./ecommerce-analytics-db/) | MySQL | Customers/products/orders/line-items schema with revenue, AOV, top-product, and refund-rate analytics. |
| [SQL Window-Functions Playground](./sql-window-functions/) | MySQL | Seven worked examples — running totals, ranking, `LAG`, share-of-total, `NTILE`, moving averages. |
| [Excel KPI Analysis](./excel-kpi-analysis/) | Excel, Python | Raw → cleaned → live-formula KPI dashboard on Georgia county population and ZIP codes. |
| [Movie Ratings & Recommendations](./movie-ratings-db/) | MySQL | Collaborative-filtering recommendations in pure SQL from self-joined ratings. |
| [HR & Payroll Database](./hr-payroll-db/) | MySQL | Versioned salary history, layered views, and a transactional stored procedure for raises. |
| [Normalization Case Study](./normalization-case-study/) | SQL, Python | UNF → 1NF → 2NF → 3NF with a runnable script that reproduces each anomaly. |
| [GSU Student Success Trends](./gsu-student-success-dashboard/) | Chart.js, JS | Enrollment and graduation-rate time series with a validated, CVD-safe palette. |
| [Budget Analyzer](./budget-analyzer/) | JS, Python | CSV in, savings-rate KPIs out; JS verified against a Python reference implementation. |
| [Population & GDP](./world-population-gdp/) | Chart.js, Python | Log-log scatters over 54 countries; population predicts total output but not output per person. |
| [Sales Funnel & Conversion](./sales-funnel-dashboard/) | Chart.js, Python | Funnel stages, step conversion, and channel efficiency across six months. |
| [Loan & ROI Model](./loan-roi-model/) | Excel, Python | Live-formula amortization workbook with a prepay-vs-invest comparison. |
| [Bike-Share Data Cleaning](./bikeshare-data-cleaning/) | pandas, matplotlib | Messy trip export cleaned with an auditable pipeline; charts in matplotlib. |
| [US State Tile Map](./us-choropleth/) | SVG, JS | Interactive tile-grid choropleth, hand-written SVG, no dependencies. |
| [PDF Study Kit](./pdf-study-kit/) | Python, FastAPI, Docker | PDF → study material offline: TF-IDF, extractive summarisation, CLI + REST API. |
| [Expense Tracker](./expense-tracker/) | JS | CRUD app with versioned localStorage, budgets, undo, and CSV round-trip. |
| [Weather](./weather-app/) | JS | Open-Meteo forecast app, keyless; 47 offline tests + 17 browser tests. |
| [Markdown Notes](./markdown-notes/) | JS | Markdown renderer written from scratch, XSS-safe by construction; 63 + 19 tests. |
| [Calibration Quiz](./quiz-app/) | JS | Quiz generated from real data; scores confidence with a Brier score. 36 + 18 tests. |
| [Focus Timer](./focus-timer/) | JS | Pomodoro that reads the wall clock, not ticks; a hidden tab costs a naive timer 593s. 50 + 26 tests. |
| [URL Shortener](./url-shortener/) | Flask + SQLite | Real backend: scheme allowlist, UNIQUE-constraint collision retry, click analytics. 44 tests. |
| [Application Tracker](./job-tracker/) | Flask + SQLite | Capstone: CRUD + funnel analytics from an event log. The naive funnel reports 1 interview where 9 happened. 36 tests. |
| [ab-test](./ab-test/) | Python | Peeking daily at an A/A test turns a 5% false-positive rate into 22%, and the false positives report an 18% lift that is not there. |
| [csv-parser](./csv-parser/) | Python | A CSV state machine diffed against the `csv` module over 50,000 generated documents, with the naive split measured beside it. |
| [regex-nfa](./regex-nfa/) | Python | A Thompson NFA regex engine diffed against `re` over 76,744 cases. 12,072x faster where `re` backtracks. |
| [docstring-search](./docstring-search/) | Python | BM25 over 2,077 stdlib docstrings, scored against substring search. With the textbook parameters it loses. |
| [rate-limiter](./rate-limiter/) | Python | Four rate limiters audited against their own promise. Three of the four exceed it; two by 2x. 22 tests. |
| [sqlite-concurrency-lab](./sqlite-concurrency-lab/) | Python + SQLite | Eight writer processes on one file: WAL against rollback journal, with the lock errors counted. |
| [query-planner-lab](./query-planner-lab/) | Python + SQLite | Times five queries with and without an index, and finds the one an index makes 39% slower. 12 MB dataset, deterministic. |
| [assay](./assay/) | Python | A data quality gate that audits its own rules by corrupting data on purpose. 58 tests, zero dependencies. |
| [omnitwin](./omnitwin/) | Python | A digital twin of a small business: price, ad spend and inventory simulated before you commit. 37 tests, zero dependencies. |
| [thicket](./thicket/) | Python | Gradient boosted trees written from scratch and diffed against scikit-learn, plus a demo of how preprocessing before the split fakes accuracy. 26 tests. |
| [Sales Ops Dashboard](./sales-ops-dashboard/) | JS | Sales operations dashboard. |
| [Impossible Gift Machine](./gift-app/) | JS | Gift-picking app. |

Each folder has its own README with methodology, findings, and run instructions.
