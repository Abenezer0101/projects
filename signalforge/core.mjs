export const FACTORS = ["fit", "growth", "timing", "risk"];
export const DEFAULT_WEIGHTS = { fit: 35, growth: 25, timing: 25, risk: 15 };
export const uid = () => globalThis.crypto.randomUUID();
export function safeUrl(value) {
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
}
export function validateWorkspace(raw) {
  const fail = (message) => {
    throw new Error(message);
  };
  if (
    !raw ||
    raw.version !== 1 ||
    !Array.isArray(raw.entities) ||
    !Array.isArray(raw.evidence) ||
    !Array.isArray(raw.runs)
  )
    fail("Unsupported workspace. Import a SignalForge v1 backup.");
  if (
    raw.entities.length > 100 ||
    raw.evidence.length > 2000 ||
    raw.runs.length > 50
  )
    fail("Workspace exceeds the 100-account, 2,000-evidence or 50-run limit.");
  const string = (x, n = 200) =>
    typeof x === "string" && x.trim().length > 0 && x.length <= n;
  const ids = new Set();
  for (const e of raw.entities) {
    if (
      !string(e.id) ||
      ids.has(e.id) ||
      !string(e.name, 100) ||
      !string(e.sector, 100)
    )
      fail("Invalid or duplicate account.");
    ids.add(e.id);
  }
  const evIds = new Set();
  for (const e of raw.evidence) {
    if (
      !string(e.id) ||
      evIds.has(e.id) ||
      !ids.has(e.entityId) ||
      !FACTORS.includes(e.factor) ||
      !Number.isInteger(e.value) ||
      Math.abs(e.value) > 2 ||
      ![1, 2, 3].includes(e.quality) ||
      !string(e.title, 200) ||
      !string(e.claim, 5000) ||
      typeof e.url !== "string" ||
      (e.url && !safeUrl(e.url)) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(e.date) ||
      !Number.isFinite(Date.parse(e.date))
    )
      fail("Invalid evidence. Check account, date, URL and rating.");
    if (
      new Date(e.date).toISOString().slice(0, 10) !== e.date ||
      e.date > new Date().toISOString().slice(0, 10)
    )
      fail(
        "Source dates must be real calendar dates and cannot be in the future.",
      );
    evIds.add(e.id);
  }
  for (const f of FACTORS)
    if (
      !Number.isFinite(raw.weights?.[f]) ||
      raw.weights[f] < 0 ||
      raw.weights[f] > 100
    )
      fail("Weights must be between 0 and 100.");
  if (!FACTORS.some((f) => raw.weights[f] > 0))
    fail("At least one weight must be above zero.");
  for (const r of raw.runs) {
    if (
      !string(r.id) ||
      !string(r.at) ||
      !Array.isArray(r.rows) ||
      r.rows.length > 100
    )
      fail("Invalid snapshot.");
    for (const row of r.rows)
      if (
        !string(row.id) ||
        !string(row.name, 100) ||
        !Number.isFinite(row.score) ||
        row.score < 0 ||
        row.score > 100 ||
        !Number.isFinite(row.coverage) ||
        row.coverage < 0 ||
        row.coverage > 100
      )
        fail("Invalid snapshot score.");
  }
  if (typeof raw.title !== "string" || raw.title.length > 200)
    fail("Invalid workspace title.");
  // Reconstruct allowed fields; imported data never becomes executable configuration.
  return {
    version: 1,
    title: raw.title,
    demo: raw.demo === true,
    entities: raw.entities.map(({ id, name, sector }) => ({
      id,
      name,
      sector,
    })),
    evidence: raw.evidence.map(
      ({ id, entityId, factor, value, quality, title, claim, url, date }) => ({
        id,
        entityId,
        factor,
        value,
        quality,
        title,
        claim,
        url,
        date,
      }),
    ),
    weights: Object.fromEntries(FACTORS.map((f) => [f, raw.weights[f]])),
    runs: raw.runs.map(({ id, at, rows }) => ({
      id,
      at,
      rows: rows.map(({ id, name, score, coverage }) => ({
        id,
        name,
        score,
        coverage,
      })),
    })),
  };
}
export function rank(workspace, now = new Date()) {
  const total = FACTORS.reduce((n, f) => n + workspace.weights[f], 0) || 1;
  return workspace.entities
    .map((entity) => {
      const evidence = workspace.evidence.filter(
        (e) => e.entityId === entity.id,
      );
      const factors = Object.fromEntries(
        FACTORS.map((f) => {
          const items = evidence.filter((e) => e.factor === f);
          // One vote per URL (or manual source title), preventing duplicate-source inflation.
          const sources = new Map();
          for (const e of items) {
            const key = e.url
              ? safeUrl(e.url).replace(/#.*$/, "")
              : e.title.trim().toLowerCase();
            const age = Math.max(0, (now - new Date(e.date)) / 86400000);
            const weight = e.quality * Math.pow(0.5, age / 180);
            const s = sources.get(key) || { sum: 0, count: 0, weight: 0 };
            s.sum += e.value;
            s.count++;
            s.weight = Math.max(s.weight, weight);
            sources.set(key, s);
          }
          let sum = 0,
            weight = 0;
          for (const s of sources.values()) {
            sum += (s.sum / s.count) * s.weight;
            weight += s.weight;
          }
          return [
            f,
            {
              score: weight ? 50 + (25 * sum) / weight : 50,
              count: items.length,
              sources: sources.size,
              disputed:
                items.some((e) => e.value > 0) &&
                items.some((e) => e.value < 0),
            },
          ];
        }),
      );
      let score = 0,
        coverage = 0,
        unknown = 0;
      for (const f of FACTORS) {
        const w = workspace.weights[f] / total;
        score += factors[f].score * w;
        if (factors[f].count) coverage += w * 100;
        else unknown += w * 50;
      }
      const disputed = FACTORS.filter((f) => factors[f].disputed);
      return {
        ...entity,
        score: Math.round(score),
        coverage: Math.round(coverage),
        low: Math.round(score - unknown),
        high: Math.round(score + unknown),
        factors,
        evidence,
        disputed,
        status:
          coverage < 75
            ? "Research"
            : disputed.length
              ? "Review"
              : score >= 70
                ? "Prioritize"
                : score >= 45
                  ? "Watch"
                  : "Deprioritize",
      };
    })
    .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
}
export function snapshot(workspace, now = new Date()) {
  return {
    id: uid(),
    at: now.toISOString(),
    rows: rank(workspace, now).map(({ id, name, score, coverage }) => ({
      id,
      name,
      score,
      coverage,
    })),
  };
}
export function changes(workspace) {
  const previous = workspace.runs.at(-1);
  if (!previous) return [];
  return rank(workspace).map((row) => {
    const old = previous.rows.find((x) => x.id === row.id);
    return {
      ...row,
      delta: old ? row.score - old.score : null,
      coverageDelta: old ? row.coverage - old.coverage : null,
    };
  });
}
export function brief(workspace) {
  const rows = rank(workspace);
  return (
    `# ${workspace.title}\n\nGenerated ${new Date().toISOString()}\n${workspace.demo ? "FICTIONAL DEMO DATA — not real company research." : "Analyst-entered evidence; review sources before acting."}\n\nWeights: ${FACTORS.map((f) => `${f} ${workspace.weights[f]}`).join(", ")}. Scores are decision heuristics, not probabilities. Risk rates resilience: positive = lower risk. Missing factors use 50; ranges show unknown factors at 0–100.\n\n` +
    rows
      .map(
        (r, i) =>
          `## ${i + 1}. ${r.name} — ${r.score}/100 · ${r.status}\n\nCoverage: ${r.coverage}%. Missing-data range: ${r.low}–${r.high}. Conflicting factors: ${r.disputed.join(", ") || "none detected"}.\n\n` +
          r.evidence
            .map(
              (e) =>
                `- [${e.factor}; ${e.value > 0 ? "+" : ""}${e.value}] ${e.claim}\n  Source: ${e.title}${e.url ? " — " + e.url : ""} (${e.date}); analyst quality ${e.quality}/3.`,
            )
            .join("\n"),
      )
      .join("\n\n")
  );
}
