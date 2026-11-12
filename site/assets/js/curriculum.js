// Pure curriculum index: no DOM. Tested in tests/js/.

export function buildIndex(data) {
  const byId = new Map();
  for (const course of data.courses) {
    byId.set(course.id, { kind: "course", item: course, parents: [] });
    for (const mod of course.modules) {
      byId.set(mod.id, { kind: "module", item: mod, parents: [course.id] });
      for (const lesson of mod.lessons) {
        byId.set(lesson.id, { kind: "lesson", item: lesson, parents: [course.id, mod.id] });
      }
    }
  }
  for (const p of data.projects) byId.set(p.id, { kind: "project", item: p, parents: [] });

  // Lessons in learning order: follow the module sequence, lessons in listed order.
  const lessonOrder = data.sequence
    .filter((id) => byId.get(id)?.kind === "module")
    .flatMap((id) => byId.get(id).item.lessons.map((l) => l.id));

  return { data, byId, lessonOrder };
}

export function get(index, id) {
  return index.byId.get(id) ?? null;
}

// [{id, title, kind}] from the course down to (and including) the item.
export function breadcrumbs(index, id) {
  const entry = index.byId.get(id);
  if (!entry) return [];
  return [...entry.parents, id].map((pid) => {
    const e = index.byId.get(pid);
    return { id: pid, title: e.item.title, kind: e.kind };
  });
}

export function lessonNeighbors(index, id) {
  const i = index.lessonOrder.indexOf(id);
  if (i === -1) return { prev: null, next: null };
  return {
    prev: index.lessonOrder[i - 1] ?? null,
    next: index.lessonOrder[i + 1] ?? null,
  };
}

// Case-insensitive match on id, title, outcomes. Ranked: id match, title match, outcome match.
export function search(index, query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const results = [];
  for (const [id, { kind, item }] of index.byId) {
    let rank = -1;
    if (id.toLowerCase().includes(q)) rank = 0;
    else if (item.title.toLowerCase().includes(q)) rank = 1;
    else if ((item.outcomes ?? []).some((o) => o.toLowerCase().includes(q))) rank = 2;
    if (rank >= 0) results.push({ id, kind, title: item.title, rank });
  }
  return results.sort((a, b) => a.rank - b.rank || a.id.localeCompare(b.id));
}

export function totalHours(index) {
  let modules = 0;
  for (const c of index.data.courses) for (const m of c.modules) modules += m.hours;
  const projects = index.data.projects.reduce((s, p) => s + p.hours, 0);
  return { modules, projects, total: modules + projects };
}

// Lowest non-null score per competency; "weak" means a demonstrated score of 1 or below.
export function weakCompetencies(assessment) {
  return assessment.competencies.filter((c) => {
    const scores = ["A", "B", "C", "D"].map((d) => c[d]).filter((v) => v !== null);
    return scores.length > 0 && Math.min(...scores) <= 1;
  });
}
