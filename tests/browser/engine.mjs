// Lesson-engine browser checks against tests/fixtures/content (served by request interception, so
// no fixture ever lives in content/). Needs the dev server: python3 -m http.server 8765 --bind 127.0.0.1
// Exits 1 if any problem is found.
import { readFileSync, mkdtempSync, cpSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
const { chromium } = process.env.PLAYWRIGHT_CORE
  ? await import(`${process.env.PLAYWRIGHT_CORE}/index.mjs`)
  : await import("playwright-core");

const ROOT = new URL("../../", import.meta.url);
const FIX = new URL("tests/fixtures/content/", ROOT);
const BASE = "http://127.0.0.1:8765/site/";
const EX = "PY.M01.L01.E1";
const problems = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) problems.push(msg); };

// A real pytest JUnit report for the fixture exercise (scaffold + reference solution), to prove the
// importer accepts what pytest actually writes.
const work = mkdtempSync(join(tmpdir(), "metis-junit-"));
const py = new URL(".venv/bin/python", ROOT).pathname;
execFileSync(py, ["-c", `import sys; sys.path.insert(0, "tools"); import scaffold, pathlib; scaffold.scaffold("${EX}", content=pathlib.Path("tests/fixtures/content"), workspace=pathlib.Path("${work}"))`], { cwd: ROOT.pathname });
cpSync(new URL(`exercises/${EX}/solution/words.py`, FIX), join(work, EX, "words.py"));
execFileSync(py, ["-m", "pytest", "-q", "-p", "no:cacheprovider"], { cwd: join(work, EX) });
const realReport = readFileSync(join(work, EX, "result.xml"));

const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/opt/google/chrome/chrome", args: ["--no-sandbox"] });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
let solutionFetches = 0;
await context.route("**/content/curriculum.json", async (route) => {
  const res = await route.fetch();
  const cur = await res.json();
  const m = cur.courses[0].modules[0];
  m.lessons[0].authored = true;
  m.lessons[0].exercises = [EX];
  m.lessons[0].quizzes = ["q1", "q2", "q3"];
  m.assessment = true;
  cur.courses[0].modules[1].assessment = false; // keep one module without an assessment for the "not found, no fetch" check
  await route.fulfill({ response: res, json: cur });
});
await context.route(/\/content\/(lessons|exercises|assessments)\//, async (route) => {
  const rel = decodeURIComponent(new URL(route.request().url()).pathname.split("/content/")[1]);
  let body;
  try { body = readFileSync(new URL(rel, FIX), "utf8"); } catch { return route.fulfill({ status: 404, body: "not found" }); }
  if (rel === "lessons/PY.M01.L01.md") body += '\n```quiz\n{ "id": "broken", \n```\n'; // malformed block on purpose
  if (rel.endsWith("SOLUTION.md")) solutionFetches++;
  await route.fulfill({ status: 200, body, contentType: rel.endsWith(".json") ? "application/json" : "text/plain" });
});

const page = await context.newPage();
page.on("console", (m) => { if (["error", "warning"].includes(m.type()) || /highlighted/i.test(m.text())) problems.push(`console ${m.type()}: ${m.text()}`); });
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });

// ---- lesson rendering + sanitising
await page.goto(`${BASE}#/lesson/PY.M01.L01`);
await page.waitForSelector(".lesson-body");
await page.waitForSelector(".exercise h3");
const r = await page.evaluate(() => {
  const c = document.querySelector("#content");
  return {
    xss: window.__xss ?? null,
    script: !!c.querySelector("script"), iframe: !!c.querySelector("iframe"),
    imgHandler: [...c.querySelectorAll("img")].some((i) => i.hasAttribute("onerror")),
    jsLink: [...c.querySelectorAll("a")].some((a) => (a.getAttribute("href") ?? "").toLowerCase().startsWith("javascript:")),
    badLinkParsed: [...c.querySelectorAll("a")].some((a) => a.textContent === "bad link"), // probe really became a link
    legend: c.querySelector(".quiz legend")?.textContent, legendHasB: !!c.querySelector(".quiz legend b"),
    pyKeyword: !!c.querySelector(".lesson-body code.language-python .hljs-keyword"),
    goKeyword: !!c.querySelector(".lesson-body code.language-go .hljs-keyword"),
    unknownPlain: !c.querySelector(".lesson-body code.language-unknownlang")?.classList.contains("hljs"),
    brokenBox: c.querySelector(".block-error")?.textContent ?? "",
    objectives: c.querySelectorAll("section.card ul li").length,
    sources: [...c.querySelectorAll("section.card a")].some((a) => a.href.startsWith("https://docs.python.org/")),
    exerciseTitle: c.querySelector(".exercise h3")?.textContent ?? "",
    problem: c.querySelector(".exercise h3 + p")?.textContent ?? "",
  };
});
check(r.badLinkParsed, "javascript: link probe was parsed as a link (so the probe is real)");
check(r.xss === null && !r.script && !r.iframe && !r.imgHandler && !r.jsLink, `hostile Markdown neutralised ${JSON.stringify({ xss: r.xss, script: r.script, iframe: r.iframe, img: r.imgHandler, js: r.jsLink })}`);
check(r.legend?.includes("<b>not bold</b>") && !r.legendHasB, "quiz prompt HTML shown as text");
check(r.pyKeyword && r.goKeyword && r.unknownPlain, "python/go highlighted, unknown language left plain");
check(r.brokenBox.includes("not valid JSON"), "malformed quiz block shows inline error");
check(r.sources, "sources rendered with https link");
check(r.exerciseTitle.includes("FIXTURE: count words") && r.problem.includes("<b>Not bold</b>"), "exercise renders; its HTML shown as text");

// ---- quizzes (choice via keyboard only)
const quizzes = page.locator(".quiz");
await quizzes.nth(0).locator('input[type="radio"]').first().focus();
await page.keyboard.press("Space");
await page.keyboard.press("Tab");
await page.keyboard.press("Enter");
check((await quizzes.nth(0).locator(".feedback").textContent()).includes("Correct."), "choice quiz works by keyboard");
await quizzes.nth(1).getByLabel("True").check();
await quizzes.nth(1).getByRole("button", { name: "Check" }).click();
check((await quizzes.nth(1).locator(".feedback").textContent()).includes("Not quite."), "true/false wrong answer flagged");
await quizzes.nth(2).locator("textarea").fill("[1,2,3]");
await quizzes.nth(2).getByRole("button", { name: "Check" }).click();
check((await quizzes.nth(2).locator(".feedback").textContent()).includes("Correct."), "output quiz honours accept list");
check(!(await page.locator("#content").textContent()).includes("null"), "no stray 'null' text in feedback");
await quizzes.nth(3).getByRole("button", { name: "Show model answer" }).click();
const early = await quizzes.nth(3).locator(".feedback").textContent();
await quizzes.nth(3).locator("textarea").fill("bounds are clamped");
await quizzes.nth(3).getByRole("button", { name: "Show model answer" }).click();
const late = await quizzes.nth(3).locator(".feedback").textContent();
check(!early.includes("Model answer") && late.includes("Model answer"), "explain quiz reveals model only after an answer");

// ---- hints unlock in order, by keyboard; focus moves to each new hint (never lost to <body>)
const ex = page.locator(".exercise");
await ex.getByRole("button", { name: "Show hint 1 of 3" }).focus();
const hintFocus = [];
for (let i = 1; i <= 3; i++) {
  if (i > 1) await ex.getByRole("button", { name: `Show hint ${i} of 3` }).focus();
  await page.keyboard.press("Enter");
  hintFocus.push(await page.evaluate(() => !!document.activeElement.closest(".hints")));
}
check(hintFocus.every(Boolean), `focus lands on each revealed hint ${JSON.stringify(hintFocus)}`);
const hints = await ex.locator(".hints li").allTextContents();
check(hints.length === 3 && hints[0].startsWith("Conceptual") && hints[2].startsWith("Implementation")
  && (await ex.getByRole("button", { name: /Show hint/ }).count()) === 0, "hints unlock one at a time, in order");

// ---- solution fetched only after explicit confirmation
check(solutionFetches === 0, "solution not fetched on page load");
await ex.getByRole("button", { name: "Show reference solution" }).click();
await ex.getByRole("button", { name: "Cancel" }).click();
check(solutionFetches === 0, "solution not fetched after Cancel");
await ex.getByRole("button", { name: "Show reference solution" }).click();
await ex.getByRole("button", { name: "Yes, show it" }).click();
await ex.locator(".solution pre code").waitFor();
check(solutionFetches === 1, "solution fetched once, after confirmation");

// ---- JUnit import
async function importReport(name, buffer) {
  await ex.locator('input[type="file"]').setInputFiles({ name, mimeType: "application/xml", buffer });
  await page.waitForTimeout(150);
  return ex.locator(".feedback").last().textContent();
}
check((await importReport("result.xml", realReport)).includes("All 2 tests passed."), "real pytest report accepted");
const tc = (n, inner = "") => `<testcase classname="test_words" name="${n}">${inner}</testcase>`;
const report = (name, cases) => Buffer.from(`<testsuites><testsuite name="${name}" tests="99" failures="0">${cases}</testsuite></testsuites>`);
check((await importReport("other.xml", report("PY.M09.L01.E1", tc("test_example") + tc("test_empty_and_whitespace"))))
  .includes("not PY.M01.L01.E1"), "report for another exercise rejected");
check((await importReport("cut.xml", report(EX, tc("test_example")))).includes("missing"),
  "report with an expected test removed is rejected (suite counts ignored)");
const withOwn = report(EX, tc("test_example") + tc("test_empty_and_whitespace", "<failure/>") + tc("test_mine"));
const ownOut = await importReport("own.xml", withOwn);
check(ownOut.includes("2 of 3 passed") && ownOut.includes("1 of them your own"), "failing report summarised; learner's extra test counted");
check((await importReport("x.xml", Buffer.from("<testsuite"))).includes("Not a valid XML"), "garbage XML rejected");
const xxe = Buffer.from(`<?xml version="1.0"?><!DOCTYPE t [<!ENTITY x SYSTEM "file:///etc/passwd">]><testsuite name="&x;" tests="1"/>`);
const xxeOut = await importReport("xxe.xml", xxe);
check(!xxeOut.includes("root:"), "external entities not resolved");

// ---- other engine routes
for (const [hash, expect] of [[`#/exercise/${EX}`, "FIXTURE: count words"], ["#/assessment/PY.M01.A", "FIXTURE module assessment"],
  ["#/exercises", EX], ["#/assessments", "PY.M01.A"], ["#/project/PRJ-01", "Functional requirements"], ["#/module/PY.M01", "PY.M01.A"]]) {
  await page.goto(BASE + hash);
  await page.waitForFunction((t) => document.querySelector("#content")?.textContent.includes(t), expect, { timeout: 3000 }).catch(() => {});
  check((await page.locator("#content").textContent()).includes(expect), `${hash} shows "${expect}"`);
}
await page.goto(`${BASE}#/assessment/PY.M02.A`);
await page.waitForTimeout(150);
check((await page.locator("#content h1").textContent()) === "Not found", "unauthored assessment is not found (no fetch)");

// ---- failure paths: each shows its error box, with no uncaught errors
for (const [label, hash, match, fulfil, expectText] of [
  ["lesson HTTP 500", "#/lesson/PY.M01.L01", /\/lessons\/PY\.M01\.L01\.md$/, { status: 500, body: "x" }, "This lesson couldn't be loaded."],
  ["lesson bad front matter", "#/lesson/PY.M01.L01", /\/lessons\/PY\.M01\.L01\.md$/, { status: 200, body: "---\n{bad json\n---\nbody" }, "This lesson couldn't be loaded."],
  ["exercise.json invalid", `#/exercise/${EX}`, /exercise\.json$/, { status: 200, body: "{nope" }, `Exercise ${EX} couldn't be loaded.`],
  ["SOLUTION.md 500", `#/exercise/${EX}`, /SOLUTION\.md$/, { status: 500, body: "x" }, "The solution couldn't be loaded."],
]) {
  const fp = await context.newPage();
  const errs = [];
  fp.on("pageerror", (err) => errs.push(err.message));
  await fp.route(match, (rt) => rt.fulfill(fulfil));
  await fp.goto(BASE + hash);
  if (label.startsWith("SOLUTION")) {
    await fp.getByRole("button", { name: "Show reference solution" }).click();
    await fp.getByRole("button", { name: "Yes, show it" }).click();
  }
  const found = await fp.waitForFunction((t) => document.querySelector("#content")?.textContent.includes(t), expectText, { timeout: 3000 })
    .then(() => true, () => false);
  check(found && errs.length === 0, `failure path: ${label} shows its error box`);
  await fp.close();
}

// ---- phone width: a full lesson must not scroll sideways (code blocks scroll inside themselves)
await page.setViewportSize({ width: 375, height: 740 });
await page.goto(`${BASE}#/lesson/PY.M01.L01`);
await page.waitForSelector(".exercise h3");
const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
check(overflow <= 0, `no horizontal overflow on a full lesson at 375px (got ${overflow}px)`);

console.log("\nPROBLEMS:", problems.length ? "\n" + problems.join("\n") : "none");
await browser.close();
process.exit(problems.length ? 1 : 0);
