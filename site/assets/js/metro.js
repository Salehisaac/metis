// The dashboard route map: each course is a metro line, each module a station, projects are diamond stations.
// layoutMetro() is pure (tested in tests/js); renderMetro() builds the SVG with s() (no innerHTML).
import { s } from "./dom.js";
import { get } from "./curriculum.js";
import { href } from "./router.js";

const STEP = 27;
const ROW = 46;
const PAD_X = 64;
const PAD_Y = 34;

export function layoutMetro(index, state) {
  const courses = index.data.courses.map((c) => c.id);
  const rowOf = Object.fromEntries(courses.map((id, i) => [id, i]));
  const stations = [];
  let lastCourse = courses[0];
  index.data.sequence.forEach((id, i) => {
    const e = get(index, id);
    const course = e.kind === "module" ? e.parents[0] : lastCourse; // projects ride the line they follow
    lastCourse = course;
    const lessons = e.kind === "module" ? e.item.lessons : [];
    const done = lessons.filter((l) => state.lessons.get(l.id)?.completedAt).length;
    stations.push({
      id, kind: e.kind, course, title: e.item.title, x: PAD_X + i * STEP, y: PAD_Y + rowOf[course] * ROW,
      done, total: lessons.length,
      status: lessons.length && done === lessons.length ? "done" : done > 0 ? "partial" : "none",
    });
  });
  const lines = courses.map((c) => {
    const xs = stations.filter((st) => st.course === c).map((st) => st.x);
    return { course: c, y: PAD_Y + rowOf[c] * ROW, x1: Math.min(...xs), x2: Math.max(...xs) };
  });
  // Transfers: where the route changes line, link the two consecutive stations.
  const links = [];
  for (let i = 1; i < stations.length; i++) {
    const a = stations[i - 1];
    const b = stations[i];
    if (a.course !== b.course) links.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
  }
  const hereModule = state.nextLesson ? get(index, state.nextLesson).parents[1] : null;
  const here = stations.find((st) => st.id === hereModule) ?? stations.at(-1);
  return {
    width: PAD_X + (stations.length - 1) * STEP + 40,
    height: PAD_Y + (courses.length - 1) * ROW + 40,
    lines, stations, links, here,
  };
}

export function renderMetro(index, state) {
  const m = layoutMetro(index, state);
  const line = (course) => `var(--line-${course.toLowerCase()})`;
  const label = (st) => (st.kind === "project"
    ? `${st.id} ${st.title}, project`
    : `${st.id} ${st.title}, ${st.done} of ${st.total} lessons completed${st.id === m.here.id ? ", you are here" : ""}`);
  const svg = s("svg", { class: "metro", viewBox: `0 0 ${m.width} ${m.height}`,
    "aria-labelledby": "metro-title" },
    s("title", { id: "metro-title" }, "Route map: one line per course, one station per module, in learning order"),
    m.links.map((l) => s("path", { class: "transfer", d: `M${l.x1} ${l.y1} C ${l.x1 + 17} ${l.y1}, ${l.x2 - 17} ${l.y2}, ${l.x2} ${l.y2}` })),
    m.lines.map((l, i) => [
      s("text", { class: "line-name", x: 14, y: l.y + 5, fill: line(l.course) }, l.course),
      s("path", { class: "line", d: `M${l.x1} ${l.y} H ${l.x2}`, stroke: line(l.course), pathLength: 1, style: `--i:${i}` }),
    ]),
    m.stations.map((st) => s("a", { href: href(st.kind === "project" ? "project" : "module", st.id), "aria-label": label(st), class: "stop" },
      s("title", {}, label(st)),
      st.kind === "project"
        ? s("rect", { class: "station project", x: st.x - 8, y: st.y - 8, width: 16, height: 16, transform: `rotate(45 ${st.x} ${st.y})`, stroke: line(st.course) })
        : [s("circle", { class: `station ${st.status}`, cx: st.x, cy: st.y, r: st.id === m.here.id ? 10 : 8, stroke: line(st.course) }),
          st.status === "partial" ? s("circle", { class: "partial-dot", cx: st.x, cy: st.y, r: 3 }) : null])),
    s("g", { class: "here-tag", transform: `translate(${m.here.x} ${m.here.y + 26})` },
      s("rect", { x: -38, y: -11, width: 76, height: 22, rx: 11 }),
      s("text", { x: 0, y: 5, "text-anchor": "middle" }, "You're here")),
    s("g", { class: "train", style: `offset-path: path("M${m.lines.find((l) => l.course === m.here.course).x1} ${m.here.y} H ${m.here.x}")` },
      s("rect", { x: -15, y: -8, width: 30, height: 16, rx: 8 })),
  );
  return svg;
}
