import {
  FACTORS,
  DEFAULT_WEIGHTS,
  uid,
  safeUrl,
  validateWorkspace,
  rank,
  snapshot,
  changes,
  brief,
} from "./core.mjs";
import { demoWorkspace } from "./demo.mjs";
const $ = (s) => document.querySelector(s),
  esc = (s) =>
    String(s ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const KEY = "signalforge.workspace.v1";
let state,
  view = "overview",
  filter = "",
  entityFilter = "",
  selected = null,
  researchResult = null,
  researchBusy = false,
  backend = { enabled: false },
  storageProblem = "";
try {
  const saved = localStorage.getItem(KEY);
  state = saved ? validateWorkspace(JSON.parse(saved)) : demoWorkspace();
} catch {
  state = demoWorkspace();
  storageProblem =
    "Saved data could not be loaded. Export any recoverable backup before saving new changes.";
}
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $("#toast").classList.remove("show"), 4500);
}
function save() {
  try {
    validateWorkspace(state);
    localStorage.setItem(KEY, JSON.stringify(state));
    return true;
  } catch (e) {
    toast("Not saved: " + e.message);
    return false;
  }
}
const factorName = (f) =>
  f === "risk" ? "Resilience" : f[0].toUpperCase() + f.slice(1);
const status = (r) =>
  `<span class="tag ${r.status.toLowerCase()}">${r.status}</span>`;
const title = (eye, name, sub, actions = "") =>
  `<div class="title-row"><div><div class="eyebrow">${eye}</div><h1>${name}</h1><p class="sub">${sub}</p></div><div class="actions">${actions}</div></div>`;
const notice = () =>
  state.demo
    ? '<div class="notice">DEMO DATA · All companies, sources and claims in this workspace are fictional. Explore the model, or start an empty workspace for real research.</div>'
    : "";
const panel = (name, content, meta = "") =>
  `<section class="panel"><div class="panel-head"><h2>${name}</h2><small>${meta}</small></div>${content}</section>`;
function table(rows, comparison = false) {
  return rows.length
    ? `<div class="table-wrap"><table><thead><tr><th>ACCOUNT</th><th>SCORE</th><th>${comparison ? "CHANGE" : "COVERAGE"}</th><th>NEXT STEP</th></tr></thead><tbody>${rows
        .map(
          (r) =>
            `<tr><td><button class="account-button" data-account="${esc(r.id)}"><span class="account-icon">${esc(
              r.name
                .split(" ")
                .map((x) => x[0])
                .slice(0, 2)
                .join(""),
            )}</span><span>${esc(r.name)}<small>${esc(r.sector)}</small></span></button></td><td><span class="score">${r.score}</span><span class="score-bar"><i style="width:${r.score}%"></i></span></td><td>${comparison ? `<span class="${r.delta < 0 ? "negative" : "delta"}">${r.delta === null ? "New" : (r.delta > 0 ? "+" : "") + r.delta}</span>` : `${r.coverage}%`}</td><td>${status(r)}</td></tr>`,
        )
        .join("")}</tbody></table></div>`
    : '<div class="empty">Your next discovery starts here.<br>Add your first account to begin.</div>';
}
function overview() {
  const rows = rank(state),
    disputes = rows.filter((r) => r.disputed.length),
    coverage = rows.length
      ? Math.round(rows.reduce((a, r) => a + r.coverage, 0) / rows.length)
      : 0;
  return (
    title(
      "THE INTELLIGENCE WORKSPACE",
      "Find the signal.<br>Make your next move.",
      "Turn scattered evidence into decisions you can explain.",
      '<button data-action="snapshot">Save snapshot</button><button class="primary" data-action="account">+ Add account</button>',
    ) +
    notice() +
    `<div class="metrics">${[
      ["Accounts tracked", rows.length, "A focused view of your market"],
      [
        "Evidence collected",
        state.evidence.length,
        "Every claim has a source record",
      ],
      ["Factor coverage", coverage + "%", "Average weighted factor coverage"],
      [
        "Needs a second look",
        disputes.length,
        "Accounts with conflicting ratings",
      ],
    ]
      .map(
        ([label, value, sub]) =>
          `<div class="metric"><div class="metric-label">${label}</div><strong>${value}</strong><small>${sub}</small></div>`,
      )
      .join(
        "",
      )}</div><div class="two-col"><div>${panel("Opportunity radar", table(rows) + '<div class="list-note">Scores / 100 · Analyst ratings, weighted by source quality and recency. Click an account to inspect.</div>', "RANKED BY YOUR PRIORITIES")}${panel("A repeatable research loop", `<div class="panel-body"><div class="pipeline"><div><span>01 / COLLECT</span><h3>Build the evidence</h3><p>Add sources, claims and ratings.</p></div><div><span>02 / CHALLENGE</span><h3>Expose uncertainty</h3><p>Inspect conflicts and missing factors.</p></div><div><span>03 / DECIDE</span><h3>Make the next move</h3><p>Test priorities and track changes.</p></div></div></div>`)}</div><div>${panel(
      "Signals worth your attention",
      `<div class="panel-body">${
        [
          ...disputes.map((r) => ({
            r,
            icon: "↯",
            text: `Conflicting ${r.disputed.map(factorName).join(", ").toLowerCase()} evidence. Review both sides before acting.`,
          })),
          ...rows
            .filter((r) => r.coverage < 100)
            .map((r) => ({
              r,
              icon: "◌",
              text: `${100 - r.coverage}% of the weighted model is unknown. Score could range from ${r.low} to ${r.high}.`,
            })),
        ]
          .slice(0, 4)
          .map(
            ({ r, icon, text }) =>
              `<div class="signal"><span class="signal-icon">${icon}</span><div><h3>${esc(r.name)}</h3><p>${text}</p><button class="text-button" data-account="${esc(r.id)}">Inspect evidence →</button></div></div>`,
          )
          .join("") ||
        '<p class="sub">No conflicting or missing factors detected. Continue checking source quality.</p>'
      }</div>`,
      "REVIEW QUEUE",
    )}${panel("Your judgment, made visible", `<div class="panel-body"><p class="sub">What matters most changes the answer. Tune the model to the decision in front of you.</p>${FACTORS.map((f) => `<div class="factor-row"><span>${factorName(f)}</span><div class="factor-bar"><i style="width:${state.weights[f]}%"></i></div><span>${state.weights[f]}</span></div>`).join("")}<button class="wide-button" data-go="scenarios">Open decision lab →</button></div>`)}</div></div>`
  );
}
function evidenceCard(e) {
  const entity = state.entities.find((x) => x.id === e.entityId);
  return `<article class="evidence-card"><div class="top"><span class="sub">${esc(entity?.name)}</span><span class="tag ${e.value < 0 ? "review" : ""}">${factorName(e.factor)} · ${e.value > 0 ? "+" : ""}${e.value}</span></div><p>${esc(e.claim)}</p><div class="source">${e.url ? `<a href="${esc(safeUrl(e.url))}" target="_blank" rel="noopener noreferrer">${esc(e.title)} ↗</a>` : esc(e.title)}<br>${esc(e.date)} · Analyst quality ${e.quality}/3${e.url ? "" : " · Manual source; no linked URL"}</div><div class="card-actions"><button data-edit="${esc(e.id)}">Edit</button><button class="danger" data-delete="${esc(e.id)}">Remove</button></div></article>`;
}
function evidence() {
  const items = state.evidence.filter(
    (e) =>
      (!entityFilter || e.entityId === entityFilter) &&
      (!filter ||
        `${e.title} ${e.claim} ${state.entities.find((x) => x.id === e.entityId)?.name}`
          .toLowerCase()
          .includes(filter.toLowerCase())),
  );
  return (
    title(
      "TRACE EVERY CLAIM",
      "The evidence library.",
      "A decision is only as strong as what stands behind it.",
      '<button class="primary" data-action="evidence">+ Add evidence</button>',
    ) +
    notice() +
    `<div class="toolbar"><input id="search" aria-label="Search evidence" placeholder="Search claims, sources, accounts…" value="${esc(filter)}"><select id="entity-filter" aria-label="Filter account"><option value="">All accounts</option>${state.entities.map((e) => `<option value="${esc(e.id)}" ${entityFilter === e.id ? "selected" : ""}>${esc(e.name)}</option>`).join("")}</select><span class="sub">${items.length} evidence records</span></div><div class="evidence-grid">${items.map(evidenceCard).join("") || '<div class="empty">No evidence matches this view.</div>'}</div>`
  );
}
function accountDetail() {
  const r = rank(state).find((r) => r.id === selected);
  if (!r) {
    view = "overview";
    return overview();
  }
  return (
    title(
      "ACCOUNT DOSSIER",
      esc(r.name),
      esc(r.sector),
      `<button data-go="overview">← Overview</button><button class="primary" data-action="evidence" data-entity="${esc(r.id)}">+ Add evidence</button>`,
    ) +
    notice() +
    `<div class="detail-summary"><span>Score <b>${r.score}/100</b></span><span>Coverage <b>${r.coverage}%</b></span><span>Missing-data range <b>${r.low}–${r.high}</b></span>${status(r)}</div>${panel("How the score is built", `<div class="panel-body">${FACTORS.map((f) => `<div class="factor-row"><span>${factorName(f)}</span><div class="factor-bar"><i style="width:${r.factors[f].score}%"></i></div><span>${Math.round(r.factors[f].score)}</span></div><p class="source">${r.factors[f].count} records · ${r.factors[f].sources} distinct source keys${!r.factors[f].count ? " · Unknown: neutral placeholder, not observed evidence" : ""}${r.factors[f].disputed ? " · Conflicting positive and negative ratings" : ""}</p>`).join("")}</div>`)}<div class="evidence-grid">${r.evidence.map(evidenceCard).join("") || '<div class="empty">Add evidence to move beyond an unknown score.</div>'}</div>`
  );
}
function mapView() {
  const entities = rank(state),
    shown = entities.slice(0, 24),
    w = 900,
    h = Math.max(450, shown.length * 72),
    fy = FACTORS.map((_, i) => 80 + (i * (h - 160)) / 3);
  return (
    title(
      "FOLLOW THE CONNECTIONS",
      "See how it connects.",
      "Accounts connect to decision factors through your evidence. Select an account to investigate.",
    ) +
    panel(
      "Evidence relationships",
      `<svg class="graph" viewBox="0 0 ${w} ${h}" aria-label="Accounts linked to decision factors">${shown.flatMap((e, i) => FACTORS.filter((f) => e.factors[f].count).map((f) => `<line x1="230" y1="${55 + (i * (h - 110)) / Math.max(shown.length - 1, 1)}" x2="650" y2="${fy[FACTORS.indexOf(f)]}"><title>${esc(e.name)} → ${factorName(f)}: ${e.factors[f].count} records</title></line>`)).join("")}${shown.map((e, i) => `<g role="button" tabindex="0" aria-label="Inspect ${esc(e.name)}" data-account="${esc(e.id)}"><circle cx="230" cy="${55 + (i * (h - 110)) / Math.max(shown.length - 1, 1)}" r="15"/><text x="201" y="${59 + (i * (h - 110)) / Math.max(shown.length - 1, 1)}" text-anchor="end">${esc(e.name)}</text><text x="230" y="${59 + (i * (h - 110)) / Math.max(shown.length - 1, 1)}" text-anchor="middle" style="font-size:9px">${e.score}</text></g>`).join("")}${FACTORS.map((f, i) => `<circle class="factor-node" cx="650" cy="${fy[i]}" r="34"/><text class="factor-text" x="650" y="${fy[i] + 4}" text-anchor="middle">${factorName(f)}</text>`).join("")}</svg><div class="legend"><span>○ Account / score</span><span>— Evidence-backed factor link</span><span>${shown.length} of ${entities.length} accounts</span></div>`,
    )
  );
}
function scenarios() {
  return (
    title(
      "TURN ASSUMPTIONS INTO QUESTIONS",
      "What if your priorities changed?",
      "Adjust the weights. Watch the ranking respond. No hidden formula.",
      '<button data-action="reset-weights">Reset weights</button><button data-action="snapshot">Save snapshot</button>',
    ) +
    `<div class="two-col"><div>${panel("Live ranking", `<div id="scenario-table">${table(rank(state))}</div>`)}</div><div>${panel("Your decision model", `<div class="panel-body"><div class="weights">${FACTORS.map((f) => `<div><label class="weight-label" for="weight-${f}"><span>${factorName(f)}</span><output id="output-${f}">${state.weights[f]}</output></label><input id="weight-${f}" data-weight="${f}" type="range" min="0" max="100" value="${state.weights[f]}"></div>`).join("")}</div><p class="checks" style="margin-top:22px">Weights normalize to 100% automatically. Missing factors score 50 and lower coverage. Evidence is rated −2 to +2; positive resilience means lower risk. Source quality and a 180-day recency half-life weight the evidence. These are decision heuristics, not calibrated probabilities.</p></div>`)}</div></div>`
  );
}
function changeView() {
  const previous = state.runs.at(-1);
  return (
    title(
      "A MEMORY FOR YOUR DECISIONS",
      "Know what changed.",
      "Compare the current model with your most recent saved snapshot.",
      '<button class="primary" data-action="snapshot">Save new snapshot</button>',
    ) +
    panel(
      "Since your last snapshot",
      previous
        ? table(changes(state), true) +
            `<div class="list-note">Compared with ${esc(new Date(previous.at).toLocaleString())}. Changes reflect evidence edits, weights and source aging. Deleted accounts: ${previous.rows.filter((r) => !state.entities.some((e) => e.id === r.id)).length}.</div>`
        : '<div class="empty">Save your first snapshot, then add evidence or adjust weights to see the difference.</div>',
    ) +
    panel(
      "Snapshot history",
      `<div class="panel-body">${
        state.runs
          .slice()
          .reverse()
          .map(
            (r) =>
              `<div class="signal"><div><h3>${esc(new Date(r.at).toLocaleString())}</h3><small>${r.rows.length} accounts · Highest score: ${Math.max(0, ...r.rows.map((x) => x.score))}</small></div></div>`,
          )
          .join("") ||
        '<p class="sub">No snapshots yet. The latest 50 are kept in your workspace backup.</p>'
      }</div>`,
    )
  );
}
function citations(part) {
  let result = "",
    pos = 0;
  const chars = Array.from(part.text);
  for (const a of (part.annotations || [])
    .filter((a) => a.type === "url_citation" && safeUrl(a.url))
    .sort((a, b) => a.start_index - b.start_index)) {
    const start = a.start_index,
      end = a.end_index;
    if (
      !Number.isInteger(start) ||
      !Number.isInteger(end) ||
      start < pos ||
      end > chars.length ||
      end <= start
    )
      continue;
    result +=
      esc(chars.slice(pos, start).join("")) +
      `<a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(chars.slice(start, end).join("") || a.title || "Source")}</a>`;
    pos = end;
  }
  return result + esc(chars.slice(pos).join(""));
}
function research() {
  return (
    title(
      "OPTIONAL / CONNECTED RESEARCH",
      "Three lenses. A clearer picture.",
      "An opportunity researcher, a skeptic, and a decision editor investigate your question.",
    ) +
    panel(
      "Launch an investigation",
      `<div class="panel-body"><p class="sub">${backend.enabled ? "Local research server connected. Each run makes three sequential API requests; two can search the web." : "Live research needs the included local Python server plus OPENAI_API_KEY and OPENAI_MODEL. The rest of SignalForge works without them."}</p><form id="research-form"><label for="question">What do you want to investigate?</label><textarea id="question" maxlength="1500" required placeholder="Compare three industrial automation companies as potential customers. Find recent buying signals, challenge the strongest claims, and suggest what to verify next."></textarea><label class="check-label"><input id="research-consent" type="checkbox" required><span>Send this question to OpenAI and use my API billing for this run. Workspace evidence is not sent.</span></label><button class="primary" ${!backend.enabled || researchBusy ? "disabled" : ""}>${researchBusy ? "Investigating…" : "Run investigation →"}</button></form><p class="checks" style="margin-top:14px">AI findings need your review. They never automatically become scored evidence. Copy a claim into the evidence library with its source after checking it.</p></div>`,
    ) +
    (researchResult
      ? panel(
          "Investigation report",
          `<div class="panel-body"><div class="actions"><button data-action="research-export">Export report ↓</button></div>${researchResult.stages
            .map(
              (s) =>
                `<section class="research-role"><h3>${esc(s.role)}</h3>${s.parts.map((p) => `<div class="research-results">${citations(p)}</div>`).join("")}<div class="source">${s.parts
                  .flatMap((p) => p.annotations || [])
                  .filter((a) => safeUrl(a.url))
                  .map(
                    (a) =>
                      `<a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(a.title || a.url)} ↗</a>`,
                  )
                  .join(" · ")}</div></section>`,
            )
            .join("")}</div>`,
        )
      : "")
  );
}
function render() {
  const names = {
    overview: "Overview",
    evidence: "Evidence library",
    map: "Knowledge map",
    scenarios: "Decision lab",
    changes: "Change log",
    research: "Live research",
    detail: "Account dossier",
  };
  $("#workspace-title").textContent = state.title;
  $("#evidence-count").textContent = state.evidence.length;
  $("#mode-badge").textContent = state.demo
    ? "Fictional demo"
    : "Your workspace";
  $("#page-name").textContent = names[view];
  document
    .querySelectorAll("nav button")
    .forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $("#main").innerHTML = {
    overview,
    evidence,
    map: mapView,
    scenarios,
    changes: changeView,
    research,
    detail: accountDetail,
  }[view]();
}
function navigate(v) {
  view = v;
  render();
  window.scrollTo(0, 0);
}
function openEditor(kind, id = "", entityId = "") {
  if (kind === "evidence" && !state.entities.length) {
    toast("Add an account first.");
    return;
  }
  const e = state.evidence.find((e) => e.id === id);
  $("#dialog-title").textContent =
    kind === "account"
      ? "Add an account"
      : e
        ? "Edit evidence"
        : "Add evidence";
  $("#form-error").textContent = "";
  $("#dialog-fields").innerHTML =
    kind === "account"
      ? '<label for="name">Account name</label><input id="name" name="name" maxlength="100" required><label for="sector">Sector</label><input id="sector" name="sector" maxlength="100" required placeholder="e.g. Industrial automation">'
      : `<label for="entityId">Account</label><select id="entityId" name="entityId">${state.entities.map((a) => `<option value="${esc(a.id)}" ${(e?.entityId || entityId) === a.id ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</select><label for="claim">Evidence / claim</label><textarea id="claim" name="claim" maxlength="5000" required>${esc(e?.claim || "")}</textarea><label for="source-title">Source title</label><input id="source-title" name="title" maxlength="200" value="${esc(e?.title || "")}" required><label for="url">Source URL (optional for manual notes)</label><input id="url" name="url" type="url" value="${esc(e?.url || "")}" placeholder="https://…"><div class="form-row"><div><label for="factor">Factor</label><select id="factor" name="factor">${FACTORS.map((f) => `<option value="${f}" ${e?.factor === f ? "selected" : ""}>${factorName(f)}</option>`).join("")}</select></div><div><label for="value">Impact rating</label><select id="value" name="value">${[-2, -1, 0, 1, 2].map((n) => `<option value="${n}" ${(e?.value ?? 1) === n ? "selected" : ""}>${n > 0 ? "+" : ""}${n} · ${["Strong negative", "Negative", "Neutral", "Positive", "Strong positive"][n + 2]}</option>`).join("")}</select></div></div><div class="form-row"><div><label for="quality">Analyst source quality</label><select id="quality" name="quality">${[1, 2, 3].map((n) => `<option value="${n}" ${(e?.quality ?? 2) === n ? "selected" : ""}>${n} · ${["Low", "Medium", "High"][n - 1]}</option>`).join("")}</select></div><div><label for="date">Source date</label><input id="date" name="date" type="date" required max="${new Date().toISOString().slice(0, 10)}" value="${esc(e?.date || new Date().toISOString().slice(0, 10))}"></div></div><p class="checks">For resilience, positive means lower risk. Ratings are your interpretation, not a verified fact.</p>`;
  $("#editor-form").onsubmit = (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
      const next = structuredClone(state);
      if (kind === "account")
        next.entities.push({
          id: uid(),
          name: data.name.trim(),
          sector: data.sector.trim(),
        });
      else {
        const item = {
          ...data,
          id: e?.id || uid(),
          value: Number(data.value),
          quality: Number(data.quality),
          title: data.title.trim(),
          claim: data.claim.trim(),
          url: data.url.trim(),
        };
        if (e)
          next.evidence[next.evidence.findIndex((x) => x.id === e.id)] = item;
        else next.evidence.push(item);
      }
      validateWorkspace(next);
      state = next;
      save();
      $("#editor").close();
      render();
    } catch (err) {
      $("#form-error").textContent = err.message;
    }
  };
  $("#editor").showModal();
}
function download(filename, content, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.addEventListener("click", (event) => {
  const el = event.target.closest("button,[data-account]");
  if (!el) return;
  if (el.dataset.view) return navigate(el.dataset.view);
  if (el.dataset.go) return navigate(el.dataset.go);
  if (el.dataset.account) {
    selected = el.dataset.account;
    return navigate("detail");
  }
  if (el.dataset.edit) return openEditor("evidence", el.dataset.edit);
  if (el.dataset.delete) {
    if (
      confirm(
        "Remove this evidence record? Export a backup first if you need to retain it.",
      )
    ) {
      state.evidence = state.evidence.filter((e) => e.id !== el.dataset.delete);
      save();
      render();
    }
    return;
  }
  switch (el.dataset.action) {
    case "account":
      openEditor("account");
      break;
    case "evidence":
      openEditor("evidence", "", el.dataset.entity);
      break;
    case "snapshot":
      state.runs.push(snapshot(state));
      state.runs = state.runs.slice(-50);
      save();
      render();
      toast(
        "Snapshot saved. Future changes will compare against this baseline.",
      );
      break;
    case "reset-weights":
      state.weights = { ...DEFAULT_WEIGHTS };
      save();
      render();
      break;
    case "research-export":
      download(
        "signalforge-research.json",
        JSON.stringify(researchResult, null, 2),
        "application/json",
      );
      break;
  }
});
document.addEventListener("keydown", (e) => {
  if (e.target.matches("g[data-account]") && ["Enter", " "].includes(e.key)) {
    e.preventDefault();
    selected = e.target.dataset.account;
    navigate("detail");
  }
});
document.addEventListener("input", (e) => {
  if (e.target.id === "search") {
    const pos = e.target.selectionStart;
    filter = e.target.value;
    render();
    $("#search").focus();
    $("#search").setSelectionRange(pos, pos);
  }
  if (e.target.dataset.weight) {
    const f = e.target.dataset.weight,
      n = Number(e.target.value);
    if (!n && FACTORS.every((k) => k === f || state.weights[k] === 0)) {
      e.target.value = state.weights[f];
      toast("Keep at least one weight above zero.");
      return;
    }
    state.weights[f] = n;
    $("#output-" + f).textContent = n;
    $("#scenario-table").innerHTML = table(rank(state));
    save();
  }
});
document.addEventListener("change", (e) => {
  if (e.target.id === "entity-filter") {
    entityFilter = e.target.value;
    render();
  }
});
$("#close-dialog").onclick = () => $("#editor").close();
$("#backup").onclick = () =>
  download(
    "signalforge-workspace.json",
    JSON.stringify(state, null, 2),
    "application/json",
  );
$("#export-brief").onclick = () =>
  download("signalforge-decision-brief.md", brief(state), "text/markdown");
$("#import").onclick = () => $("#import-file").click();
$("#import-file").onchange = async (e) => {
  try {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 4_000_000)
      throw Error("Backup is too large (4 MB maximum).");
    const next = validateWorkspace(JSON.parse(await file.text()));
    if (
      !confirm(
        "Replace this workspace with the imported backup? Export your current workspace first if needed.",
      )
    )
      return;
    state = next;
    entityFilter = "";
    filter = "";
    save();
    navigate("overview");
    toast("Workspace imported.");
  } catch (err) {
    toast("Import rejected: " + err.message);
  } finally {
    e.target.value = "";
  }
};
$("#new-workspace").onclick = () => {
  if (!confirm("Start empty? Export your current workspace first to keep it."))
    return;
  state = {
    version: 1,
    title: "My research workspace",
    demo: false,
    entities: [],
    evidence: [],
    weights: { ...DEFAULT_WEIGHTS },
    runs: [],
  };
  save();
  entityFilter = "";
  filter = "";
  navigate("overview");
};
document.addEventListener("submit", async (e) => {
  if (e.target.id !== "research-form") return;
  e.preventDefault();
  if (researchBusy) return;
  const question = $("#question").value.trim();
  if (question.length < 10) {
    toast("Write a question with at least 10 characters.");
    return;
  }
  researchBusy = true;
  render();
  toast("Research started. This can take several minutes.");
  try {
    const response = await fetch("./api/research", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-SignalForge-Token": backend.token,
      },
      body: JSON.stringify({ question }),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "Research failed.");
    researchResult = result;
    toast(
      "Investigation complete. Review the citations before using its findings.",
    );
  } catch (err) {
    toast(err.message);
  } finally {
    researchBusy = false;
    render();
  }
});
render();
if (storageProblem) toast(storageProblem);
fetch("./api/config")
  .then((r) => (r.ok ? r.json() : null))
  .then((c) => {
    if (c) {
      backend = c;
      if (view === "research") render();
    }
  })
  .catch(() => {});
