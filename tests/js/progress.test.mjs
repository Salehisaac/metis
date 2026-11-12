import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildIndex } from "../../site/assets/js/curriculum.js";
import { derive, deriveLesson, RULES } from "../../site/assets/js/progress.js";
import { validateEvent, parseImport, exportPayload, sortEvents, SCHEMA_VERSION } from "../../site/assets/js/events.js";

const L = "PY.M01.L01";
const EX = `${L}.E1`;
const lessonWithEx = { id: L, exercises: [EX], quizzes: ["q1", "q2", "q3"] };
const quizOnly = { id: L, exercises: [], quizzes: ["q1", "q2", "q3"] };

let n = 0;
const t0 = Date.parse("2026-11-01T10:00:00.000Z");
const at = (days, minutes = 0) => new Date(t0 + days * 86_400_000 + minutes * 60_000).toISOString();
const ev = (type, item, when, extra = {}) => ({ id: `evt-${String(++n).padStart(6, "0")}`, type, item, at: when, ...extra });
const ans = (q, ok, when) => ev("quiz_answer", `${L}#${q}`, when, { correct: ok });
const pass = (when, passed = true) => ev("exercise_result", EX, when, { passed, tests: 2, failures: passed ? 0 : 1, errors: 0, skipped: 0, expected: 2 });
const review = (when, correct, total = 3) => ev("review_done", L, when, { correct, total });

// A lesson that becomes COMPETENT at day 0 + 30 min.
const competentBase = () => [
  ev("lesson_started", L, at(0)), ans("q1", true, at(0, 5)), ans("q2", true, at(0, 6)), ans("q3", true, at(0, 7)),
  pass(at(0, 20)), ev("lesson_completed", L, at(0, 30)),
];

test("opening a lesson never completes it", () => {
  const s = deriveLesson(lessonWithEx, [ev("lesson_started", L, at(0))]);
  assert.equal(s.status, "STARTED");
  assert.equal(s.completedAt, null);
});

test("completed is not competent without evidence", () => {
  const s = deriveLesson(lessonWithEx, [ev("lesson_completed", L, at(0))]);
  assert.equal(s.status, "COMPLETED");
});

test("competent needs completion, an independent pass and first-attempt quizzes", () => {
  const s = deriveLesson(lessonWithEx, competentBase());
  assert.equal(s.status, "COMPETENT");
  assert.equal(s.competentAt, at(0, 30)); // the moment the last condition held
});

test("a wrong first answer stays wrong after a correct retry", () => {
  const evs = [ev("lesson_completed", L, at(0)), ans("q1", false, at(0, 1)), ans("q1", true, at(0, 2)), ans("q2", true, at(0, 3)), ans("q3", true, at(0, 4))];
  const s = deriveLesson(quizOnly, evs);
  assert.equal(s.evidence.firstCorrect, 2); // 2/3 < 0.8
  assert.equal(s.status, "COMPLETED");
});

test("a pass after viewing the solution doesn't count; a pass before it does", () => {
  const after = [...competentBase().filter((e) => e.type !== "exercise_result"),
    ev("solution_viewed", EX, at(0, 10)), pass(at(0, 20))];
  assert.equal(deriveLesson(lessonWithEx, after).status, "COMPLETED");
  const before = [...competentBase(), ev("solution_viewed", EX, at(0, 40))];
  assert.equal(deriveLesson(lessonWithEx, before).status, "COMPETENT");
});

test("hints are recorded as context, not a blocker", () => {
  const s = deriveLesson(lessonWithEx, [...competentBase(), ev("hint_viewed", EX, at(0, 15), { n: 2 })]);
  assert.equal(s.status, "COMPETENT");
  assert.equal(s.evidence.exercises[0].hints, 2);
});

test("too little evidence: a lesson with 1 quiz and no exercise can't become competent", () => {
  const s = deriveLesson({ id: L, exercises: [], quizzes: ["q1"] }, [ev("lesson_completed", L, at(0)), ans("q1", true, at(0, 1))]);
  assert.equal(s.status, "COMPLETED");
  assert.equal(s.evidence.enoughEvidence, false);
});

test("no mastery from a review at day 3; mastery from a valid review at day 7+", () => {
  assert.equal(deriveLesson(lessonWithEx, [...competentBase(), review(at(3), 3)]).status, "COMPETENT");
  const s = deriveLesson(lessonWithEx, [...competentBase(), review(at(3), 3), review(at(8), 3)]);
  assert.equal(s.status, "MASTERED");
  assert.equal(s.masteredAt, at(8));
});

test("a review needs enough items and ratio", () => {
  assert.equal(deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 2, 2)]).status, "COMPETENT");
  assert.equal(deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 2, 3)]).status, "COMPETENT");
});

test("a later failed review removes mastery and resets the interval", () => {
  const s = deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 3), review(at(20), 1)]);
  assert.equal(s.status, "COMPETENT");
  assert.equal(s.review.nextAt, at(20 + RULES.intervalsDays[0]));
  const again = deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 3), review(at(20), 1), review(at(22), 3)]);
  assert.equal(again.status, "MASTERED");
});

test("spaced intervals advance on success", () => {
  // competent at day 0 +30min -> due day 1 +30min; review then -> next due 3 days later
  const s = deriveLesson(lessonWithEx, [...competentBase(), review(at(1, 60), 3), review(at(4, 120), 3)]);
  assert.equal(s.review.nextAt, new Date(Date.parse(at(4, 120)) + RULES.intervalsDays[2] * 86_400_000).toISOString());
});

test("reviews before they are due are practice, not evidence", () => {
  const early = deriveLesson(lessonWithEx, [...competentBase(), review(at(0, 40), 3)]); // before the 1-day due time
  assert.equal(early.review.nextAt, at(1, 30), "early review doesn't move the schedule");
  assert.equal(early.review.practice, 1);
  // fail a due review at day 8, retake 5 minutes later with full marks: the retake is ignored (next due in 1 day)
  const retake = deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 1), review(at(8, 5), 3)]);
  assert.equal(retake.status, "COMPETENT");
  assert.equal(retake.review.practice, 1);
  // the next due success, 7+ days after competence, still gives mastery
  assert.equal(deriveLesson(lessonWithEx, [...competentBase(), review(at(8), 1), review(at(9, 5), 3)]).status, "MASTERED");
});

test("derive: out-of-order events, retired ids, bookmarks, totals, due list", () => {
  const index = buildIndex(JSON.parse(readFileSync(new URL("../../content/curriculum.json", import.meta.url))));
  const lesson = index.byId.get(L).item;
  Object.assign(lesson, { authored: true, exercises: [EX], quizzes: ["q1", "q2", "q3"] });
  const evs = [
    ...competentBase().reverse(), // out of order on purpose
    ev("lesson_completed", "PY.M09.L01", at(0)), // retired / unknown lesson: ignored
    ev("bookmark", "PY.M02", at(1), { on: true }), ev("bookmark", "PY.M03", at(1), { on: true }), ev("bookmark", "PY.M03", at(2), { on: false }),
  ];
  const s = derive(evs, index, at(2));
  assert.equal(s.lessons.get(L).status, "COMPETENT");
  assert.deepEqual([...s.bookmarks], ["PY.M02"]);
  assert.deepEqual(s.totals, { defined: index.lessonOrder.length, completed: 1, competent: 1, mastered: 0 });
  assert.equal(s.nextLesson, "PY.M01.L02");
  assert.deepEqual(s.due, [L]); // first review due 1 day after competence
  assert.deepEqual(derive(evs, index, at(0, 40)).due, []);
});

test("event validation: closed schema, ids, timestamps, types", () => {
  const good = ev("quiz_answer", `${L}#q1`, at(0), { correct: true, answerText: "secret" });
  const { event } = validateEvent(good);
  assert.equal(event.answerText, undefined, "unknown fields dropped");
  for (const bad of [
    null, [], { ...good, type: "evil" }, { ...good, id: "x" }, { ...good, at: "yesterday" },
    { ...good, item: "<script>" }, { ...good, correct: "yes" },
    ev("review_done", L, at(0), { correct: 4, total: 3 }), ev("hint_viewed", EX, at(0), { n: 0 }),
    ev("lesson_started", EX, at(0)), // wrong item kind for the type
  ]) assert.ok(validateEvent(bad).error, JSON.stringify(bad));
  assert.ok(validateEvent(ev("bookmark", "PRJ-01", at(0), { on: true })).event);
});

test("import: round trip, all-or-nothing, version and size limits", () => {
  const evs = competentBase();
  const text = JSON.stringify(exportPayload(evs, at(1)));
  const r = parseImport(text);
  assert.ok(r.ok);
  assert.deepEqual(r.events, sortEvents(evs));
  assert.equal(parseImport("{").ok, false);
  assert.equal(parseImport(JSON.stringify({ format: "other" })).ok, false);
  const newer = parseImport(JSON.stringify({ ...exportPayload(evs, at(1)), schemaVersion: SCHEMA_VERSION + 1 }));
  assert.match(newer.errors[0], /newer version/);
  const oneBad = parseImport(JSON.stringify(exportPayload([...evs, { ...evs[0], id: "!" }], at(1))));
  assert.equal(oneBad.ok, false, "one bad event rejects the whole file");
  assert.equal(parseImport("x".repeat(5_000_001)).ok, false);
  const future = parseImport(JSON.stringify(exportPayload([ev("lesson_completed", L, at(30))], at(1))), at(1));
  assert.match(future.errors[0], /future/);
});
