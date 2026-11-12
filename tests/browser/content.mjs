// Real-content sweep: every authored lesson, exercise, assessment and specified project renders cleanly.
// No fixtures, no routing. Needs the dev server on 127.0.0.1:8765. Exits 1 on any problem.
import { readFileSync } from "node:fs";
const { chromium } = process.env.PLAYWRIGHT_CORE
  ? await import(`${process.env.PLAYWRIGHT_CORE}/index.mjs`)
  : await import("playwright-core");

const ROOT = new URL("../../", import.meta.url);
const BASE = "http://127.0.0.1:8765/site/";
const cur = JSON.parse(readFileSync(new URL("content/curriculum.json", ROOT)));
const problems = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) problems.push(msg); };

const browser = await chromium.launch({ executablePath: process.env.CHROME ?? "/opt/google/chrome/chrome", args: ["--no-sandbox"] });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
page.on("console", (m) => { if (["error", "warning"].includes(m.type()) || /highlighted/i.test(m.text())) problems.push(`console ${m.type()}: ${m.text()}`); });
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });

const fenceCount = (text) => (text.match(/^```quiz[ \t]*$/gm) ?? []).length;
const lessons = cur.courses.flatMap((c) => c.modules.flatMap((m) => m.lessons)).filter((l) => l.authored);
const modules = cur.courses.flatMap((c) => c.modules).filter((m) => m.assessment);

async function open(hash) {
  await page.goto(BASE + "#/");
  await page.locator("#content h1").waitFor();
  await page.goto(BASE + hash);
  await page.waitForFunction(() => !document.querySelector("#content")?.textContent.includes("Loading exercise"), null, { timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(200);
}

for (const l of lessons) {
  await open(`#/lesson/${l.id}`);
  const text = readFileSync(new URL(`content/lessons/${l.id}.md`, ROOT), "utf8");
  const r = await page.evaluate(() => ({
    h1: document.querySelector("#content h1")?.textContent,
    errors: [...document.querySelectorAll(".block-error")].map((e) => e.textContent),
    quizzes: document.querySelectorAll(".lesson-body .quiz").length,
    exercises: [...document.querySelectorAll(".exercise h3")].map((e) => e.textContent),
    sources: [...document.querySelectorAll("section.card a")].filter((a) => a.href.startsWith("https://")).length,
    progress: !!document.querySelector(".progress-card"),
    backticks: [...document.querySelectorAll(".quiz legend, .quiz .prompt, .quiz label")].some((e) => e.textContent.includes("`")),
  }));
  check(!r.backticks, `${l.id}: quiz text shows inline code, not literal backticks`);
  check(r.h1 === l.title && r.errors.length === 0 && r.quizzes === fenceCount(text) && r.exercises.length === l.exercises.length
    && r.sources >= 1 && r.progress, `${l.id} renders: ${r.quizzes} quizzes, ${r.exercises.length} exercise(s), ${r.sources} source link(s)${r.errors.length ? `, errors: ${r.errors}` : ""}`);
  // Answer every auto-graded quiz with its own key: catches wrong keys and escaping slips in answers.
  const quizzes = [...text.matchAll(/^```quiz[ \t]*\n([\s\S]*?)\n```[ \t]*$/gm)].map((m) => JSON.parse(m[1]));
  const wrong = [];
  for (const [i, q] of quizzes.entries()) {
    if (q.type === "explain") continue;
    const box = page.locator(".lesson-body .quiz").nth(i);
    if (q.type === "choice") await box.locator('input[type="radio"]').nth(q.answer).check();
    else if (q.type === "truefalse") await box.locator(`input[value="${q.answer}"]`).check();
    else await box.locator("textarea").fill(q.answer);
    await box.getByRole("button", { name: "Check" }).click();
    if (!(await box.locator(".feedback").textContent()).includes("Correct.")) wrong.push(q.id);
  }
  check(wrong.length === 0, `${l.id}: every auto-graded answer key is accepted${wrong.length ? ` (rejected: ${wrong})` : ""}`);
  for (const x of l.exercises) {
    await open(`#/exercise/${x}`);
    const t = await page.locator("#content").textContent();
    check(t.includes(x) && !t.includes("couldn't be loaded") && t.includes("Show hint 1 of 3"), `${x} renders`);
  }
}
for (const m of modules) {
  await open(`#/assessment/${m.id}.A`);
  const text = readFileSync(new URL(`content/assessments/${m.id}.A.md`, ROOT), "utf8");
  const n = await page.locator(".lesson-body .quiz").count();
  const aq = [...text.matchAll(/^```quiz[ \t]*\n([\s\S]*?)\n```[ \t]*$/gm)].map((m) => JSON.parse(m[1]));
  const bad = [];
  for (const [i, q] of aq.entries()) {
    if (q.type === "explain") continue;
    const box = page.locator(".lesson-body .quiz").nth(i);
    if (q.type === "choice") await box.locator('input[type="radio"]').nth(q.answer).check();
    else if (q.type === "truefalse") await box.locator(`input[value="${q.answer}"]`).check();
    else await box.locator("textarea").fill(q.answer);
    await box.getByRole("button", { name: "Check" }).click();
    if (!(await box.locator(".feedback").textContent()).includes("Correct.")) bad.push(q.id);
  }
  check(bad.length === 0, `${m.id}.A: every auto-graded answer key is accepted${bad.length ? ` (rejected: ${bad})` : ""}`);
  check(n === fenceCount(text) && (await page.locator(".block-error").count()) === 0, `${m.id}.A renders ${n} questions`);
}
for (const p of cur.projects.filter((x) => x.specified)) {
  await open(`#/project/${p.id}`);
  check((await page.locator(".lesson-body").textContent()).length > 200, `${p.id} specification renders`);
}

console.log("\nPROBLEMS:", problems.length ? "\n" + problems.join("\n") : "none");
await browser.close();
process.exit(problems.length ? 1 : 0);
