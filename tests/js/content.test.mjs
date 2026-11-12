import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseFrontMatter, normalizeOutput, gradeQuiz, junitVerdict } from "../../site/assets/js/content.js";

test("front matter parses the fixture lesson like the Python validator", () => {
  const text = readFileSync(new URL("../fixtures/content/lessons/PY.M01.L01.md", import.meta.url), "utf8");
  const { meta, body } = parseFrontMatter(text);
  assert.equal(meta.id, "PY.M01.L01");
  assert.ok(body.startsWith("## Fixture lesson"));
  assert.deepEqual(parseFrontMatter('---\r\n{"a": 1}\r\n---\r\nbody'), { meta: { a: 1 }, body: "body" });
  assert.throws(() => parseFrontMatter("no header"));
  assert.throws(() => parseFrontMatter("---\n{}\n"));
  assert.throws(() => parseFrontMatter("---\n[1]\n---\nx"));
});

test("output normalisation keeps in-line spacing but forgives edges", () => {
  assert.equal(normalizeOutput("  [1, 2]  \r\n\n"), "[1, 2]");
  assert.equal(normalizeOutput("a   b\t\tc"), "a b c");
  assert.notEqual(normalizeOutput("[1,2]"), normalizeOutput("[1, 2]"));
});

test("quiz grading per type, with accept list", () => {
  assert.deepEqual(gradeQuiz({ type: "choice", answer: 1 }, "1"), { correct: true });
  assert.deepEqual(gradeQuiz({ type: "choice", answer: 1 }, "0"), { correct: false });
  assert.deepEqual(gradeQuiz({ type: "truefalse", answer: false }, "false"), { correct: true });
  const q = { type: "output", answer: "[1, 2, 3]", accept: ["[1,2,3]"] };
  assert.equal(gradeQuiz(q, "[1, 2, 3]\n").correct, true);
  assert.equal(gradeQuiz(q, "[1,2,3]").correct, true);
  assert.equal(gradeQuiz(q, "[1, 2]").correct, false);
  assert.equal(gradeQuiz({ type: "explain" }, "anything").correct, null);
});

test("junit verdict: suite name, expected tests present, per-case status", () => {
  const id = "PY.M01.L01.E1";
  const exp = ["test_a", "test_b"];
  const c = (name, status = "passed") => ({ name, status });
  assert.equal(junitVerdict(id, exp, "other", [c("test_a"), c("test_b")]).ok, false);
  const missing = junitVerdict(id, exp, id, [c("test_a")]); // learner deleted a failing test
  assert.equal(missing.ok, false);
  assert.match(missing.reason, /test_b/);
  const pass = junitVerdict(id, exp, id, [c("test_a"), c("test_b")]);
  assert.deepEqual([pass.ok, pass.allPassed, pass.passed, pass.extra], [true, true, 2, 0]);
  const extraFail = junitVerdict(id, exp, id, [c("test_a"), c("test_b"), c("test_mine", "failed")]);
  assert.deepEqual([extraFail.ok, extraFail.allPassed, extraFail.failures, extraFail.extra], [true, false, 1, 1]);
  const mixed = junitVerdict(id, exp, id, [c("test_a", "error"), c("test_b", "skipped")]);
  assert.deepEqual([mixed.allPassed, mixed.errors, mixed.skipped, mixed.passed], [false, 1, 1, 0]);
});
