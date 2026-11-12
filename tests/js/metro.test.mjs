import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildIndex } from "../../site/assets/js/curriculum.js";
import { layoutMetro } from "../../site/assets/js/metro.js";

const index = buildIndex(JSON.parse(readFileSync(new URL("../../content/curriculum.json", import.meta.url))));
const fakeState = (completed, nextLesson) => ({
  nextLesson,
  lessons: new Map(index.lessonOrder.map((id) => [id, { completedAt: completed.includes(id) ? "2026-11-12T10:00:00.000Z" : null }])),
});

test("one station per sequence item, one line per course, in sequence order", () => {
  const m = layoutMetro(index, fakeState([], index.lessonOrder[0]));
  assert.equal(m.stations.length, index.data.sequence.length);
  assert.deepEqual(m.lines.map((l) => l.course), index.data.courses.map((c) => c.id));
  const xs = m.stations.map((s) => s.x);
  assert.deepEqual(xs, [...xs].sort((a, b) => a - b));
});

test("station status comes from real lesson completion; 'here' is the next lesson's module", () => {
  const py1 = index.byId.get("PY.M01").item.lessons.map((l) => l.id);
  const m = layoutMetro(index, fakeState([...py1, "PY.M02.L01"], "PY.M02.L02"));
  const st = (id) => m.stations.find((s) => s.id === id);
  assert.equal(st("PY.M01").status, "done");
  assert.equal(st("PY.M02").status, "partial");
  assert.equal(st("PY.M03").status, "none");
  assert.equal(m.here.id, "PY.M02");
});

test("projects ride the line of the module before them; transfers mark line changes", () => {
  const m = layoutMetro(index, fakeState([], null));
  const seq = index.data.sequence;
  const prj = m.stations.find((s) => s.id === "PRJ-01");
  const before = index.byId.get(seq[seq.indexOf("PRJ-01") - 1]);
  assert.equal(prj.course, before.parents[0]);
  const changes = m.stations.slice(1).filter((s, i) => s.course !== m.stations[i].course).length;
  assert.equal(m.links.length, changes);
  assert.equal(m.here.id, m.stations.at(-1).id, "with nothing left, 'here' is the final station");
});
