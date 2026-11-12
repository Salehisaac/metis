// Progress-system browser checks (Phase 5). Fresh context per scenario; fixture content via routing.
// Needs the dev server: python3 -m http.server 8765 --bind 127.0.0.1. Exits 1 on any problem.
import { readFileSync, mkdtempSync, cpSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
const { chromium } = process.env.PLAYWRIGHT_CORE
  ? await import(`${process.env.PLAYWRIGHT_CORE}/index.mjs`)
  : await import("playwright-core");

const ROOT = new URL("../../", import.meta.url);
const FIX = new URL("tests/fixtures/content/", ROOT);
const BASE = "http://127.0.0.1:8765/site/";
const L = "PY.M01.L01";
const EX = `${L}.E1`;
const problems = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) problems.push(msg); };

// Real passing pytest report for the fixture exercise.
const work = mkdtempSync(join(tmpdir(), "metis-progress-"));
const py = new URL(".venv/bin/python", ROOT).pathname;
execFileSync(py, ["-c", `import sys; sys.path.insert(0, "tools"); import scaffold, pathlib; scaffold.scaffold("${EX}", content=pathlib.Path("tests/fixtures/content"), workspace=pathlib.Path("${work}"))`], { cwd: ROOT.pathname });
cpSync(new URL(`exercises/${EX}/solution/words.py`, FIX), join(work, EX, "words.py"));
execFileSync(py, ["-m", "pytest", "-q", "-p", "no:cacheprovider"], { cwd: join(work, EX) });
const passingReport = readFileSync(join(work, EX, "result.xml"));

const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/opt/google/chrome/chrome", args: ["--no-sandbox"] });

async function freshContext({ initScript } = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  if (initScript) await context.addInitScript(initScript);
  await context.route("**/content/curriculum.json", async (route) => {
    const res = await route.fetch();
    const cur = await res.json();
    const m = cur.courses[0].modules[0];
    Object.assign(m.lessons[0], { authored: true, exercises: [EX], quizzes: ["q1", "q2", "q3"] });
    await route.fulfill({ response: res, json: cur });
  });
  await context.route(/\/content\/(lessons|exercises|assessments)\//, async (route) => {
    const rel = decodeURIComponent(new URL(route.request().url()).pathname.split("/content/")[1]);
    try { await route.fulfill({ status: 200, body: readFileSync(new URL(rel, FIX), "utf8") }); } catch { await route.fulfill({ status: 404, body: "" }); }
  });
  return context;
}
function watch(page, label) {
  page.on("console", (m) => { if (["error", "warning"].includes(m.type()) || /highlighted/i.test(m.text())) problems.push(`${label} console ${m.type()}: ${m.text()}`); });
  page.on("pageerror", (e) => problems.push(`${label} pageerror: ${e.message}`));
}
const statusText = (page) => page.locator(".progress-card .badge").first().textContent();
async function openLesson(page) {
  await page.goto(`${BASE}#/lesson/${L}`);
  await page.locator(".exercise h3").waitFor();
}
async function earnCompetence(page) {
  const q = page.locator(".lesson-body .quiz");
  await q.nth(0).getByLabel("print([1, 2])").check();
  await q.nth(0).getByRole("button", { name: "Check" }).click();
  await q.nth(1).getByLabel("False").check();
  await q.nth(1).getByRole("button", { name: "Check" }).click();
  await q.nth(2).locator("textarea").fill("[1, 2, 3]");
  await q.nth(2).getByRole("button", { name: "Check" }).click();
  await page.locator('.exercise input[type="file"]').setInputFiles({ name: "result.xml", mimeType: "application/xml", buffer: passingReport });
  await page.getByText("Saved to your progress.").waitFor();
  await page.getByRole("button", { name: "Mark lesson as completed" }).click();
  await page.waitForFunction(() => document.querySelector(".progress-card .badge")?.textContent === "competent", null, { timeout: 3000 }).catch(() => {});
}
async function goView(page, hash, heading) { // hash-only gotos resolve before the view renders
  await page.goto(`${BASE}${hash}`);
  await page.waitForFunction((t) => document.querySelector("#content h1")?.textContent === t, heading);
}
async function gotoData(page) { // a hash-only goto resolves before the view renders: wait for its heading
  await page.goto(`${BASE}#/data`);
  await page.waitForFunction(() => document.querySelector("#content h1")?.textContent === "Your data");
}
async function eventCount(page) {
  await gotoData(page);
  const t = await page.locator("#content").textContent();
  return Number((t.match(/\(IndexedDB\): (\d+) events/) ?? [])[1] ?? -1);
}

// ---- 1. statuses, persistence across reload, history, dashboard, bookmarks; clock-driven review -> mastery
{
  const context = await freshContext();
  const page = await context.newPage();
  watch(page, "main");
  await page.clock.install({ time: new Date("2026-11-12T10:00:00Z") });
  await openLesson(page);
  check(await statusText(page) === "started", "opening a lesson records 'started', never 'completed'");
  await earnCompetence(page);
  check(await statusText(page) === "competent", "quizzes + independent pass + completion -> competent");
  await page.getByRole("button", { name: "☆ Bookmark" }).click();
  await page.reload();
  await page.locator(".progress-card .badge").waitFor();
  check(await statusText(page) === "competent", "status survives reload (IndexedDB)");
  check(await page.getByRole("button", { name: "★ Bookmarked" }).getAttribute("aria-pressed") === "true", "bookmark survives reload");
  await goView(page, "#/", "Dashboard");
  const dash = await page.locator("#content").textContent();
  const definedLessons = JSON.parse(readFileSync(new URL("content/curriculum.json", ROOT))).courses
    .flatMap((c) => c.modules.flatMap((m) => m.lessons)).length;
  check(dash.includes(`1 of ${definedLessons}`) && !dash.includes("don't have lessons defined") && dash.includes("1 competent") && dash.includes("PY.M01.L01 · Running Python"), "dashboard shows real counts, next lesson and bookmark");
  check(dash.includes("Export it now"), "dashboard asks for a first backup");
  await goView(page, "#/history", "Learning history");
  const hist = await page.locator("#content").textContent();
  check(hist.includes("Marked lesson completed") && hist.includes("Exercise passed") && hist.includes("Answered quiz q3 correctly"), "history lists recorded events");
  const q = page.locator(".quiz");
  await goView(page, `#/review/${L}`, `Review: Running Python: interpreter, REPL, scripts, python -m`);
  const early = await page.locator("#content").textContent();
  check(early.includes("Not due until") && (await q.count()) === 0, "a review that isn't due shows no questions and records nothing");
  await page.clock.setSystemTime(new Date("2026-11-21T10:00:00Z")); // +9 days
  await goView(page, "#/revision", "Revision center");
  check((await page.locator("#content").textContent()).includes("Review now"), "review is due after the interval");
  await page.getByRole("link", { name: "Review now" }).click();
  await q.first().waitFor();
  await q.nth(0).getByLabel("print(1, 2)").check(); await q.nth(0).getByRole("button", { name: "Check" }).click(); // wrong first...
  await q.nth(0).getByLabel("print([1, 2])").check(); await q.nth(0).getByRole("button", { name: "Check" }).click(); // ...retry ignored
  await q.nth(1).getByLabel("False").check(); await q.nth(1).getByRole("button", { name: "Check" }).click();
  const midway = await page.locator("#content").textContent();
  check(!/Correct\.|Not quite\./.test(midway) && midway.includes("already recorded"), "no feedback before the last answer; retries refused");
  await q.nth(2).locator("textarea").fill("[1, 2, 3]"); await q.nth(2).getByRole("button", { name: "Check" }).click();
  await page.getByText("Review recorded").waitFor();
  const r1 = await page.locator("#content").textContent();
  check(r1.includes("2 of 3 correct") && r1.includes("Status: competent") && r1.includes("Not quite."), "review counts first answers only; feedback revealed at the end; 2/3 is not mastery");
  await goView(page, "#/revision", "Revision center");
  await goView(page, `#/review/${L}`, `Review: Running Python: interpreter, REPL, scripts, python -m`);
  check((await page.locator("#content").textContent()).includes("Not due until"), "an immediate retake after a failed review is refused");
  await page.clock.setSystemTime(new Date("2026-11-23T10:00:00Z"));
  await goView(page, "#/revision", "Revision center");
  await page.getByRole("link", { name: "Review now" }).click();
  await q.first().waitFor();
  await q.nth(0).getByLabel("print([1, 2])").check(); await q.nth(0).getByRole("button", { name: "Check" }).click();
  await q.nth(1).getByLabel("False").check(); await q.nth(1).getByRole("button", { name: "Check" }).click();
  await q.nth(2).locator("textarea").fill("[1, 2, 3]"); await q.nth(2).getByRole("button", { name: "Check" }).click();
  await page.getByText("Review recorded").waitFor();
  check((await page.locator("#content").textContent()).includes("Status: mastered"), "a due full review 7+ days after competence gives mastery");

  // export -> fresh context import gives identical status; re-import adds nothing
  await gotoData(page);
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export progress (JSON)" }).click()]);
  const exported = readFileSync(await download.path(), "utf8");
  check(!/\[1, 2, 3\]|print\(/.test(exported), "export holds no answer text");
  const n1 = await eventCount(page);
  await context.close();

  const c2 = await freshContext();
  const p2 = await c2.newPage();
  watch(p2, "import");
  await p2.clock.install({ time: new Date("2026-11-23T12:00:00Z") });
  await gotoData(p2);
  const importFile = (name, text) => p2.locator("#import-file").setInputFiles({ name, mimeType: "application/json", buffer: Buffer.from(text) });
  await importFile("p.json", exported);
  await p2.getByRole("button", { name: /^Import \d+ new events?$/ }).click();
  await p2.getByText(/Imported \d+ events/).waitFor();
  await openLesson(p2);
  check(await statusText(p2) === "mastered", "export -> import into a fresh browser reproduces the status");
  const n2 = await eventCount(p2);
  check(n2 === n1, `imported event count matches (${n1} -> ${n2})`);
  await importFile("p.json", exported);
  const noop = await p2.getByText("Nothing new to import.").waitFor({ timeout: 3000 }).then(() => true, () => false);
  check(noop, "re-importing the same file adds nothing");

  const payload = JSON.parse(exported);
  for (const [label, text] of [
    ["not JSON", "{oops"],
    ["a bad event", JSON.stringify({ ...payload, events: [...payload.events, { id: "zzzzzzzz-1", type: "evil", item: "x", at: payload.events[0].at }] })],
    ["a newer schema version", JSON.stringify({ ...payload, schemaVersion: 99 })],
    ["an oversized file", "x".repeat(5_000_001)],
  ]) {
    await p2.locator(".feedback").last().evaluate((el) => el.replaceChildren()); // clear the previous message
    await importFile("bad.json", text);
    await p2.waitForFunction(() => /rejected|too large/.test(document.querySelector("#content").textContent), null, { timeout: 3000 }).catch(() => {});
    const t = await p2.locator("#content").textContent();
    check(/rejected|too large/.test(t) && (await eventCount(p2)) === n2, `import of ${label} rejected, nothing changed`);
  }
  await c2.close();
}

// ---- 1b. two tabs: an export from a tab opened earlier still contains events recorded in another tab
{
  const context = await freshContext();
  const a = await context.newPage();
  const b = await context.newPage();
  watch(a, "tabA"); watch(b, "tabB");
  await openLesson(a);
  await gotoData(b); // tab B loaded its store now
  await a.getByRole("button", { name: "Mark lesson as completed" }).click();
  await a.waitForFunction(() => document.querySelector(".progress-card .badge")?.textContent === "completed");
  const [dl] = await Promise.all([b.waitForEvent("download"), b.getByRole("button", { name: "Export progress (JSON)" }).click()]);
  const types = JSON.parse(readFileSync(await dl.path(), "utf8")).events.map((e) => e.type);
  check(types.includes("lesson_completed"), "export from a stale tab includes events recorded in another tab");
  await context.close();
}

// ---- 2. corrupt stored record is quarantined, not deleted; site keeps working
{
  const context = await freshContext();
  const page = await context.newPage();
  watch(page, "quarantine");
  await openLesson(page); // creates the DB and one event
  await page.evaluate(() => new Promise((resolve, reject) => {
    const r = indexedDB.open("metis");
    r.onsuccess = () => {
      const tx = r.result.transaction("events", "readwrite");
      tx.objectStore("events").put({ id: "corrupt-0001", type: "evil", item: "<script>", at: "never" });
      tx.oncomplete = () => { r.result.close(); resolve(); };
      tx.onerror = () => reject(tx.error);
    };
  }));
  await page.reload();
  await gotoData(page);
  const t = await page.locator("#content").textContent();
  check(t.includes("1 stored record failed validation") && t.includes("not deleted"), `corrupt record quarantined and reported${t.includes("failed validation") ? "" : ` [page: ${t.slice(0, 200)}]`}`);
  await openLesson(page);
  check(await statusText(page) === "started", "site still works with a corrupt record present");
  await context.close();
}

// ---- 3. storage unavailable -> banner, memory-only mode still works
{
  const context = await freshContext({ initScript: () => { indexedDB.open = () => { throw new DOMException("blocked", "SecurityError"); }; } });
  const page = await context.newPage();
  watch(page, "blocked");
  await openLesson(page);
  const banner = page.locator("#banner");
  check(await banner.isVisible() && (await banner.textContent()).includes("doesn't allow saving"), "blocked storage shows a banner");
  await page.getByRole("button", { name: "Mark lesson as completed" }).click();
  await page.waitForTimeout(100);
  check(await statusText(page) === "completed", "memory-only mode still records within the session");
  await context.close();
}

// ---- 4. data written by a newer version -> untouched, memory-only with a message
{
  const context = await freshContext();
  const page = await context.newPage();
  watch(page, "version");
  await page.goto(BASE);
  await page.locator("#content h1").waitFor();
  await page.evaluate(() => new Promise((resolve) => { // simulate a newer build upgrading the DB (our tab closes on versionchange)
    const r = indexedDB.open("metis", 2);
    r.onupgradeneeded = () => r.result.createObjectStore("future");
    r.onsuccess = () => { r.result.close(); resolve(); };
    r.onblocked = () => resolve();
  }));
  await page.reload();
  await page.locator("#content h1").waitFor();
  check((await page.locator("#banner").textContent()).includes("newer version"), "newer-version data left untouched, with a banner");
  await context.close();
}

console.log("\nPROBLEMS:", problems.length ? "\n" + problems.join("\n") : "none");
await browser.close();
process.exit(problems.length ? 1 : 0);
