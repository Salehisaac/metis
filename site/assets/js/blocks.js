// Interactive lesson blocks: quizzes and exercises. All text via h()/textContent.
// Recording is optional via hooks (onAnswer, onHint, onSolution, onResult); blocks never store anything themselves.
import { h } from "./dom.js";
import { gradeQuiz, junitVerdict } from "./content.js";
import { renderMarkdown, highlight } from "./render.js";

let uid = 0;
const nextId = (p) => `${p}-${++uid}`;

export const errorBox = (text) => h("div", { class: "block-error" }, text);

// `code` spans in quiz text become <code> elements; everything else stays plain text (never parsed as HTML).
export const inline = (text) => String(text).split(/`([^`]+)`/).map((part, i) => (i % 2 ? h("code", {}, part) : part));

function codeBlock(code, lang = "python") {
  const el = h("code", { class: `language-${lang}` }, code);
  highlight(el);
  return h("pre", {}, el);
}

// ---------------------------------------------------------------- quiz
const TYPE_LABEL = { choice: "Multiple choice", truefalse: "True or false", output: "Predict the output", explain: "Explain" };

export function quizBlock(raw, hooks = {}) {
  let q;
  try { q = JSON.parse(raw); } catch { return errorBox("This quiz couldn't be loaded: its data is not valid JSON."); }
  if (!q || !TYPE_LABEL[q.type]) return errorBox("This quiz couldn't be loaded: unknown question type.");

  const id = nextId("quiz");
  const feedback = h("div", { class: "feedback", "aria-live": "polite" });
  const show = (correct) => {
    feedback.replaceChildren(...[ // replaceChildren would print null as "null"; filter it out
      correct === null ? null : h("p", { class: correct ? "ok" : "bad" }, correct ? "Correct." : "Not quite."),
      q.type === "explain" ? h("p", {}, h("strong", {}, "Model answer: "), inline(q.model)) : null,
      h("p", {}, inline(q.explanation))].filter(Boolean));
  };
  const code = q.code ? codeBlock(q.code) : null;
  const tag = h("p", { class: "quiz-type" }, q.label ?? TYPE_LABEL[q.type]); // e.g. "Debugging", "Application"
  // Review mode (hooks.deferFeedback): only the first answer counts and nothing is revealed until reveal() is called,
  // so reloading mid-review leaks no answers.
  let firstResult;
  const respond = (correct) => {
    if (!hooks.deferFeedback) { show(correct); hooks.onAnswer?.(q, correct); return; }
    if (firstResult !== undefined) { feedback.replaceChildren(h("p", {}, "Your first answer is already recorded.")); return; }
    firstResult = correct;
    feedback.replaceChildren(h("p", {}, "Answer recorded. Feedback appears when the review is finished."));
    hooks.onAnswer?.(q, correct);
  };
  const finish = (section) => Object.assign(section, { reveal: () => show(firstResult ?? null) });

  if (q.type === "choice" || q.type === "truefalse") {
    const options = q.type === "choice" ? q.options.map((o, i) => [String(i), o]) : [["true", "True"], ["false", "False"]];
    const form = h("form", { class: "quiz" },
      h("fieldset", {},
        h("legend", {}, inline(q.prompt)),
        code,
        options.map(([value, label]) => {
          const oid = nextId("opt");
          return h("div", { class: "option" }, h("input", { type: "radio", name: id, id: oid, value }), h("label", { for: oid }, inline(label)));
        })),
      h("button", { class: "btn", type: "submit" }, "Check"), feedback);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const picked = form.querySelector(`input[name="${id}"]:checked`);
      if (!picked) { feedback.replaceChildren(h("p", {}, "Choose an answer first.")); return; }
      respond(gradeQuiz(q, picked.value).correct);
    });
    return finish(h("section", { class: "card block" }, tag, form));
  }

  // output / explain: free text
  const area = h("textarea", { id, rows: q.type === "output" ? 3 : 4, spellcheck: "false" });
  const btn = h("button", { class: "btn", type: "submit" }, q.type === "output" ? "Check" : "Show model answer");
  const form = h("form", { class: "quiz" },
    h("p", { class: "prompt" }, inline(q.prompt)), code,
    h("label", { for: id }, q.type === "output" ? "Exact output:" : "Your answer (write it before revealing):"),
    area, btn, feedback);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!area.value.trim()) { feedback.replaceChildren(h("p", {}, "Write your answer first.")); area.focus(); return; }
    const { correct } = gradeQuiz(q, area.value);
    if (correct === null) { show(null); return; } // explain answers are never stored or graded
    respond(correct);
  });
  return finish(h("section", { class: "card block" }, tag, form));
}

// ---------------------------------------------------------------- exercise
const MAX_REPORT_BYTES = 1_000_000;

function readJunit(file, exerciseId, expectedTests) {
  return new Promise((resolve) => {
    if (file.size > MAX_REPORT_BYTES) return resolve({ ok: false, reason: "File is too large to be a test report (limit 1 MB)." });
    const reader = new FileReader();
    reader.onerror = () => resolve({ ok: false, reason: "Couldn't read the file." });
    reader.onload = () => {
      const doc = new DOMParser().parseFromString(String(reader.result), "application/xml");
      if (doc.querySelector("parsererror")) return resolve({ ok: false, reason: "Not a valid XML file." });
      const suite = doc.documentElement.tagName === "testsuite" ? doc.documentElement : doc.querySelector("testsuites > testsuite");
      if (!suite) return resolve({ ok: false, reason: "No <testsuite> found. Import the result.xml that pytest wrote." });
      const cases = [...suite.querySelectorAll("testcase")].map((tc) => ({
        name: tc.getAttribute("name") ?? "",
        status: tc.querySelector("failure") ? "failed" : tc.querySelector("error") ? "error" : tc.querySelector("skipped") ? "skipped" : "passed",
      }));
      resolve(junitVerdict(exerciseId, expectedTests, suite.getAttribute("name") ?? "", cases));
    };
    reader.readAsText(file);
  });
}

function list(items) { return h("ul", {}, items.map((x) => h("li", {}, x))); }

export function exerciseBlock(exerciseId, load, hooks = {}) {
  const box = h("section", { class: "card block exercise" }, h("p", { class: "muted" }, `Loading exercise ${exerciseId}…`));
  load(`exercises/${exerciseId}/exercise.json`)
    .then((text) => box.replaceChildren(...exerciseBody(JSON.parse(text), load, hooks)))
    .catch(() => box.replaceChildren(errorBox(`Exercise ${exerciseId} couldn't be loaded.`)));
  return box;
}

function exerciseBody(ex, load, hooks) {
  // Hints: each reveal unlocks the next one.
  const hintList = h("ol", { class: "hints" });
  const hintBtn = h("button", { class: "btn", type: "button" }, `Show hint 1 of ${ex.hints.length}`);
  hintBtn.addEventListener("click", () => {
    const n = hintList.children.length;
    const li = h("li", { tabindex: "-1" }, ex.hints[n]);
    hintList.append(li);
    if (n + 1 >= ex.hints.length) hintBtn.remove();
    else hintBtn.textContent = `Show hint ${n + 2} of ${ex.hints.length}`;
    li.focus(); // moves focus to (and announces) the new hint; also keeps focus when the button is removed
    hooks.onHint?.(ex.id, n + 1);
  });

  // Test-result import (session only).
  const fileId = nextId("junit");
  const resultOut = h("div", { class: "feedback", "aria-live": "polite" });
  const fileInput = h("input", { type: "file", id: fileId, accept: ".xml,application/xml,text/xml" });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    const v = await readJunit(file, ex.id, ex.tests);
    resultOut.replaceChildren(v.ok
      ? h("p", { class: v.allPassed ? "ok" : "bad" },
        (v.allPassed ? `All ${v.tests} tests passed.` : `${v.passed} of ${v.tests} passed: ${v.failures} failed, ${v.errors} errors, ${v.skipped} skipped.`)
          + (v.extra > 0 ? ` (${v.extra} of them your own.)` : ""))
      : h("p", { class: "bad" }, v.reason),
    h("p", { class: "muted" }, v.ok && hooks.onResult ? "Saved to your progress." : "Not saved."));
    if (v.ok) hooks.onResult?.(ex, v);
  });

  // Reference solution: fetched only after an explicit, confirmed request.
  const solution = h("div", { class: "solution" });
  const askBtn = h("button", { class: "btn", type: "button" }, "Show reference solution");
  askBtn.addEventListener("click", () => {
    const yes = h("button", { class: "btn", type: "button" }, "Yes, show it");
    const no = h("button", { class: "btn", type: "button" }, "Cancel");
    solution.replaceChildren(h("div", { class: "note", role: "group", "aria-label": "Confirm" },
      h("p", {}, "Have you attempted this yet? Reading the solution first removes most of what the exercise teaches."), yes, " ", no));
    no.addEventListener("click", () => { solution.replaceChildren(); askBtn.focus(); });
    yes.addEventListener("click", async () => {
      hooks.onSolution?.(ex.id); // recorded before display: later passes no longer count as independent
      solution.replaceChildren(h("p", { class: "muted" }, "Loading solution…"));
      try {
        const md = await load(`exercises/${ex.id}/solution/SOLUTION.md`);
        askBtn.remove();
        solution.replaceChildren(h("h4", { tabindex: "-1" }, "Reference solution"),
          renderMarkdown(md, () => errorBox("Interactive blocks aren't allowed in solutions.")));
        solution.querySelector("h4").focus();
      } catch { solution.replaceChildren(errorBox("The solution couldn't be loaded.")); }
    });
    yes.focus();
  });

  const cmd = [
    `.venv/bin/python tools/scaffold.py ${ex.id}   # once, from the project root`,
    `cd workspace/${ex.id}`,
    `../../.venv/bin/pytest                         # writes result.xml`,
    `../../.venv/bin/pytest -x -vv                  # debugging: stop at first failure, show details`,
  ].join("\n");

  return [
    h("p", { class: "quiz-type" }, "Exercise"),
    h("h3", {}, ex.title, " ", h("code", {}, ex.id)),
    h("p", {}, ex.problem),
    h("h4", {}, "Requirements"), list(ex.requirements),
    h("h4", {}, "Contract"), h("p", {}, h("code", {}, ex.contract)),
    h("h4", {}, "Expected behaviour"), h("p", {}, ex.expectedBehavior),
    h("h4", {}, "Edge cases"), list(ex.edgeCases),
    h("h4", {}, "How it's evaluated"), list(ex.evaluation),
    h("h4", {}, "Work locally"), codeBlock(cmd, "bash"),
    h("h4", {}, "Hints"), hintList, hintBtn,
    h("p", {}, h("a", { href: `#/mentor?${new URLSearchParams({ mode: "hint", exercise: ex.id })}` }, "Stuck after the hints? Ask the AI mentor for one more")),
    h("h4", {}, "Check your result"),
    h("label", { for: fileId }, "Import result.xml: "), fileInput, resultOut,
    h("h4", {}, "Solution"), askBtn, solution,
  ];
}
