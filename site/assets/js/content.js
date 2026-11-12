// Pure content helpers (no DOM). Front-matter format must match tools/validate.py parse_front_matter.

export function parseFrontMatter(text) {
  const t = text.replace(/\r\n/g, "\n");
  if (!t.startsWith("---\n")) throw new Error("missing front matter");
  const end = t.indexOf("\n---\n", 4);
  if (end === -1) throw new Error("unterminated front matter");
  const meta = JSON.parse(t.slice(4, end));
  if (meta === null || typeof meta !== "object" || Array.isArray(meta)) throw new Error("front matter must be a JSON object");
  return { meta, body: t.slice(end + 5) };
}

// Output answers: compare line by line after trimming each line, collapsing runs of spaces/tabs,
// and dropping trailing blank lines. Spacing *inside* a line (e.g. "[1, 2]" vs "[1,2]") still matters:
// knowing Python's exact print format is part of predicting output. Authors add alternatives via `accept`.
export function normalizeOutput(s) {
  const lines = String(s).replace(/\r\n?/g, "\n").split("\n").map((l) => l.trim().replace(/[ \t]+/g, " "));
  while (lines.length && lines.at(-1) === "") lines.pop();
  return lines.join("\n");
}

// Returns { correct: boolean } for auto-graded types; explain-type is never auto-graded.
export function gradeQuiz(quiz, response) {
  switch (quiz.type) {
    case "choice": return { correct: Number(response) === quiz.answer };
    case "truefalse": return { correct: response === String(quiz.answer) };
    case "output": {
      const got = normalizeOutput(response);
      return { correct: [quiz.answer, ...(quiz.accept ?? [])].some((a) => normalizeOutput(a) === got) };
    }
    default: return { correct: null };
  }
}

// Verdict for a pytest JUnit report. suiteName: <testsuite name>; cases: [{name, status}] with status
// passed|failed|error|skipped, taken per <testcase> (suite-level counts are ignored: they're easy to hand-edit).
// Every expected test must be present; extra tests (the learner's own) are allowed but must pass too.
// ponytail: matches on test name only, not classname; add classname if exercises ever have two files with equal names.
export function junitVerdict(expectedId, expectedTests, suiteName, cases) {
  if (suiteName !== expectedId) return { ok: false, reason: `This report is for "${suiteName}", not ${expectedId}.` };
  const status = new Map(cases.map((c) => [c.name, c.status]));
  const missing = expectedTests.filter((t) => !status.has(t));
  if (missing.length) {
    return { ok: false, reason: `Expected tests are missing from the report: ${missing.join(", ")}. Run the exercise's full, unmodified tests.` };
  }
  const count = (s) => cases.filter((c) => c.status === s).length;
  return {
    ok: true, tests: cases.length, passed: count("passed"), failures: count("failed"), errors: count("error"),
    skipped: count("skipped"), extra: cases.length - expectedTests.length, allPassed: count("passed") === cases.length,
  };
}
