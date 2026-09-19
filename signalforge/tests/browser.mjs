import { createRequire } from "node:module";
import assert from "node:assert/strict";
import { tmpdir } from "node:os";
import { join } from "node:path";
const require = createRequire(import.meta.url);
const { chromium } = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + "/playwright")
  : require("playwright");
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROMIUM_EXECUTABLE_PATH
    ? {
        executablePath: process.env.CHROMIUM_EXECUTABLE_PATH,
        args: ["--no-sandbox", "--disable-dev-shm-usage"],
      }
    : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const base = process.env.SIGNALFORGE_URL || "http://127.0.0.1:8787";
await page.goto(base);
await page.getByRole("heading", { name: "Find the signal." }).waitFor();
assert.equal(await page.locator("tbody tr").count(), 6);
await page.screenshot({
  path: join(tmpdir(), "signalforge-desktop.png"),
  fullPage: true,
});
await page.getByRole("button", { name: "+ Add account", exact: true }).click();
await page.getByLabel("Account name").fill("Test <script>alert(1)</script>");
await page.getByLabel("Sector", { exact: true }).fill("Testing");
await page.getByRole("button", { name: "Save to workspace" }).click();
assert.equal(await page.locator("tbody tr").count(), 7);
await page.getByRole("button", { name: /Test <script>/ }).click();
await page.getByRole("button", { name: "+ Add evidence", exact: true }).click();
await page
  .getByLabel("Evidence / claim")
  .fill("A real workflow test with a supported claim.");
await page.getByLabel("Source title", { exact: true }).fill("Test source");
await page.getByLabel("Source URL").fill("https://example.com/research");
await page.getByRole("button", { name: "Save to workspace" }).click();
assert.equal(await page.locator(".evidence-card").count(), 1);
await page.getByRole("button", { name: "Edit", exact: true }).click();
await page.getByLabel("Impact rating").selectOption("-2");
await page.getByRole("button", { name: "Save to workspace" }).click();
assert.match(await page.locator(".evidence-card .tag").innerText(), /-2/);
await page.reload();
assert.equal(await page.locator("tbody tr").count(), 7);
await page.getByRole("button", { name: "Save snapshot", exact: true }).click();
await page.locator('nav [data-view="scenarios"]').click();
await page.locator("#weight-fit").fill("100");
assert.equal(await page.locator("#output-fit").innerText(), "100");
await page.locator('nav [data-view="changes"]').click();
assert.equal(await page.locator("tbody tr").count(), 7);
assert.ok((await page.locator("tbody").innerText()).includes("+"));
await page.locator('nav [data-view="map"]').click();
assert.equal(await page.locator("svg [role=button]").count(), 7);
await page.locator("svg [role=button]").first().focus();
await page.keyboard.press("Enter");
assert.equal(await page.locator("#page-name").innerText(), "Account dossier");
await page.locator('nav [data-view="evidence"]').click();
await page
  .getByRole("textbox", { name: "Search evidence" })
  .fill("real workflow test");
assert.equal(await page.locator(".evidence-card").count(), 1);
const downloadPromise = page.waitForEvent("download");
await page.locator("#backup").click();
const download = await downloadPromise;
assert.equal(download.suggestedFilename(), "signalforge-workspace.json");
await download.saveAs(join(tmpdir(), "signalforge-backup.json"));
page.on("dialog", (dialog) => dialog.accept());
await page.locator("#new-workspace").click();
assert.equal(await page.locator("tbody tr").count(), 0);
await page
  .locator("#import-file")
  .setInputFiles(join(tmpdir(), "signalforge-backup.json"));
await page.waitForFunction(
  () => document.querySelectorAll("tbody tr").length === 7,
);
const briefPromise = page.waitForEvent("download");
await page.locator("#export-brief").click();
assert.equal(
  (await briefPromise).suggestedFilename(),
  "signalforge-decision-brief.md",
);
await page.locator('nav [data-view="research"]').click();
assert.equal(
  await page.getByRole("button", { name: "Run investigation" }).isDisabled(),
  true,
);
await page.setViewportSize({ width: 390, height: 844 });
await page.locator('nav [data-view="overview"]').click();
assert.equal(
  await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  ),
  true,
);
assert.equal(await page.locator("#backup").isVisible(), true);
await page.screenshot({
  path: join(tmpdir(), "signalforge-mobile.png"),
  fullPage: true,
});
assert.deepEqual(errors, []);
await browser.close();
console.log(
  "Browser flows passed: add/edit evidence, safe text, persistence, weights, snapshots, graph keyboard navigation, filtering, backup/restore, brief, disabled API state, mobile layout.",
);
