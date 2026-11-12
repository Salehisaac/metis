import { h } from "./dom.js";
import { parseHash, href } from "./router.js";
import { buildIndex } from "./curriculum.js";
import { views } from "./views.js";
import { openStore } from "./store.js";
import { createTracker } from "./tracker.js";

const AREAS = [
  ["dashboard", "Dashboard"], ["roadmap", "My roadmap"], ["courses", "Courses"],
  ["exercises", "Exercises"], ["assessments", "Assessments"], ["projects", "Projects"],
  ["revision", "Revision"], ["profile", "Skill profile"], ["history", "History"], ["mentor", "AI mentor"], ["data", "Your data"],
];

const $ = (sel) => document.querySelector(sel);

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

// ---- theme: per-viewer convenience only; storage may be unavailable ----
const THEMES = ["dark", "light", "system"]; // dark is the Transit default; "system" follows the OS
function applyTheme(theme) {
  if (theme === "dark") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
  const btn = $("#theme-toggle");
  btn.textContent = `Theme: ${theme}`;
  btn.setAttribute("aria-label", `Theme: ${theme}. Activate to change.`);
}
function initTheme() {
  let theme = "dark";
  try { theme = localStorage.getItem("metis.theme") || "dark"; } catch { /* storage blocked */ }
  if (!THEMES.includes(theme)) theme = "dark";
  applyTheme(theme);
  $("#theme-toggle").addEventListener("click", () => {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
    try { localStorage.setItem("metis.theme", theme); } catch { /* ignore */ }
    applyTheme(theme);
  });
}

// ---- navigation ----
function renderNav(index) {
  const areas = h("ul", { class: "nav-areas" },
    AREAS.map(([view, label]) => h("li", {}, h("a", { href: href(view), "data-view": view }, label))));
  const tree = h("ul", { class: "nav-tree" }, index.data.courses.map((c) =>
    h("li", {}, h("details", { "data-course": c.id },
      h("summary", {}, `${c.id} · ${c.title}`),
      h("ul", {}, c.modules.map((m) => h("li", {}, h("a", { href: href("module", m.id), "data-id": m.id }, `${m.id} ${m.title}`))))))));
  $("#nav").replaceChildren(h("h2", { class: "sr-only" }, "Main navigation"), areas,
    h("h2", { class: "nav-heading" }, "Curriculum"), tree);
}

function markCurrent(route) {
  // Areas: exact view match; lesson/module/course pages highlight "Courses".
  const areaView = { course: "courses", module: "courses", lesson: "courses", project: "projects",
    exercise: "exercises", assessment: "assessments", review: "revision" }[route.view] ?? route.view;
  document.querySelectorAll("#nav [data-view]").forEach((a) => {
    if (a.dataset.view === areaView) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  const moduleId = route.view === "module" ? route.id : route.view === "lesson" ? route.id?.split(".").slice(0, 2).join(".") : null;
  document.querySelectorAll("#nav [data-id]").forEach((a) => {
    if (a.dataset.id === moduleId) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  if (moduleId) {
    const d = document.querySelector(`#nav details[data-course="${CSS.escape(moduleId.split(".")[0])}"]`);
    if (d) d.open = true;
  }
}

function initMenu() {
  const btn = $("#menu-toggle");
  const sidebar = $("#sidebar");
  const set = (open) => { btn.setAttribute("aria-expanded", String(open)); sidebar.classList.toggle("open", open); };
  btn.addEventListener("click", () => set(btn.getAttribute("aria-expanded") !== "true"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sidebar.classList.contains("open")) { set(false); btn.focus(); } });
  return () => set(false);
}

function initSearch() {
  $("#search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#search-input").value.trim();
    location.hash = q ? `#/search?q=${encodeURIComponent(q)}` : "#/search";
  });
}

// ---- render ----
let renderSeq = 0;
async function render(index, ctx, closeMenu, { focus }) {
  const seq = ++renderSeq;
  const route = parseHash(location.hash);
  const view = views[route.view] ?? views.notfound;
  ctx.progress.reset(); // drop the previous page's progress listeners
  let title, body;
  try {
    ({ title, body } = await view(index, route.id, route.query, ctx));
  } catch (err) { // a bug in a view must not leave a blank or stale page
    console.error(err);
    title = "Something went wrong";
    body = [h("h1", { tabindex: "-1" }, title), h("p", {}, "This page failed to render. Try another page or reload.")];
  }
  if (seq !== renderSeq) return; // a newer navigation finished first
  $("#content").replaceChildren(...body);
  document.title = `${title} · Metis`;
  if (route.view === "search") $("#search-input").value = route.query.q ?? "";
  markCurrent(route);
  // Course colour for the page (lesson/module/exercise/assessment ids start with the course code).
  const course = String(route.id ?? "").split(".")[0];
  if (index.data.courses.some((c) => c.id === course)) $("#main").dataset.course = course;
  else delete $("#main").dataset.course;
  closeMenu();
  if (focus) $("#content h1")?.focus();
}

async function main() {
  // Skip link must not change the hash: "#main" would be routed as a page.
  $(".skip-link").addEventListener("click", (e) => { e.preventDefault(); $("#main").focus(); });
  initTheme();
  initSearch();
  const closeMenu = initMenu();
  try {
    const [curriculum, assessments, profile] = await Promise.all([
      loadJson("../content/curriculum.json"),
      loadJson("../content/learner/assessments.json"),
      loadJson("../content/learner/profile.json"),
    ]);
    const index = buildIndex(curriculum);
    // Content loader for authored files (lessons, exercises, solutions, projects). Returns text.
    const load = async (path) => {
      const res = await fetch(`../content/${path}`);
      if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
      return res.text();
    };
    const store = await openStore();
    const progress = createTracker(store, index);
    const banner = $("#banner");
    const drawBanner = () => {
      banner.hidden = store.persistent && !store.reason;
      banner.textContent = store.persistent && !store.reason ? "" : store.reason;
    };
    progress.always(drawBanner);
    drawBanner();
    // Other tabs may record events: pick them up when this tab becomes visible again.
    document.addEventListener("visibilitychange", async () => {
      if (document.visibilityState !== "visible") return;
      await store.refresh();
      progress.changed();
    });
    const ctx = { assessments, profile, load, progress };
    renderNav(index);
    render(index, ctx, closeMenu, { focus: false });
    window.addEventListener("hashchange", () => render(index, ctx, closeMenu, { focus: true }));
  } catch (err) {
    $("#content").replaceChildren(
      h("h1", {}, "Couldn't load the curriculum"),
      h("p", {}, "Serve the project root with ", h("code", {}, "python3 -m http.server"),
        " and open ", h("code", {}, "http://localhost:8000/site/"), ". Opening the file directly (file://) can't load data."),
      h("p", { class: "muted" }, String(err.message)));
    console.error(err);
  }
}

main();
