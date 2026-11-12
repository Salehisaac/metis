import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  buildIndex, breadcrumbs, lessonNeighbors, search, totalHours, weakCompetencies,
} from "../../site/assets/js/curriculum.js";
import { parseHash, href } from "../../site/assets/js/router.js";

const root = new URL("../../", import.meta.url);
const data = JSON.parse(readFileSync(new URL("content/curriculum.json", root)));
const asm = JSON.parse(readFileSync(new URL("content/learner/assessments.json", root)));
const index = buildIndex(data);

test("breadcrumbs go course > module > lesson", () => {
  assert.deepEqual(breadcrumbs(index, "PY.M02.L03").map((b) => b.id), ["PY", "PY.M02", "PY.M02.L03"]);
  assert.deepEqual(breadcrumbs(index, "nope"), []);
});

test("lesson neighbors follow sequence, with null at the ends", () => {
  assert.deepEqual(lessonNeighbors(index, "PY.M01.L01"), { prev: null, next: "PY.M01.L02" });
  assert.deepEqual(lessonNeighbors(index, "PY.M01.L04"), { prev: "PY.M01.L03", next: "PY.M02.L01" });
  const last = index.lessonOrder.at(-1);
  assert.equal(lessonNeighbors(index, last).next, null);
  assert.deepEqual(lessonNeighbors(index, "unknown"), { prev: null, next: null });
});

test("lesson order follows sequence, not course order", () => {
  // PY.M07 is sequenced after PY.M06, so its first lesson must follow PY.M06's last.
  const i = index.lessonOrder.indexOf("PY.M06.L03");
  assert.equal(index.lessonOrder[i + 1], "PY.M07.L01");
});

test("search ranks id, then title, then outcome; ignores blank", () => {
  assert.deepEqual(search(index, "   "), []);
  const r = search(index, "transactions");
  const ranks = r.map((x) => x.rank);
  assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b), "results ordered by rank (id, title, outcome)");
  assert.ok(r.some((x) => x.id === "DB.M03" && x.rank === 1), "title match found at title rank");
  assert.ok(search(index, "py.m02.l03").some((x) => x.id === "PY.M02.L03"));
});

test("hours match the approved curriculum (about 290h)", () => {
  assert.deepEqual(totalHours(index), { modules: 188, projects: 102, total: 290 });
});

test("weak competencies use only assessed scores", () => {
  const weak = weakCompetencies(asm.assessments[0]).map((c) => c.name);
  assert.ok(weak.includes("Transactions and atomicity"));
  assert.ok(!weak.includes("Git"), "not assessed must not count as weak");
  assert.ok(!weak.includes("Caching (Redis)"));
});

test("parseHash handles views, ids, queries and unknowns", () => {
  assert.deepEqual(parseHash(""), { view: "dashboard", id: null, query: {} });
  assert.deepEqual(parseHash("#/lesson/PY.M02.L03"), { view: "lesson", id: "PY.M02.L03", query: {} });
  assert.deepEqual(parseHash("#/search?q=sql%20join"), { view: "search", id: null, query: { q: "sql join" } });
  assert.equal(parseHash("#/<script>").view, "notfound");
  assert.equal(href("module", "DB.M03"), "#/module/DB.M03");
});
