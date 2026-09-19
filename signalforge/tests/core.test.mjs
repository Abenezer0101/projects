import test from "node:test";
import assert from "node:assert/strict";
import {
  rank,
  validateWorkspace,
  safeUrl,
  changes,
  snapshot,
  brief,
} from "../core.mjs";
import { demoWorkspace } from "../demo.mjs";
const now = new Date("2026-09-19T12:00:00Z");
const empty = () => ({
  version: 1,
  title: "Test",
  demo: false,
  entities: [{ id: "a", name: "A", sector: "Test" }],
  evidence: [],
  weights: { fit: 25, growth: 25, timing: 25, risk: 25 },
  runs: [],
});
const record = (overrides = {}) => ({
  id: "e",
  entityId: "a",
  factor: "fit",
  value: 2,
  quality: 3,
  title: "Source",
  claim: "A claim",
  url: "https://example.com/report",
  date: "2026-09-18",
  ...overrides,
});
test("unknowns never masquerade as complete evidence", () => {
  const r = rank(empty(), now)[0];
  assert.deepEqual(
    [r.score, r.coverage, r.low, r.high, r.status],
    [50, 0, 0, 100, "Research"],
  );
});
test("observed factor narrows missing-data interval without filling gaps", () => {
  const w = empty();
  w.evidence = [record()];
  const r = rank(w, now)[0];
  assert.deepEqual([r.score, r.coverage, r.low, r.high], [63, 25, 25, 100]);
});
test("opposing source ratings trigger review when coverage is sufficient", () => {
  const w = empty();
  w.evidence = [
    ...["fit", "growth", "timing", "risk"].map((factor, i) =>
      record({ id: String(i), factor }),
    ),
    record({ id: "opposition", url: "https://example.org/counter", value: -2 }),
  ];
  const r = rank(w, now)[0];
  assert.equal(r.status, "Review");
  assert.deepEqual(r.disputed, ["fit"]);
});
test("duplicating the same source does not inflate its voting power", () => {
  const w = empty();
  w.evidence = [
    record(),
    record({ id: "b", url: "https://other.test/", value: -2 }),
  ];
  const before = rank(w, now)[0].score;
  w.evidence.push(record({ id: "c" }));
  assert.equal(rank(w, now)[0].score, before);
});
test("recent contradictory evidence outweighs old evidence of equal quality", () => {
  const w = empty();
  w.evidence = [
    record(),
    record({
      id: "b",
      url: "https://other.test/",
      value: -2,
      date: "2024-01-01",
    }),
  ];
  assert.ok(rank(w, now)[0].factors.fit.score > 90);
});
test("weight scaling preserves rankings", () => {
  const w = demoWorkspace();
  const before = rank(w, now).map((x) => x.score);
  for (const f of Object.keys(w.weights)) w.weights[f] *= 2;
  assert.deepEqual(
    rank(w, now).map((x) => x.score),
    before,
  );
});
test("raising a rating never decreases score across all rating pairs", () => {
  for (let i = -2; i < 2; i++) {
    const w = empty();
    w.evidence = [record({ value: i })];
    const before = rank(w, now)[0].score;
    w.evidence[0].value++;
    assert.ok(rank(w, now)[0].score >= before);
  }
});
test("all score bounds remain ordered for varied weights and ratings", () => {
  for (let i = 0; i < 100; i++) {
    const w = empty();
    w.weights.fit = i;
    w.evidence = [record({ value: (i % 5) - 2 })];
    const r = rank(w, now)[0];
    assert.ok(
      0 <= r.low && r.low <= r.score && r.score <= r.high && r.high <= 100,
    );
  }
});
test("backup rejects bad values and dangling evidence", () => {
  for (const invalid of [
    { value: 9 },
    { entityId: "missing" },
    { url: "javascript:alert(1)" },
    { quality: 0 },
    { date: "bad" },
  ]) {
    const w = empty();
    w.evidence = [record(invalid)];
    assert.throws(() => validateWorkspace(w));
  }
});
test("backup rejects duplicate account IDs and all-zero weights", () => {
  const w = empty();
  w.entities.push({ ...w.entities[0] });
  assert.throws(() => validateWorkspace(w));
  w.entities.pop();
  for (const f in w.weights) w.weights[f] = 0;
  assert.throws(() => validateWorkspace(w));
});
test("backup round trip and malformed snapshots", () => {
  const w = demoWorkspace();
  w.runs.push(snapshot(w));
  assert.deepEqual(validateWorkspace(JSON.parse(JSON.stringify(w))), w);
  w.runs[0].rows[0].score = Infinity;
  assert.throws(() => validateWorkspace(w));
});
test("snapshot detects changed score without mutating baseline", () => {
  const w = empty();
  w.runs.push(snapshot(w));
  w.evidence.push(record());
  assert.equal(changes(w)[0].delta, 13);
  assert.equal(w.runs[0].rows[0].score, 50);
});
test("brief discloses demo provenance and unknown-factor assumptions", () => {
  const text = brief(demoWorkspace());
  assert.match(text, /FICTIONAL DEMO/);
  assert.match(text, /Missing-data range/);
  assert.match(text, /Fictional strategy memo/);
});
test("unsafe URL protocols are rejected", () => {
  for (const s of [
    "javascript:alert(1)",
    "data:text/html,x",
    "file:///etc/passwd",
  ])
    assert.equal(safeUrl(s), "");
  assert.equal(safeUrl("https://example.com"), "https://example.com/");
});
