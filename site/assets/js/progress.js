// Derive learning state from the event log. Pure: (events, curriculum index, now) -> state.
// Statuses are evidence-based and kept separate (spec §8.7, §11): opening a lesson never completes it,
// only first attempts count, a pass after viewing the solution is not independent, mastery needs a delayed review.
import { sortEvents } from "./events.js";

// Teaching rules approved by the learner at Gate 5 (2026-11-12); change only with their agreement, here and in ARCHITECTURE.md.
export const RULES = {
  quizRatio: 0.8,          // first-attempt correct ratio needed (lesson quizzes and reviews)
  minQuizItems: 3,         // a lesson with no exercises needs at least this many auto-graded quizzes
  minReviewItems: 3,       // a review needs at least this many items to count
  masteryDelayDays: 7,     // a review counts toward mastery only this long after competence
  intervalsDays: [1, 3, 7, 14, 30, 60], // spaced review: success -> next step, failure -> back to the first
};

const DAY = 86_400_000;
const addDays = (iso, d) => new Date(Date.parse(iso) + d * DAY).toISOString();
const maxIso = (xs) => xs.reduce((m, x) => (x > m ? x : m));

export function deriveLesson(lesson, evs, rules = RULES) {
  const of = (type, item = lesson.id) => evs.filter((e) => e.type === type && e.item === item);
  const started = of("lesson_started")[0]?.at ?? null;
  const completedAt = of("lesson_completed")[0]?.at ?? null;

  const exercises = (lesson.exercises ?? []).map((id) => {
    const solutionAt = of("solution_viewed", id)[0]?.at ?? null;
    const pass = of("exercise_result", id).find((e) => e.passed && (!solutionAt || e.at < solutionAt));
    const hints = Math.max(0, ...of("hint_viewed", id).filter((e) => !pass || e.at <= pass.at).map((e) => e.n));
    const attempts = of("exercise_result", id).length;
    return { id, passedAt: pass?.at ?? null, hints, solutionAt, attempts };
  });

  const quizzes = (lesson.quizzes ?? []).map((qid) => {
    const first = of("quiz_answer", `${lesson.id}#${qid}`)[0];
    return { id: qid, answeredAt: first?.at ?? null, correct: first?.correct ?? null };
  });
  const answered = quizzes.filter((q) => q.answeredAt);
  const firstCorrect = quizzes.filter((q) => q.correct).length;
  const quizOk = quizzes.length === 0 || (answered.length === quizzes.length && firstCorrect / quizzes.length >= rules.quizRatio);
  const exercisesOk = exercises.every((x) => x.passedAt);
  const enoughEvidence = exercises.length > 0 || quizzes.length >= rules.minQuizItems;

  let competentAt = null;
  if (completedAt && enoughEvidence && exercisesOk && quizOk) {
    competentAt = maxIso([completedAt, ...exercises.map((x) => x.passedAt), ...answered.map((q) => q.answeredAt)]);
  }

  // Spaced review + mastery, replayed in time order after competence.
  let review = null;
  let masteredAt = null;
  const reviewable = quizzes.length >= rules.minReviewItems;
  if (competentAt) {
    let step = 0;
    let nextAt = addDays(competentAt, rules.intervalsDays[0]);
    const history = [];
    let practice = 0;
    for (const r of of("review_done").filter((e) => e.at >= competentAt)) {
      if (r.at < nextAt) { practice++; continue; } // not due yet (early or an immediate retake): practice, not evidence
      const success = r.total >= rules.minReviewItems && r.correct / r.total >= rules.quizRatio;
      step = success ? Math.min(step + 1, rules.intervalsDays.length - 1) : 0;
      nextAt = addDays(r.at, rules.intervalsDays[step]);
      if (success && !masteredAt && r.at >= addDays(competentAt, rules.masteryDelayDays)) masteredAt = r.at;
      if (!success) masteredAt = null; // later failure: mastery is reconsidered (spec §11.2)
      history.push({ at: r.at, correct: r.correct, total: r.total, success });
    }
    review = { reviewable, nextAt, history, practice };
  }

  return {
    id: lesson.id, started, completedAt, competentAt, masteredAt,
    status: masteredAt ? "MASTERED" : competentAt ? "COMPETENT" : completedAt ? "COMPLETED" : started ? "STARTED" : "NOT_STARTED",
    evidence: { exercises, quizzes, firstCorrect, enoughEvidence },
    review,
  };
}

export function derive(rawEvents, index, now, rules = RULES) {
  const events = sortEvents(rawEvents);
  const byItem = new Map();
  for (const e of events) {
    const key = e.item.split("#")[0].replace(/\.E\d+$/, ""); // quiz + exercise events belong to their lesson
    if (!byItem.has(key)) byItem.set(key, []);
    byItem.get(key).push(e);
  }
  const lessons = new Map(index.lessonOrder.map((id) => [id, deriveLesson(index.byId.get(id).item, byItem.get(id) ?? [], rules)]));

  const bookmarks = new Set();
  for (const e of events.filter((x) => x.type === "bookmark")) e.on ? bookmarks.add(e.item) : bookmarks.delete(e.item);

  const all = [...lessons.values()];
  const count = (pred) => all.filter(pred).length;
  return {
    lessons,
    bookmarks,
    totals: {
      defined: all.length,
      completed: count((l) => l.completedAt),
      competent: count((l) => l.competentAt),
      mastered: count((l) => l.masteredAt),
    },
    nextLesson: index.lessonOrder.find((id) => !lessons.get(id).completedAt) ?? null,
    due: all.filter((l) => l.review?.reviewable && l.review.nextAt <= now).map((l) => l.id),
    upcoming: all.filter((l) => l.review?.reviewable && l.review.nextAt > now).sort((a, b) => (a.review.nextAt < b.review.nextAt ? -1 : 1)).map((l) => l.id),
    recent: events.slice(-15).reverse(),
    count: events.length,
  };
}
