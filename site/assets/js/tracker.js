// Glue between the event store, the derived state and the pages.
import { derive } from "./progress.js";

export function createTracker(store, index) {
  const pageListeners = new Set(); // cleared on every navigation
  const globalListeners = new Set();
  let cached = null;

  const notify = () => {
    cached = null;
    for (const fn of [...pageListeners, ...globalListeners]) fn();
  };

  return {
    store,
    state() { return (cached ??= derive(store.events, index, new Date().toISOString())); },
    async record(type, item, extra) {
      try { await store.add(type, item, extra); } catch (err) { store.reason = `Not recorded: ${err.message}`; }
      notify();
    },
    changed: notify,
    on(fn) { pageListeners.add(fn); },
    always(fn) { globalListeners.add(fn); },
    reset() { pageListeners.clear(); cached = null; },
    // Hooks for quiz/exercise blocks inside a lesson or module assessment (itemId).
    hooksFor(itemId) {
      return {
        onAnswer: (q, correct) => this.record("quiz_answer", `${itemId}#${q.id}`, { correct }),
        onHint: (exId, n) => this.record("hint_viewed", exId, { n }),
        onSolution: (exId) => this.record("solution_viewed", exId),
        onResult: (ex, v) => this.record("exercise_result", ex.id, {
          passed: v.allPassed, tests: v.tests, failures: v.failures, errors: v.errors, skipped: v.skipped, expected: ex.tests.length,
        }),
      };
    },
  };
}
