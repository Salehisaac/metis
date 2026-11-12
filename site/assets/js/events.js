// Learning-event schema v1: validation for stored records and imports. Pure (no DOM, no IndexedDB).
// Closed schema: unknown fields are dropped; no free text is ever stored (answers keep only correct/incorrect).

export const SCHEMA_VERSION = 1;
export const EXPORT_FORMAT = "metis-progress";
export const MAX_IMPORT_BYTES = 5_000_000;
export const MAX_EVENTS = 100_000;

const LESSON = /^[A-Z]+\.M\d{2}\.L\d{2}$/;
const ASSESSMENT = /^[A-Z]+\.M\d{2}\.A$/;
const EXERCISE = /^[A-Z]+\.M\d{2}\.L\d{2}\.E\d+$/;
const QUIZ_ITEM = /^[A-Z]+\.M\d{2}\.(L\d{2}|A)#[A-Za-z0-9_-]{1,40}$/;
const ANY_ITEM = /^[A-Za-z0-9.-]{1,40}$/; // bookmarks: course, module, lesson, project, exercise ids
const EVENT_ID = /^[A-Za-z0-9-]{8,64}$/;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;

const int = (v, max = 10_000) => Number.isInteger(v) && v >= 0 && v <= max;
const bool = (v) => typeof v === "boolean";

// type -> [item pattern, extra-field validators]
const TYPES = {
  lesson_started: [LESSON, {}],
  lesson_completed: [LESSON, {}],
  quiz_answer: [QUIZ_ITEM, { correct: bool }],
  review_done: [LESSON, { correct: int, total: int }],
  exercise_result: [EXERCISE, { passed: bool, tests: int, failures: int, errors: int, skipped: int, expected: int }],
  hint_viewed: [EXERCISE, { n: (v) => int(v, 10) && v >= 1 }],
  solution_viewed: [EXERCISE, {}],
  bookmark: [ANY_ITEM, { on: bool }],
};

// Returns { event } (a clean copy) or { error }.
export function validateEvent(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { error: "not an object" };
  const spec = TYPES[raw.type];
  if (!spec) return { error: `unknown type ${JSON.stringify(String(raw.type)).slice(0, 40)}` };
  const [itemPattern, fields] = spec;
  if (typeof raw.id !== "string" || !EVENT_ID.test(raw.id)) return { error: "bad id" };
  if (typeof raw.at !== "string" || !ISO.test(raw.at) || Number.isNaN(Date.parse(raw.at))) return { error: "bad timestamp" };
  if (typeof raw.item !== "string" || !itemPattern.test(raw.item)) return { error: `bad item for ${raw.type}` };
  const event = { id: raw.id, type: raw.type, at: raw.at, item: raw.item };
  for (const [k, ok] of Object.entries(fields)) {
    if (!ok(raw[k])) return { error: `bad ${k} for ${raw.type}` };
    event[k] = raw[k];
  }
  if (event.type === "review_done" && event.correct > event.total) return { error: "correct > total" };
  return { event };
}

export function sortEvents(events) {
  return [...events].sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

export function exportPayload(events, exportedAt) {
  return { format: EXPORT_FORMAT, schemaVersion: SCHEMA_VERSION, exportedAt, events: sortEvents(events) };
}

// All-or-nothing: returns { ok: true, events } or { ok: false, errors: [...] }. Events dated more than a day after
// `now` are rejected (a crafted file could otherwise backdate the clock-based rules).
export function parseImport(text, now = new Date().toISOString()) {
  if (typeof text !== "string") return { ok: false, errors: ["not text"] };
  if (text.length > MAX_IMPORT_BYTES) return { ok: false, errors: ["file is too large"] };
  let data;
  try { data = JSON.parse(text); } catch { return { ok: false, errors: ["not valid JSON"] }; }
  if (!data || data.format !== EXPORT_FORMAT) return { ok: false, errors: ["not a Metis progress export"] };
  if (data.schemaVersion > SCHEMA_VERSION) {
    return { ok: false, errors: [`exported by a newer version (schema ${data.schemaVersion}); this site reads up to ${SCHEMA_VERSION}`] };
  }
  if (data.schemaVersion !== SCHEMA_VERSION) return { ok: false, errors: ["unsupported schema version"] };
  if (!Array.isArray(data.events)) return { ok: false, errors: ["events missing"] };
  if (data.events.length > MAX_EVENTS) return { ok: false, errors: ["too many events"] };
  const events = [];
  const errors = [];
  data.events.forEach((raw, i) => {
    const r = validateEvent(raw);
    if (r.error) errors.push(`event ${i + 1}: ${r.error}`);
    else if (Date.parse(r.event.at) > Date.parse(now) + 86_400_000) errors.push(`event ${i + 1}: dated in the future`);
    else events.push(r.event);
  });
  return errors.length ? { ok: false, errors: errors.slice(0, 20) } : { ok: true, events: sortEvents(events) };
}
