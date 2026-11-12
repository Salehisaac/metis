// Hash routes: #/view or #/view/ID or #/search?q=text. Pure; tested in tests/js/.

export const VIEWS = new Set([
  "dashboard", "roadmap", "courses", "course", "module", "lesson",
  "projects", "project", "profile", "search",
  "exercises", "exercise", "assessments", "assessment", "review", "revision", "history", "mentor", "data",
]);

export function parseHash(hash) {
  const raw = (hash || "").replace(/^#\/?/, "");
  const [pathPart, queryPart = ""] = raw.split("?");
  const [view = "", ...rest] = pathPart.split("/").map(decodeURIComponent);
  const query = Object.fromEntries(new URLSearchParams(queryPart));
  if (!view) return { view: "dashboard", id: null, query };
  if (!VIEWS.has(view)) return { view: "notfound", id: null, query };
  return { view, id: rest.join("/") || null, query };
}

export function href(view, id) {
  return id ? `#/${view}/${encodeURIComponent(id)}` : `#/${view}`;
}
