// Usage: python3 -m http.server 8765 --bind 127.0.0.1   (from project root), then:
//        npm run -s test:browser -- /tmp/out
// Exits 1 if any problem is found. Uses the installed Chrome (override with CHROME=...); playwright-core is a devDependency.
const { chromium } = process.env.PLAYWRIGHT_CORE
  ? await import(`${process.env.PLAYWRIGHT_CORE}/index.mjs`)
  : await import("playwright-core");
const CHROME = process.env.CHROME ?? "/opt/google/chrome/chrome";
const BASE = "http://127.0.0.1:8765/site/";
const OUT = process.argv[2] ?? (await import("node:os")).tmpdir();
const routes = ["", "#/roadmap", "#/courses", "#/course/PY", "#/module/PY.M02", "#/module/DB.M01", "#/lesson/PY.M01.L01",
  "#/lesson/PY.M07.L04", "#/projects", "#/project/PRJ-04", "#/profile", "#/search?q=transactions", "#/search",
  "#/exercises", "#/mentor", "#/revision", "#/history", "#/data", "#/review/PY.M01.L01", "#/lesson/NOPE", "#/bogus"];
const browser = await chromium.launch({ executablePath: CHROME, args: ["--no-sandbox"] });
const problems = [];
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await ctx.newPage();
page.on("console", (m) => { if (["error", "warning"].includes(m.type())) problems.push(`console ${m.type()}: ${m.text()}`); });
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("requestfailed", (r) => problems.push(`requestfailed: ${r.url()}`));
page.on("response", (r) => { if (r.status() >= 400) problems.push(`HTTP ${r.status()}: ${r.url()}`); });

await page.goto(BASE);
await page.waitForSelector("#content h1");
for (const r of routes) {
  await page.evaluate((h) => { location.hash = h; }, r);
  await page.waitForTimeout(80);
  const info = await page.evaluate(() => ({
    h1: document.querySelector("#content h1")?.textContent, title: document.title,
    focused: document.activeElement?.tagName, current: [...document.querySelectorAll('#nav [aria-current="page"]')].map(a => a.textContent),
  }));
  console.log(`${r || "#/"} | ${info.h1} | focus=${info.focused} | nav=${info.current.join(" + ")}`);
  if (!info.h1) problems.push(`no h1 on ${r}`);
}
// XSS probe through search query
await page.goto(BASE + "#/search?q=" + encodeURIComponent('<img src=x onerror="window.__x=1">'));
await page.waitForTimeout(150);
const xss = await page.evaluate(() => ({ img: !!document.querySelector("#content img"), flag: window.__x === 1, h1: document.querySelector("#content h1").textContent }));
console.log("xss probe:", JSON.stringify(xss)); if (xss.img || xss.flag) problems.push("XSS: markup injected");

// Keyboard: first Tab hits skip link; Enter moves to main
await page.goto(BASE, { waitUntil: "networkidle" }); await page.waitForSelector("#content h1");
await page.keyboard.press("Tab");
const first = await page.evaluate(() => document.activeElement.textContent.trim());
await page.keyboard.press("Enter");
await page.waitForTimeout(100);
const afterSkip = await page.evaluate(() => ({ focus: document.activeElement.id, hash: location.hash, h1: document.querySelector("#content h1").textContent }));
console.log(`keyboard: first tab="${first}", after Enter`, JSON.stringify(afterSkip));
if (first !== "Skip to content" || afterSkip.focus !== "main" || afterSkip.h1 !== "Dashboard") problems.push("skip link not working");

// Search via form + keyboard
await page.fill("#search-input", "pytest"); await page.press("#search-input", "Enter"); await page.waitForTimeout(100);
console.log("search form ->", await page.evaluate(() => location.hash + " | " + document.querySelector("#content h1").textContent + " | results=" + document.querySelectorAll("#content li").length));

// Theme cycle
const themes = [];
for (let i = 0; i < 3; i++) { await page.click("#theme-toggle"); themes.push(await page.evaluate(() => (document.documentElement.dataset.theme || "system") + "/" + getComputedStyle(document.body).backgroundColor)); }
console.log("theme cycle:", themes.join(" -> "));

// Screenshots: light + dark desktop
await page.goto(BASE); await page.waitForSelector("#content h1");
await page.emulateMedia({ colorScheme: "light" }); await page.screenshot({ path: `${OUT}/dash-light.png`, fullPage: true });
await page.emulateMedia({ colorScheme: "dark" }); await page.screenshot({ path: `${OUT}/dash-dark.png`, fullPage: true });
await page.goto(BASE + "#/profile"); await page.waitForTimeout(100); await page.screenshot({ path: `${OUT}/profile-dark.png`, fullPage: true });

// Phone width
const phone = await browser.newContext({ viewport: { width: 375, height: 740 } });
const p2 = await phone.newPage();
p2.on("pageerror", (e) => problems.push(`phone pageerror: ${e.message}`));
for (const r of ["", "#/roadmap", "#/profile", "#/lesson/PY.M02.L03"]) {
  await p2.goto(BASE + r); await p2.waitForSelector("#content h1"); await p2.waitForTimeout(50);
  const ov = await p2.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  console.log(`phone ${r || "#/"}: horizontal overflow=${ov}px`); if (ov > 0) problems.push(`phone overflow ${ov}px on ${r}`);
}
await p2.goto(BASE); await p2.waitForSelector("#content h1");
await p2.screenshot({ path: `${OUT}/phone-dash.png`, fullPage: false });
await p2.click("#menu-toggle");
const menu = await p2.evaluate(() => ({ expanded: document.querySelector("#menu-toggle").getAttribute("aria-expanded"), visible: getComputedStyle(document.querySelector("#sidebar")).display }));
await p2.screenshot({ path: `${OUT}/phone-menu.png` });
await p2.keyboard.press("Escape");
const closed = await p2.evaluate(() => document.querySelector("#menu-toggle").getAttribute("aria-expanded"));
console.log("phone menu:", JSON.stringify(menu), "after Escape expanded=", closed);

// Route map: every sequence item is a keyboard-reachable, labelled station link that opens its page.
{
  const mp = await (await browser.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
  await mp.goto(BASE, { waitUntil: "networkidle" });
  await mp.waitForSelector(".metro .stop");
  const seqLen = JSON.parse(await (await fetch(BASE + "../content/curriculum.json")).text()).sequence.length;
  const n = await mp.locator(".metro .stop").count();
  await mp.locator(".metro .stop").nth(1).focus();
  const label = await mp.evaluate(() => document.activeElement.getAttribute("aria-label"));
  await mp.keyboard.press("Enter");
  await mp.waitForFunction(() => location.hash.startsWith("#/module/"), null, { timeout: 3000 }).catch(() => {});
  const hash = await mp.evaluate(() => location.hash);
  console.log(`metro: ${n} stations (sequence ${seqLen}); 2nd label "${label}" -> ${hash}`);
  if (n !== seqLen || !/lessons completed/.test(label ?? "") || !hash.startsWith("#/module/")) problems.push("metro stations not keyboard-usable");
  await mp.context().close();
}

// Failure cases: data fetch returns 500, then invalid JSON. Expect the error view, no uncaught errors.
for (const [label, fulfil] of [["HTTP 500", { status: 500, body: "boom" }],
  ["invalid JSON", { status: 200, contentType: "application/json", body: "{not json" }]]) {
  const fctx = await browser.newContext();
  const fp = await fctx.newPage();
  const errs = [];
  fp.on("pageerror", (e) => errs.push(e.message));
  await fp.route("**/content/curriculum.json", (r) => r.fulfill(fulfil));
  await fp.goto(BASE); await fp.waitForSelector("#content h1");
  const h1 = await fp.evaluate(() => document.querySelector("#content h1").textContent);
  console.log(`failure ${label}: h1="${h1}" pageerrors=${errs.length}`);
  if (h1 !== "Couldn't load the curriculum" || errs.length) problems.push(`failure case ${label} not handled`);
  await fctx.close();
}

// WCAG 2.4.11: after Shift+Tab back up the roadmap table, focus must not sit under the sticky top bar.
for (const [w, hgt] of [[1280, 800], [375, 740]]) {
  const c = await browser.newContext({ viewport: { width: w, height: hgt } });
  const pg = await c.newPage();
  await pg.goto(BASE + "#/roadmap"); await pg.waitForSelector("#content table");
  const links = await pg.$$("#content table a");
  await links.at(-1).focus();
  for (let i = 0; i < 25; i++) await pg.keyboard.press("Shift+Tab");
  const r = await pg.evaluate(() => {
    const el = document.activeElement.getBoundingClientRect(), bar = document.querySelector(".topbar").getBoundingClientRect();
    return { focusTop: Math.round(el.top), barBottom: Math.round(bar.bottom), text: document.activeElement.textContent.slice(0, 30) };
  });
  console.log(`focus-not-obscured ${w}px:`, JSON.stringify(r));
  if (r.focusTop < r.barBottom) problems.push(`focus hidden under top bar at ${w}px`);
  await c.close();
}

console.log("\nPROBLEMS:", problems.length ? "\n" + problems.join("\n") : "none");
await browser.close();
process.exit(problems.length ? 1 : 0);
