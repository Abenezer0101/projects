# SignalForge

**A research and decision workspace that makes its reasoning inspectable.**

SignalForge connects source records to account rankings, exposes conflicting evidence, shows what is still unknown, and lets you test how different priorities change the decision. An optional Python server adds a three-stage AI research workflow with web citations.

## Run it

Requires **Python 3.11+**. No package installation or API key is needed for the workspace.

```bash
cd signalforge
python server.py
```

Open **http://127.0.0.1:8787**. The demo contains six entirely fictional companies and 22 fictional evidence records. Use **Start empty workspace** to begin real work.

The browser workspace also works on static hosting, including GitHub Pages. Serve this folder over HTTP; do not open the HTML with a `file://` URL. The optional research API runs only through `server.py` on your own computer.

## What works

- Account creation and evidence creation, editing, removal, filtering, and source links.
- Rankings derived from evidence, with source quality, recency, adjustable factor weights, and visible missing-data ranges.
- A review queue for opposing positive/negative ratings and incomplete factor coverage.
- An interactive, keyboard-accessible graph connecting accounts to factors supported by evidence.
- Live scenario analysis with normalized weights and immediate ranking changes.
- Timestamped snapshots and score deltas against the most recent snapshot.
- Local browser persistence; validated JSON backup/restore; Markdown decision briefs.
- Responsive layouts, semantic forms, reduced-motion support, and no external frontend scripts or fonts.
- Optional opportunity researcher → skeptic → decision editor pipeline. The first two stages can search the web; the final stage synthesizes their findings. Findings do **not** automatically become scored evidence.

## Try the full loop

1. Open **Atlas Robotics** in the demo. Its timing evidence contains opposing ratings.
2. Read both source records, then inspect the factor breakdown.
3. Save a snapshot from Overview.
4. Open Decision lab and increase Resilience. Rankings recompute immediately.
5. Open Change log to see score changes against the baseline.
6. Export a brief, including evidence and all missing-data disclosures.
7. Export a workspace backup before replacing the demo with your own accounts.

The demo is deliberately not real company research. Its sources are labeled fictional and have no invented source links. Real and fictional evidence should not be mixed: start an empty workspace for real work.

## Optional live research

Configure these environment variables **in the terminal that starts the server**:

```bash
# macOS / Linux — read the key without placing it in shell history
read -s -p 'OpenAI API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
export OPENAI_MODEL='YOUR_WEB_SEARCH_CAPABLE_MODEL'
python server.py
```

PowerShell:

```powershell
$secret = Read-Host 'OpenAI API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
$env:OPENAI_MODEL = 'YOUR_WEB_SEARCH_CAPABLE_MODEL'
python server.py
```

Select a model available to your API project that supports the Responses API `web_search` tool. There is intentionally no hard-coded model assumption. `.env.example` documents the variables; the server does not automatically load dotenv files.

A run makes **three sequential API requests**, with up to three search-tool calls per search stage and up to 2,200 output tokens per stage. Actual billing depends on model and tool usage; these limits are not a dollar cap. The run starts only after the user checks the billing consent box. No workspace evidence is transmitted, only the question and intermediate research. Requests use `store: false`; this is not a guarantee of zero provider retention. API keys remain server-side.

The integration follows the [official OpenAI web-search guide](https://developers.openai.com/api/docs/guides/tools-web-search). Web citation annotations are preserved and displayed as clickable links. Model output is rendered as text, never HTML. Research reports can be exported as JSON, including citations and token usage. Reports remain in memory until the page is closed or reloaded; export them to retain them.

**Validation status:** the core workflow, browser flows and mocked provider integration are tested. A real paid OpenAI run has not been performed in this implementation environment. A model/key combination must be validated in your own account. Search and generated citations do not independently verify a claim.

## The scoring model

Evidence has an analyst-assigned factor, impact from −2 to +2, quality from 1 to 3, source date, source title and optional HTTP(S) URL.

| Factor | Default weight | Positive rating means |
| --- | ---: | --- |
| Fit | 35 | Stronger alignment with the use case |
| Growth | 25 | More favorable growth evidence |
| Timing | 25 | A nearer or clearer buying opportunity |
| Resilience (`risk`) | 15 | Lower risk / stronger resilience |

For each account and factor:

1. Group evidence by normalized URL without its fragment, or by source title when no URL exists. This reduces exact duplicate-source inflation; it does not identify syndicated articles or prove source independence.
2. Average impact ratings inside each source group.
3. Weight each source by `quality × 0.5^(age_in_days / 180)`. For a group, use the greatest evidence weight in that group.
4. Convert the weighted impact to a factor score: `50 + 25 × impact`.
5. Normalize your factor weights, then calculate the weighted composite.

Missing factors contribute a neutral placeholder of 50. **Coverage** is the percentage of factor weight with any evidence, not a probability or measure of factual accuracy. The displayed score range replaces missing factors with 0 and 100; it is **not** a statistical confidence interval. Recency changes the relative influence of sources, not a standalone confidence score.

Below 75% coverage, the next step is Research. With sufficient coverage, opposing signs within a factor trigger Review. Otherwise, scores ≥70 are Prioritize, ≥45 Watch, and lower scores Deprioritize. These are editable-code heuristics, not scientific conclusions. Opposing signs are a review flag, not semantic proof that two statements contradict one another.

Snapshot deltas include evidence edits, weight changes, and relative source aging. Snapshots preserve score and coverage, not full historical evidence. Export backups to retain complete historical workspaces.

## Data, privacy and limits

- Stored in this browser's localStorage. No accounts, cloud sync, or encryption. Do not use a shared browser profile for confidential data. Export backups regularly.
- Workspaces are separated by origin. A localhost workspace and GitHub Pages workspace do not automatically sync; use export/import.
- Up to 100 accounts, 2,000 evidence records, 50 snapshots, and a 4 MB import file. The graph shows the 24 highest-ranked accounts to remain readable. Browser storage quotas can be lower; save failures are surfaced.
- The research server binds only to loopback, validates Host and Origin, requires a session token for research, and allows one investigation at a time. Only a fixed asset list is served; source files and environment files are not exposed by that server.
- The static portfolio deployment publishes repository files. Never place real secrets in this repository or in browser code.
- Not a production multi-user server. Remote deployment would require authentication, tenancy, durable storage, request budgets, and an audited hosting setup.
- Change tracking is manual, driven by snapshots. There is no unattended monitoring, scheduled crawling, semantic contradiction detector, PowerPoint generation, or email delivery in this version.

## Tests

Core and backend tests have no third-party dependencies:

```bash
node --test tests/core.test.mjs
python -m unittest discover -s tests -p 'test_*.py'
```

For browser verification, install Playwright in a disposable environment and leave `python server.py` running:

```bash
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node tests/browser.mjs
```

Browser tests cover evidence CRUD, escaped user text, persistence, scenarios, snapshots, graph keyboard navigation, search, backup/restore, Markdown export, missing-key state, and mobile layout. Test artifacts are written to the operating system temp directory. `SIGNALFORGE_URL` overrides the test server address.

## Architecture

```text
index.html + style.css + app.mjs  →  UI and local persistence
core.mjs                         →  validation, evidence model, rankings, snapshots, exports
demo.mjs                         →  explicitly fictional demo
server.py                        →  optional local Responses API orchestration
```

The pure decision engine is independent of the UI and research provider. That separation makes it possible to replace localStorage with a database or add new research providers without changing the scoring rules.

## Next substantial extensions

1. Versioned SQLite/Postgres workspaces and immutable evidence history.
2. Provider-backed source ingestion with extraction evaluations and human approval.
3. Scheduled monitoring with explicit budgets and change provenance.
4. Authenticated teams, permissions, and independently calibrated source-quality metrics.
