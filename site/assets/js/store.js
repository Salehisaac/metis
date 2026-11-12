// IndexedDB event store with a memory-only fallback. Invalid stored records are quarantined
// (excluded, counted, downloadable), never deleted automatically.
import { validateEvent, sortEvents } from "./events.js";

const DB_NAME = "metis";
const DB_VERSION = 1; // bump + add an upgrade step in onupgradeneeded for schema changes

function req(r) {
  return new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
}

function openDb() {
  return new Promise((resolve, reject) => {
    let r;
    try { r = indexedDB.open(DB_NAME, DB_VERSION); } catch (err) { reject(err); return; }
    r.onupgradeneeded = () => {
      const db = r.result;
      if (!db.objectStoreNames.contains("events")) db.createObjectStore("events", { keyPath: "id" });
      if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta", { keyPath: "key" });
    };
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
    r.onblocked = () => reject(new Error("database upgrade blocked by another open tab"));
  });
}

async function load(db) {
  const tx = db.transaction(["events", "meta"], "readonly");
  const [rawEvents, metaRows] = await Promise.all([req(tx.objectStore("events").getAll()), req(tx.objectStore("meta").getAll())]);
  const events = [];
  const quarantined = [];
  for (const raw of rawEvents) {
    const { event } = validateEvent(raw);
    if (event) events.push(event);
    else quarantined.push(raw && typeof raw === "object" ? raw : { value: raw });
  }
  const meta = {};
  for (const row of metaRows) if (row && typeof row.key === "string") meta[row.key] = row.value;
  return { events: sortEvents(events), quarantined, meta };
}

const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`);

export async function openStore() {
  const store = {
    persistent: false,
    reason: "",
    events: [],
    quarantined: [],
    meta: {},
    async add(type, item, extra = {}) {
      const { event, error } = validateEvent({ id: newId(), at: new Date().toISOString(), type, item, ...extra });
      if (error) throw new Error(`refusing to record invalid event: ${error}`);
      if (this.persistent) {
        try {
          await req(db.transaction("events", "readwrite").objectStore("events").add(event));
        } catch (err) {
          this.persistent = false;
          this.reason = `Saving failed (${err?.name ?? "error"}); progress is now kept in memory only.`;
        }
        if (!this.persistAsked && navigator.storage?.persist) { this.persistAsked = true; navigator.storage.persist().catch(() => {}); }
      }
      this.events.push(event);
      return event;
    },
    // All-or-nothing merge in one transaction; skips ids already present (including quarantined ones).
    async importEvents(events) {
      const known = new Set([...this.events.map((e) => e.id), ...this.quarantined.map((q) => q.id)]);
      const fresh = events.filter((e) => !known.has(e.id));
      if (this.persistent && fresh.length) {
        await new Promise((resolve, reject) => {
          const tx = db.transaction("events", "readwrite");
          const os = tx.objectStore("events");
          for (const e of fresh) os.add(e);
          tx.oncomplete = resolve;
          tx.onerror = () => reject(tx.error);
          tx.onabort = () => reject(tx.error ?? new Error("import aborted"));
        });
      }
      this.events = sortEvents([...this.events, ...fresh]);
      return { added: fresh.length, skipped: events.length - fresh.length };
    },
    // Re-read from IndexedDB (other tabs write too). Same validate-on-load path as opening.
    async refresh() {
      if (!this.persistent) return;
      try { Object.assign(this, await load(db)); } catch { /* keep current state */ }
    },
    async setMeta(key, value) {
      this.meta[key] = value;
      if (this.persistent) {
        try { await req(db.transaction("meta", "readwrite").objectStore("meta").put({ key, value })); } catch { /* non-critical */ }
      }
    },
  };

  let db;
  try {
    db = await openDb();
  } catch (err) {
    store.reason = err?.name === "VersionError"
      ? "Saved progress was written by a newer version of this site. It was left untouched; progress is kept in memory only."
      : "This browser doesn't allow saving here (storage blocked or unavailable). Progress is kept in memory only and is lost on reload.";
    return store;
  }
  db.onversionchange = () => {
    db.close();
    store.persistent = false;
    store.reason = "Another tab upgraded the saved data. Reload this tab to keep saving.";
  };
  try {
    Object.assign(store, await load(db));
    store.persistent = true;
  } catch {
    store.reason = "Saved progress couldn't be read. It was left untouched; progress is kept in memory only.";
  }
  return store;
}
