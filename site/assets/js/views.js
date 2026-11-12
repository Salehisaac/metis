import { h } from "./dom.js";
import { href } from "./router.js";
import { get, breadcrumbs, lessonNeighbors, search, totalHours, weakCompetencies } from "./curriculum.js";
import { parseFrontMatter } from "./content.js";
import { renderMarkdown } from "./render.js";
import { quizBlock, exerciseBlock, errorBox } from "./blocks.js";
import { RULES } from "./progress.js";
import { exportPayload, parseImport, MAX_IMPORT_BYTES } from "./events.js";
import { MODES, buildPrompt } from "./mentor.js";
import { renderMetro } from "./metro.js";

const mentorHref = (params) => `#/mentor?${new URLSearchParams(params)}`;

const VIEW_FOR_KIND = { course: "course", module: "module", lesson: "lesson", project: "project" };

const link = (index, id) => {
  const e = get(index, id);
  return e ? h("a", { href: href(VIEW_FOR_KIND[e.kind], id) }, `${id} · ${e.item.title}`) : h("span", {}, id);
};
const badge = (status, provisional) =>
  h("span", { class: `badge badge-${status.toLowerCase()}` }, status, provisional ? " (provisional)" : "");
const STATUS_TEXT = { NOT_STARTED: "not started", STARTED: "started", COMPLETED: "completed", COMPETENT: "competent", MASTERED: "mastered" };
const statusBadge = (s) => h("span", { class: `badge status-${s.toLowerCase()}` }, STATUS_TEXT[s]);
const empty = (text) => h("p", { class: "empty" }, text);
const card = (title, ...body) => h("section", { class: "card" }, h("h2", {}, title), ...body);
const list = (items) => h("ul", {}, items.map((x) => h("li", {}, x)));
// Flatten and drop null/false: app.js passes body to replaceChildren, which would stringify arrays and nulls.
const page = (title, ...body) => ({ title, body: [h("h1", { tabindex: "-1" }, title), ...body].flat(Infinity).filter((x) => x != null && x !== false) });
const notFound = (what) => page("Not found", empty(`No ${what} with that ID exists in the curriculum.`));
const joinLinks = (index, ids) => ids.length ? ids.flatMap((a, i) => (i ? [", ", link(index, a)] : [link(index, a)])) : "none";
const day = (iso) => (iso ? iso.slice(0, 10) : "—");
const when = (iso) => new Date(iso).toLocaleString();
const NO_CONTENT = "None yet. Content is written module by module in Phase 7.";
const FENCE = /^```(quiz|exercise)[ \t]*\n([\s\S]*?)\n```[ \t]*$/gm; // same as tools/validate.py

const mount = (ctx, itemId) => ({ kind, raw }) => (kind === "quiz"
  ? quizBlock(raw, ctx.progress.hooksFor(itemId))
  : exerciseBlock(raw.trim(), ctx.load, ctx.progress.hooksFor(itemId)));

function sources(items) {
  return card("Sources", h("ul", {}, items.map((s) => h("li", {},
    String(s.url).startsWith("https://") ? h("a", { href: s.url, rel: "noopener noreferrer" }, s.title) : s.title,
    h("span", { class: "muted" }, ` · version ${s.version} · verified ${s.verified}`)))));
}

function bookmarkButton(ctx, itemId) {
  const btn = h("button", { class: "btn", type: "button" });
  const sync = () => {
    const on = ctx.progress.state().bookmarks.has(itemId);
    btn.setAttribute("aria-pressed", String(on));
    btn.textContent = on ? "★ Bookmarked" : "☆ Bookmark";
  };
  btn.addEventListener("click", () => ctx.progress.record("bookmark", itemId, { on: !ctx.progress.state().bookmarks.has(itemId) }));
  ctx.progress.on(sync);
  sync();
  return btn;
}

export function describeEvent(e) {
  switch (e.type) {
    case "lesson_started": return "Started lesson";
    case "lesson_completed": return "Marked lesson completed";
    case "quiz_answer": return `Answered quiz ${e.item.split("#")[1]} ${e.correct ? "correctly" : "incorrectly"}`;
    case "review_done": return `Review: ${e.correct} of ${e.total} correct`;
    case "exercise_result": return e.passed ? `Exercise passed (${e.tests} tests)` : `Exercise: ${e.tests - e.failures - e.errors - e.skipped} of ${e.tests} tests passed`;
    case "hint_viewed": return `Viewed hint ${e.n}`;
    case "solution_viewed": return "Viewed reference solution";
    case "bookmark": return e.on ? "Bookmarked" : "Removed bookmark";
    default: return e.type;
  }
}
const eventItem = (index, e) => { // compact: the id only, linked when it's a known item
  const id = e.item.split("#")[0];
  const x = get(index, id);
  return x ? h("a", { href: href(VIEW_FOR_KIND[x.kind], id), title: x.item.title }, id) : id;
};

export function crumbs(index, id) {
  const items = [h("li", {}, h("a", { href: "#/courses" }, "Courses"))];
  const trail = breadcrumbs(index, id);
  trail.forEach((b, i) => {
    const last = i === trail.length - 1;
    items.push(h("li", {}, last
      ? h("span", { "aria-current": "page" }, b.title)
      : h("a", { href: href(VIEW_FOR_KIND[b.kind], b.id) }, b.title)));
  });
  return h("nav", { class: "crumbs", "aria-label": "Breadcrumb" }, h("ol", {}, items));
}

function authoredExercises(index) {
  return index.lessonOrder.flatMap((lid) => (get(index, lid).item.exercises ?? []).map((xid) => ({ id: xid, lesson: lid })));
}
function modulesWithAssessment(index) {
  return index.data.sequence.filter((id) => get(index, id).kind === "module" && get(index, id).item.assessment);
}
function moduleProgress(index, st, modId) {
  const lessons = get(index, modId).item.lessons;
  return { done: lessons.filter((l) => st.lessons.get(l.id)?.completedAt).length, total: lessons.length };
}

function assessmentSummary(ctx, aid) {
  const first = new Map();
  for (const e of ctx.progress.store.events) {
    if (e.type === "quiz_answer" && e.item.startsWith(`${aid}#`) && !first.has(e.item)) first.set(e.item, e.correct);
  }
  return first.size
    ? h("p", { class: "muted" }, `First attempts: ${[...first.values()].filter(Boolean).length} of ${first.size} answered questions correct.`)
    : h("p", { class: "muted" }, "Not attempted yet.");
}

// Lesson progress panel: status, evidence, actions. Re-renders itself on progress changes.
function lessonProgress(index, ctx, lesson) {
  const box = h("section", { class: "card progress-card", "aria-labelledby": "progress-h" });
  const draw = () => {
    const s = ctx.progress.state().lessons.get(lesson.id);
    const ev = s.evidence;
    const lines = [];
    for (const x of ev.exercises) {
      lines.push(x.passedAt
        ? `${x.id}: passed independently on ${day(x.passedAt)}${x.hints ? ` (used ${x.hints} hint${x.hints > 1 ? "s" : ""})` : ""}.`
        : x.solutionAt
          ? `${x.id}: reference solution viewed before a pass, so a later pass doesn't count as independent.`
          : `${x.id}: not passed yet${x.attempts ? ` (${x.attempts} result${x.attempts > 1 ? "s" : ""} imported)` : ""}.`);
    }
    if (ev.quizzes.length) lines.push(`Quizzes: ${ev.firstCorrect} of ${ev.quizzes.length} correct on the first attempt (${ev.quizzes.filter((q) => q.answeredAt).length} answered).`);
    if (!ev.enoughEvidence) lines.push("This lesson doesn't have enough auto-graded work to reach COMPETENT on the platform; that needs a mentor session.");
    const complete = h("button", { class: "btn", type: "button" }, "Mark lesson as completed");
    complete.addEventListener("click", () => ctx.progress.record("lesson_completed", lesson.id));
    box.replaceChildren(...[ // replaceChildren prints null as "null": filter it out
      h("h2", { id: "progress-h" }, "Your progress"),
      h("p", {}, statusBadge(s.status),
        s.masteredAt ? ` since ${day(s.masteredAt)}` : s.competentAt ? ` since ${day(s.competentAt)}` : s.completedAt ? ` on ${day(s.completedAt)}` : ""),
      lines.length ? list(lines) : null,
      s.review && s.review.reviewable
        ? (s.review.nextAt <= new Date().toISOString()
          ? h("p", {}, "A review is due. ", h("a", { href: href("review", lesson.id) }, "Review now"))
          : h("p", {}, `Next review: ${day(s.review.nextAt)}.`))
        : null,
      h("div", { class: "actions" }, s.completedAt ? null : complete, " ", bookmarkButton(ctx, lesson.id))].filter(Boolean));
  };
  ctx.progress.on(draw);
  draw();
  return box;
}

export const views = {
  dashboard(index, _id, _q, ctx) {
    const { data } = index;
    const st = ctx.progress.state();
    const asm = ctx.assessments.assessments.at(-1);
    const weak = asm ? weakCompetencies(asm) : [];
    const nextLesson = st.nextLesson;
    const here = nextLesson ? get(index, nextLesson) : null;
    const hereModule = here ? get(index, here.parents[1]).item : null;
    const hereCourse = here ? get(index, here.parents[0]).item : null;
    const projectId = data.sequence.find((id) => get(index, id).kind === "project");
    const before = data.sequence.slice(0, data.sequence.indexOf(projectId)).filter((id) => get(index, id).kind === "module");
    const beforeLessons = before.flatMap((m) => get(index, m).item.lessons.map((l) => l.id));
    const lastExport = ctx.progress.store.meta.lastExportAt;
    const needsBackup = st.count > 0 && (!lastExport || Date.now() - Date.parse(lastExport) > 7 * 86_400_000);
    const moduleCount = data.courses.reduce((n, c) => n + c.modules.length, 0);

    // Real activity for the last 7 local days.
    const dayKey = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    const active = new Set(ctx.progress.store.events.map((e) => dayKey(new Date(e.at))));
    const week = [...Array(7)].map((_, i) => { const d = new Date(); d.setDate(d.getDate() - (6 - i)); return d; });

    const scored = asm ? asm.competencies.filter((c) => ["A", "B", "C", "D"].some((k) => c[k] !== null)) : [];
    const heat = (v) => (v === null
      ? h("td", { class: "na" }, h("span", { class: "sr-only" }, "not assessed"))
      : h("td", { class: `lvl lvl-${v}` }, h("span", { class: "sr-only" }, `${v} of 4`)));

    return {
      title: "Dashboard",
      body: [
        h("h1", { tabindex: "-1", class: "sr-only" }, "Dashboard"),
        h("section", { class: "hero", "aria-labelledby": "route-h" },
          h("h2", { id: "route-h" }, "Your route to backend engineer"),
          h("p", { class: "muted" }, `${data.courses.length} lines, ${moduleCount} stations and ${data.projects.length} projects.`,
            hereCourse ? ` You're on the ${hereCourse.title} line.` : " Every defined lesson is completed."),
          h("div", { class: "metro-wrap", tabindex: "-1" }, renderMetro(index, st))),
        needsBackup ? h("p", { class: "note" }, lastExport ? `Last backup ${day(lastExport)}. ` : "You haven't backed up your progress yet. ",
          h("a", { href: "#/data" }, "Export it now"), " (browser storage can be cleared).") : null,
        here ? h("section", { class: "next-stop", "data-course": here.parents[0], "aria-labelledby": "next-h" },
          h("div", {},
            h("h2", { id: "next-h" }, `Next stop: ${hereModule.title}`),
            h("p", {}, link(index, nextLesson))),
          h("a", { class: "cta", href: href("lesson", nextLesson) }, "Open lesson"))
          : h("section", { class: "next-stop" }, h("h2", {}, "All defined lessons are completed.")),
        h("div", { class: "grid" },
          card("Progress",
            h("p", { class: "big" }, h("strong", {}, `${st.totals.completed} of ${st.totals.defined}`), " defined lessons completed"),
            h("p", {}, `${st.totals.competent} competent · ${st.totals.mastered} mastered`),
            index.data.courses.some((c) => c.modules.some((m) => m.lessons.length === 0))
              ? h("p", { class: "muted" }, "Some modules don't have lessons defined yet; they get them when they start.")
              : null,
            st.count ? null : empty("No activity recorded yet.")),
          card(asm ? `Skills from ${asm.id}` : "Skills",
            asm ? [
              h("table", { class: "heat" },
                h("caption", { class: "sr-only" }, "Assessment scores 0 to 4 per dimension"),
                h("thead", {}, h("tr", {}, h("td"), ["A", "B", "C", "D"].map((k) => h("th", { scope: "col" }, k)))),
                h("tbody", {}, scored.map((c) => h("tr", {}, h("th", { scope: "row" }, c.name), ["A", "B", "C", "D"].map((k) => heat(c[k])))))),
              h("p", {}, h("a", { href: "#/profile" }, "View skill profile")),
            ] : empty("No assessment recorded.")),
          card("This week",
            h("ol", { class: "week" }, week.map((d) => {
              const on = active.has(dayKey(d));
              const name = d.toLocaleDateString(undefined, { weekday: "short" });
              return h("li", { class: on ? "on" : null }, h("span", { "aria-hidden": "true" }, name.slice(0, 2)),
                h("span", { class: "sr-only" }, `${name}: ${on ? "studied" : "no activity"}`));
            })),
            st.due.length ? h("p", {}, `${st.due.length} review${st.due.length > 1 ? "s" : ""} due. `, h("a", { href: "#/revision" }, "Open revision center"))
              : h("p", { class: "muted" }, st.upcoming.length ? `Nothing due. Next review: ${day(st.lessons.get(st.upcoming[0]).review.nextAt)}.` : "Nothing to review yet.")),
          card("Weak spots",
            weak.length ? h("ul", {}, weak.map((c) => h("li", {}, c.name, h("span", { class: "muted" }, ` · ${c.evidence}`)))) : empty("None recorded.")),
          card("Next project",
            projectId ? [h("p", {}, link(index, projectId)),
              h("p", { class: "muted" }, `${beforeLessons.filter((l) => st.lessons.get(l)?.completedAt).length} of ${beforeLessons.length} defined lessons before it completed.`)]
              : empty("No projects.")),
          card("Bookmarks",
            st.bookmarks.size ? list([...st.bookmarks].map((id) => link(index, id))) : empty("No bookmarks yet.")),
          card("Recent activity",
            st.recent.length ? [list(st.recent.slice(0, 5).map((e) => [describeEvent(e), " · ", eventItem(index, e)])),
              h("p", {}, h("a", { href: "#/history" }, "Full history"))] : empty("Nothing yet."))),
      ].flat(Infinity).filter((x) => x != null && x !== false),
    };
  },

  roadmap(index, _id, _q, ctx) {
    const st = ctx.progress.state();
    const { modules, projects, total } = totalHours(index);
    let cumulative = 0;
    const rows = index.data.sequence.map((id, i) => {
      const { kind, item } = get(index, id);
      cumulative += item.hours;
      const p = kind === "module" ? moduleProgress(index, st, id) : null;
      return h("tr", {},
        h("td", {}, String(i + 1)),
        h("td", {}, link(index, id)),
        h("td", {}, kind === "project" ? h("span", { class: "badge badge-project" }, "PROJECT") : badge(item.status, item.provisional)),
        h("td", { class: "num" }, String(item.hours)),
        h("td", { class: "num" }, String(cumulative)),
        h("td", { class: "num" }, p && p.total ? `${p.done}/${p.total}` : "—"),
        h("td", {}, (item.prereqs ?? item.after).join(", ") || "none"));
    });
    return page("My learning roadmap",
      h("p", {}, `Estimated ${total} h (${modules} h modules + ${projects} h projects). `,
        `At 5–10 h/week that is about ${Math.ceil(total / 10)}–${Math.ceil(total / 5)} weeks. These are estimates, not promises.`),
      h("div", { class: "table-wrap" }, h("table", {},
        h("caption", {}, "Approved learning sequence (Done = lessons completed / defined)"),
        h("thead", {}, h("tr", {}, ["#", "Item", "Status", "Hours", "Cumulative h", "Done", "Requires"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, rows))));
  },

  courses(index) {
    return page("Courses", h("div", { class: "grid" }, index.data.courses.map((c) =>
      h("section", { class: "card" },
        h("h2", {}, h("a", { href: href("course", c.id) }, `${c.id} · ${c.title}`)),
        h("p", {}, badge(c.status)),
        h("p", {}, c.reason),
        h("p", { class: "muted" }, `${c.modules.length} modules · ${c.modules.reduce((s, m) => s + m.hours, 0)} h estimated`)))));
  },

  course(index, id) {
    const e = get(index, id);
    if (e?.kind !== "course") return notFound("course");
    const c = e.item;
    return page(`${c.id} · ${c.title}`, crumbs(index, id), h("p", {}, badge(c.status), " ", c.reason),
      h("ol", { class: "list" }, c.modules.map((m) => h("li", {},
        link(index, m.id), " ", badge(m.status, m.provisional), h("span", { class: "muted" }, ` · ${m.hours} h`)))));
  },

  module(index, id, _q, ctx) {
    const e = get(index, id);
    if (e?.kind !== "module") return notFound("module");
    const m = e.item;
    const st = ctx.progress.state();
    const p = moduleProgress(index, st, id);
    return page(`${m.id} · ${m.title}`, crumbs(index, id),
      h("p", {}, badge(m.status, m.provisional), h("span", { class: "muted" }, ` · ${m.hours} h estimated`),
        p.total ? h("span", { class: "muted" }, ` · ${p.done} of ${p.total} lessons completed`) : null),
      h("div", { class: "actions" }, bookmarkButton(ctx, id)),
      m.provisional ? h("p", { class: "note" }, "Not assessed yet: a short placement check at the start decides SKIP, REVIEW or LEARN.") : null,
      card("Learning outcomes", list(m.outcomes)),
      card("Prerequisites", m.prereqs.length ? list(m.prereqs.map((x) => link(index, x))) : empty("None.")),
      card("Lessons", m.lessons.length
        ? h("ol", { class: "list" }, m.lessons.map((l) => h("li", {}, link(index, l.id), " ",
          l.authored ? statusBadge(st.lessons.get(l.id).status) : h("span", { class: "muted" }, "· not written yet"))))
        : empty("Lessons get IDs when this module starts, so they can adapt to how earlier modules went.")),
      card("Module assessment", m.assessment
        ? [h("p", {}, h("a", { href: href("assessment", `${m.id}.A`) }, `${m.id}.A`)), assessmentSummary(ctx, `${m.id}.A`)]
        : empty("Not written yet.")));
  },

  async lesson(index, id, _q, ctx) {
    const e = get(index, id);
    if (e?.kind !== "lesson") return notFound("lesson");
    const mod = get(index, e.parents[1]).item;
    const { prev, next } = lessonNeighbors(index, id);
    const pager = h("nav", { class: "pager", "aria-label": "Lesson navigation" },
      prev ? h("a", { href: href("lesson", prev), rel: "prev" }, "← ", get(index, prev).item.title) : h("span"),
      next ? h("a", { href: href("lesson", next), rel: "next" }, get(index, next).item.title, " →") : h("span"));

    if (!e.item.authored) {
      return page(e.item.title, crumbs(index, id),
        h("dl", { class: "meta" },
          h("dt", {}, "Lesson ID"), h("dd", {}, h("code", {}, id)),
          h("dt", {}, "Module"), h("dd", {}, link(index, mod.id)),
          h("dt", {}, "Module prerequisites"), h("dd", {}, joinLinks(index, mod.prereqs))),
        h("p", { class: "note" }, "This lesson isn't written yet. Content is written module by module in Phase 7."),
        h("div", { class: "actions" }, bookmarkButton(ctx, id)),
        pager);
    }
    let meta, body;
    try {
      ({ meta, body } = parseFrontMatter(await ctx.load(`lessons/${id}.md`)));
    } catch {
      return page(e.item.title, crumbs(index, id), errorBox("This lesson couldn't be loaded."), pager);
    }
    if (!ctx.progress.state().lessons.get(id).started) ctx.progress.record("lesson_started", id); // once per lesson
    return page(meta.title, crumbs(index, id),
      h("dl", { class: "meta" },
        h("dt", {}, "Lesson ID"), h("dd", {}, h("code", {}, id)),
        h("dt", {}, "Difficulty"), h("dd", {}, meta.difficulty),
        h("dt", {}, "Estimated time"), h("dd", {}, `${meta.minutes} min`),
        h("dt", {}, "Prerequisites"), h("dd", {}, joinLinks(index, meta.prerequisites)),
        h("dt", {}, "Module"), h("dd", {}, link(index, mod.id))),
      lessonProgress(index, ctx, e.item),
      card("Learning objectives", list(meta.objectives)),
      card("Why this matters", h("p", {}, meta.why), h("h3", {}, "Real-world applications"), list(meta.applications)),
      h("p", {}, h("a", { href: mentorHref({ mode: "explain", lesson: id }) }, "Ask the AI mentor about this lesson")),
      h("article", { class: "lesson-body" }, renderMarkdown(body, mount(ctx, id))),
      sources(meta.sources),
      pager);
  },

  async review(index, id, _q, ctx) {
    const e = get(index, id);
    if (e?.kind !== "lesson" || !e.item.authored) return notFound("lesson");
    const s = ctx.progress.state().lessons.get(id);
    if (!s.review?.reviewable) {
      return page(`Review: ${e.item.title}`, crumbs(index, id),
        empty(s.competentAt ? "This lesson has too few auto-graded questions for a platform review." : "Reviews start once the lesson is COMPETENT."),
        h("p", {}, link(index, id)));
    }
    if (s.review.nextAt > new Date().toISOString()) {
      return page(`Review: ${e.item.title}`, crumbs(index, id),
        empty(`Not due until ${day(s.review.nextAt)}. Reviewing early wouldn't count, so come back then.`), h("p", {}, link(index, id)));
    }
    let body;
    try { ({ body } = parseFrontMatter(await ctx.load(`lessons/${id}.md`))); } catch {
      return page(`Review: ${e.item.title}`, errorBox("This lesson couldn't be loaded."));
    }
    const wanted = new Set(e.item.quizzes);
    const raws = [...body.matchAll(FENCE)].filter(([, kind, raw]) => {
      if (kind !== "quiz") return false;
      try { return wanted.has(JSON.parse(raw).id); } catch { return false; }
    }).map(([, , raw]) => raw);
    const first = new Map();
    const result = h("div", { class: "feedback", "aria-live": "polite" });
    let recorded = false;
    let blocks = [];
    const onAnswer = async (q, correct) => {
      if (!first.has(q.id)) first.set(q.id, correct); // only the first answer to each question counts
      if (recorded || first.size < raws.length) return;
      recorded = true;
      const n = [...first.values()].filter(Boolean).length;
      await ctx.progress.record("review_done", id, { correct: n, total: raws.length });
      blocks.forEach((b) => b.reveal?.());
      const after = ctx.progress.state().lessons.get(id);
      result.replaceChildren(h("p", {}, `Review recorded: ${n} of ${raws.length} correct on the first try. `,
        `Status: ${STATUS_TEXT[after.status]}. Next review: ${day(after.review.nextAt)}.`));
    };
    return page(`Review: ${e.item.title}`, crumbs(index, id),
      h("p", { class: "note" }, "Answer from memory, without the lesson open. Only your first answer to each question counts; feedback appears at the end."),
      (blocks = raws.map((raw) => quizBlock(raw, { onAnswer, deferFeedback: true }))),
      result);
  },

  revision(index, _id, _q, ctx) {
    const st = ctx.progress.state();
    const needEvidence = [...st.lessons.values()].filter((l) => l.completedAt && !l.competentAt);
    return page("Revision center",
      h("p", { class: "muted" }, `Reviews follow a spaced schedule (${RULES.intervalsDays.join(", ")} days; a failed review restarts it). `,
        "It's a heuristic to fight forgetting, not a guarantee of retention."),
      card("Due now", st.due.length
        ? list(st.due.map((id) => [link(index, id), " · ", h("a", { href: href("review", id) }, "Review now")]))
        : empty("Nothing due.")),
      card("Coming up", st.upcoming.length
        ? list(st.upcoming.map((id) => [link(index, id), ` · ${day(st.lessons.get(id).review.nextAt)}`]))
        : empty("Nothing scheduled. Reviews start once a lesson is COMPETENT.")),
      card("Completed, but no evidence yet", needEvidence.length
        ? list(needEvidence.map((l) => [link(index, l.id), h("span", { class: "muted" }, " · pass its exercises and quizzes to show competence")]))
        : empty("None.")));
  },

  history(index, _id, _q, ctx) {
    const events = [...ctx.progress.store.events].reverse();
    const shown = events.slice(0, 500);
    return page("Learning history", events.length
      ? [h("div", { class: "table-wrap" }, h("table", {},
        h("caption", {}, `${events.length} recorded events, newest first${events.length > shown.length ? " (latest 500 shown)" : ""}`),
        h("thead", {}, h("tr", {}, ["When", "Activity", "Item"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, shown.map((e) => h("tr", {}, h("td", {}, when(e.at)), h("td", {}, describeEvent(e)), h("td", {}, eventItem(index, e)))))))]
      : empty("Nothing recorded yet. Activity in lessons, quizzes and exercises shows up here."));
  },

  data(_index, _id, _q, ctx) {
    const store = ctx.progress.store;
    const status = h("p", {});
    const persistedLine = h("p", { class: "muted" });
    const drawStatus = () => status.replaceChildren(store.persistent
      ? `Saved in this browser (IndexedDB): ${store.events.length} events.`
      : h("strong", {}, store.reason || "Not saving."));
    drawStatus();
    navigator.storage?.persisted?.().then((p) => persistedLine.replaceChildren(p
      ? "The browser has granted persistent storage, so it won't evict this data on its own."
      : "Persistent storage isn't granted: the browser may clear this data under storage pressure. Export regularly."))
      .catch(() => {});

    const download = (obj, name) => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" }));
      const a = h("a", { href: url, download: name });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    const lastExport = h("p", {});
    const drawExport = () => lastExport.replaceChildren(store.meta.lastExportAt ? `Last export: ${when(store.meta.lastExportAt)}.` : "Never exported.");
    drawExport();
    const exportBtn = h("button", { class: "btn", type: "button" }, "Export progress (JSON)");
    exportBtn.addEventListener("click", async () => {
      await store.refresh(); // another tab may have recorded events since this page loaded
      const now = new Date().toISOString();
      download(exportPayload(store.events, now), `metis-progress-${now.slice(0, 10)}.json`);
      await store.setMeta("lastExportAt", now);
      drawExport();
      ctx.progress.changed();
    });

    const importOut = h("div", { class: "feedback", "aria-live": "polite" });
    const fileInput = h("input", { type: "file", id: "import-file", accept: ".json,application/json" });
    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (!file) return;
      if (file.size > MAX_IMPORT_BYTES) { importOut.replaceChildren(h("p", { class: "bad" }, "File is too large.")); return; }
      file.text().then(async (text) => {
        await store.refresh();
        const r = parseImport(text, new Date().toISOString());
        if (!r.ok) {
          importOut.replaceChildren(h("p", { class: "bad" }, "Import rejected; nothing was changed."), list(r.errors));
          return;
        }
        const known = new Set(store.events.map((e) => e.id));
        const fresh = r.events.filter((e) => !known.has(e.id)).length;
        const confirm = h("button", { class: "btn", type: "button" }, `Import ${fresh} new event${fresh === 1 ? "" : "s"}`);
        confirm.addEventListener("click", async () => {
          try {
            const res = await store.importEvents(r.events);
            importOut.replaceChildren(h("p", { class: "ok" }, `Imported ${res.added} events (${res.skipped} already present).`));
            drawStatus();
            ctx.progress.changed();
          } catch {
            importOut.replaceChildren(h("p", { class: "bad" }, "Import failed; nothing was changed."));
          }
        });
        importOut.replaceChildren(h("p", {}, `${r.events.length} valid events found, ${fresh} new. Existing progress is kept; duplicates are skipped.`),
          fresh ? confirm : h("p", {}, "Nothing new to import."));
      });
    });

    let quarantine = null;
    if (store.quarantined.length) {
      const btn = h("button", { class: "btn", type: "button" }, "Download them");
      btn.addEventListener("click", () => download(store.quarantined, "metis-quarantined.json"));
      quarantine = card("Unreadable records",
        h("p", {}, `${store.quarantined.length} stored record${store.quarantined.length > 1 ? "s" : ""} failed validation and are ignored. They were not deleted.`), btn);
    }

    return page("Your data",
      card("Storage", status, persistedLine),
      quarantine,
      card("Back up", lastExport, exportBtn,
        h("p", { class: "muted" }, "Export after study sessions and keep the file somewhere safe (e.g. a synced folder). ",
          "Browser data can be cleared by the browser or by clearing site data. The export contains learning events only: no passwords, keys or answer text.")),
      card("Restore or merge", h("label", { for: "import-file" }, "Import a progress export: "), fileInput, importOut));
  },

  exercises(index) {
    const items = authoredExercises(index);
    return page("Coding exercises", items.length
      ? h("ol", { class: "list" }, items.map((x) => h("li", {},
        h("a", { href: href("exercise", x.id) }, x.id), h("span", { class: "muted" }, " · in "), link(index, x.lesson))))
      : empty(NO_CONTENT));
  },

  exercise(index, id, _q, ctx) {
    const x = authoredExercises(index).find((e) => e.id === id);
    if (!x) return notFound("exercise");
    return page(`Exercise ${id}`, crumbs(index, x.lesson), exerciseBlock(id, ctx.load, ctx.progress.hooksFor(x.lesson)),
      h("p", {}, "Part of lesson ", link(index, x.lesson)));
  },

  assessments(index) {
    const mods = modulesWithAssessment(index);
    return page("Assessments", mods.length
      ? h("ol", { class: "list" }, mods.map((m) => h("li", {},
        h("a", { href: href("assessment", `${m}.A`) }, `${m}.A`), h("span", { class: "muted" }, " · "), link(index, m))))
      : empty(NO_CONTENT));
  },

  async assessment(index, id, _q, ctx) {
    const modId = String(id ?? "").replace(/\.A$/, "");
    const e = get(index, modId);
    if (e?.kind !== "module" || !e.item.assessment || id !== `${modId}.A`) return notFound("assessment");
    try {
      const { meta, body } = parseFrontMatter(await ctx.load(`assessments/${id}.md`));
      return page(meta.title, crumbs(index, modId),
        h("p", { class: "muted" }, `${id} · about ${meta.minutes} min · answer on your own first; no AI.`),
        h("article", { class: "lesson-body" }, renderMarkdown(body, mount(ctx, id))));
    } catch {
      return page(`Assessment ${id}`, crumbs(index, modId), errorBox("This assessment couldn't be loaded."));
    }
  },

  projects(index) {
    return page("Projects", h("ol", { class: "list" }, index.data.projects.map((p) => h("li", {},
      link(index, p.id), h("span", { class: "muted" }, ` · after ${p.after.join(", ")} · ${p.hours} h`)))));
  },

  async project(index, id, _q, ctx) {
    const e = get(index, id);
    if (e?.kind !== "project") return notFound("project");
    const p = e.item;
    const meta = h("dl", { class: "meta" },
      h("dt", {}, "Starts after"), h("dd", {}, joinLinks(index, p.after)),
      h("dt", {}, "Estimate"), h("dd", {}, `${p.hours} h`));
    const actions = h("div", { class: "actions" }, bookmarkButton(ctx, id));
    if (!p.specified) return page(`${p.id} · ${p.title}`, meta, actions, h("p", { class: "note" }, "Outline only. Fully specified once its prerequisites are done."));
    try {
      const md = await ctx.load(`projects/${id}.md`);
      const frag = renderMarkdown(md, () => errorBox("Interactive blocks aren't supported in project specs."));
      frag.querySelector("h1")?.remove(); // the page provides its own h1
      return page(`${p.id} · ${p.title}`, meta, actions, h("article", { class: "lesson-body" }, frag));
    } catch {
      return page(`${p.id} · ${p.title}`, meta, actions, errorBox("This project specification couldn't be loaded."));
    }
  },

  profile(index, _id, _q, ctx) {
    const st = ctx.progress.state();
    const evidenced = [...st.lessons.values()].filter((l) => l.competentAt);
    const cell = (v) => v === null
      ? h("td", { class: "na" }, h("span", { "aria-hidden": "true" }, "—"), h("span", { class: "sr-only" }, "not assessed"))
      : h("td", { class: `num score-${v}` }, String(v));
    return page("Skill profile", ...ctx.assessments.assessments.map((a) => h("section", {},
      h("h2", {}, `${a.id} · ${a.date}`),
      h("p", { class: "muted" }, a.note),
      h("div", { class: "table-wrap" }, h("table", {},
        h("caption", {}, "Scores 0–4: A concept, B implementation, C debugging, D real-world"),
        h("thead", {}, h("tr", {}, ["Competency", "A", "B", "C", "D", "Confidence", "Evidence"].map((t) => h("th", { scope: "col" }, t)))),
        h("tbody", {}, a.competencies.map((c) => h("tr", {},
          h("th", { scope: "row" }, c.name), ["A", "B", "C", "D"].map((d) => cell(c[d])),
          h("td", {}, c.confidence), h("td", {}, c.evidence)))))))),
    card("Evidence from lessons",
      h("p", { class: "muted" }, "Shown next to the scores above, never merged into them: formal scores change only in mentor assessment sessions."),
      evidenced.length ? list(evidenced.map((l) => [link(index, l.id), " ", statusBadge(l.status), ` · ${day(l.masteredAt ?? l.competentAt)}`]))
        : empty("No lesson is COMPETENT yet.")));
  },

  search(index, _id, query) {
    const q = query.q ?? "";
    const results = search(index, q);
    return page(q ? `Search: ${q}` : "Search",
      !q ? empty("Type in the search box to find courses, modules, lessons and projects.")
        : results.length
          ? h("ol", { class: "list" }, results.map((r) => h("li", {}, link(index, r.id), h("span", { class: "muted" }, ` · ${r.kind}`))))
          : empty(`No results for "${q}".`));
  },

  notfound() {
    return page("Page not found", empty("That address doesn't match any page."), h("p", {}, h("a", { href: "#/" }, "Go to dashboard")));
  },

  async mentor(index, _id, query, ctx) {
    const exercises = authoredExercises(index);
    const fromExercise = exercises.find((x) => x.id === query.exercise);
    const pick = (key, fallback) => (MODES[key] ? key : fallback);
    const mode = pick(query.mode, "explain");
    const opt = (v, t, sel) => h("option", { value: v, selected: v === sel }, t);
    const select = (id, label, options, sel) => h("div", { class: "field" }, h("label", { for: id }, label),
      h("select", { id }, opt("", "(none)", sel), options.map(([v, t]) => opt(v, t, sel))));
    const area = (id, label, hint) => h("div", { class: "field" }, h("label", { for: id }, label), h("p", { class: "muted", id: `${id}-hint` }, hint),
      h("textarea", { id, rows: 6, spellcheck: "false", "aria-describedby": `${id}-hint` }));

    const modes = h("fieldset", { class: "modes" }, h("legend", {}, "Mode"),
      Object.entries(MODES).map(([key, m]) => h("div", { class: "option" },
        h("input", { type: "radio", name: "mentor-mode", id: `mode-${key}`, value: key, checked: key === mode }),
        h("label", { for: `mode-${key}` }, h("strong", {}, m.label), ` · ${m.purpose}`, m.needs ? h("span", { class: "muted" }, ` (needs ${m.needs.join(", ")})`) : null))));
    const form = h("form", { class: "mentor" }, modes,
      select("mentor-lesson", "Lesson", index.lessonOrder.map((id) => [id, `${id} · ${get(index, id).item.title}`]), query.lesson ?? fromExercise?.lesson ?? ""),
      select("mentor-exercise", "Exercise", exercises.map((x) => [x.id, x.id]), fromExercise?.id ?? ""),
      select("mentor-project", "Project", index.data.projects.map((p) => [p.id, `${p.id} · ${p.title}`]), query.project ?? ""),
      area("mentor-code", "Your code (optional)", "Paste the code you wrote. It stays on this page: nothing is stored or sent."),
      area("mentor-question", "Your question or error output (optional)", "For example a traceback, failing test output, or what confuses you."),
      h("div", { class: "option" }, h("input", { type: "checkbox", id: "mentor-profile", checked: true }),
        h("label", { for: "mentor-profile" }, "Include my learner profile and weak areas")),
      h("button", { class: "btn", type: "submit" }, "Build prompt"));
    const status = h("p", { class: "feedback", "aria-live": "polite" });
    const out = h("textarea", { id: "mentor-out", rows: 16, readonly: true, spellcheck: "false" });
    const copy = h("button", { class: "btn", type: "button", disabled: true }, "Copy prompt");
    const val = (id) => form.querySelector(`#${id}`).value;

    async function gather() {
      const c = { code: val("mentor-code"), question: val("mentor-question") };
      if (form.querySelector("#mentor-profile").checked) {
        c.profile = ctx.profile;
        const asm = ctx.assessments.assessments.at(-1);
        c.weak = asm ? weakCompetencies(asm) : [];
      }
      const progress = [];
      const st = ctx.progress.state();
      const lid = val("mentor-lesson");
      if (lid) {
        const entry = get(index, lid);
        const item = entry.item;
        const [courseId, moduleId] = entry.parents;
        c.lesson = { id: lid, title: item.title, objectives: [],
          module: `${moduleId} · ${get(index, moduleId).item.title}`, course: `${courseId} · ${get(index, courseId).item.title}` };
        if (item.authored) {
          try { c.lesson.objectives = parseFrontMatter(await ctx.load(`lessons/${lid}.md`)).meta.objectives; } catch { /* title only */ }
        }
        const s = st.lessons.get(lid);
        progress.push(`Lesson ${lid}: ${STATUS_TEXT[s.status]}`);
        if (s.evidence.quizzes.length) progress.push(`Quizzes: ${s.evidence.firstCorrect} of ${s.evidence.quizzes.length} correct on the first attempt`);
      }
      const xid = val("mentor-exercise");
      if (xid) {
        try { c.exercise = JSON.parse(await ctx.load(`exercises/${xid}/exercise.json`)); } catch { return { error: `Exercise ${xid} couldn't be loaded.` }; }
        const evs = ctx.progress.store.events.filter((e) => e.item === xid);
        const hints = Math.min(c.exercise.hints.length, Math.max(0, ...evs.filter((e) => e.type === "hint_viewed").map((e) => e.n)));
        c.hintsSeen = hints;
        const results = evs.filter((e) => e.type === "exercise_result");
        progress.push(`Exercise ${xid}: ${results.some((e) => e.passed) ? "passed" : "not passed yet"}; ${results.length} test result(s) imported; hints seen: ${hints} of ${c.exercise.hints.length}${evs.some((e) => e.type === "solution_viewed") ? "; reference solution viewed" : ""}`);
      }
      const pid = val("mentor-project");
      if (pid) {
        const proj = get(index, pid).item;
        c.project = { id: pid, title: proj.title };
        if (proj.specified) {
          try { c.project.spec = await ctx.load(`projects/${pid}.md`); } catch { return { error: `Project ${pid} specification couldn't be loaded.` }; }
        }
      }
      c.progress = progress;
      return c;
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const c = await gather();
      if (c.error) { status.replaceChildren(h("span", { class: "bad" }, c.error)); return; }
      const m = form.querySelector('input[name="mentor-mode"]:checked').value;
      const r = buildPrompt(m, c);
      if (!r.ok) {
        out.value = "";
        copy.disabled = true;
        status.replaceChildren(h("span", { class: "bad" }, `${MODES[m].label} mode needs: ${r.missing}.`));
        return;
      }
      out.value = r.prompt;
      copy.disabled = false;
      status.replaceChildren(`Prompt ready (${r.prompt.length} characters). Copy it, then paste it into Claude Code.`);
      out.focus();
    });
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(out.value);
        status.replaceChildren("Copied. Paste it into Claude Code.");
      } catch {
        out.focus();
        out.select();
        status.replaceChildren("Couldn't copy automatically. The text is selected: press Ctrl+C (Cmd+C on a Mac).");
      }
    });

    return page("AI mentor",
      h("p", { class: "note" }, "This builds a prompt for you to paste into Claude Code. The site doesn't send anything anywhere, ",
        "can't see your Claude conversations, and never includes reference solutions. Use it after you've attempted the work."),
      form,
      h("section", { class: "card" }, h("h2", {}, "Prompt"), h("label", { for: "mentor-out", class: "sr-only" }, "Generated prompt"), out, h("div", { class: "actions" }, copy), status));
  },
};
