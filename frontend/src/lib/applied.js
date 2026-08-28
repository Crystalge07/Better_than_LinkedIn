export const APPLIED_STORAGE_KEY = "jobboard.appliedJobs";

export function loadAppliedJobs() {
  try {
    const raw = localStorage.getItem(APPLIED_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (job) => job && typeof job === "object" && typeof job.id === "string",
    );
  } catch {
    return [];
  }
}

export function saveAppliedJobs(jobs) {
  localStorage.setItem(APPLIED_STORAGE_KEY, JSON.stringify(jobs));
}

export function appliedJobId(link) {
  if (link) {
    return link;
  }
  return `manual:${crypto.randomUUID()}`;
}

export function appliedFromJob(job) {
  return {
    id: appliedJobId(job.apply_url),
    firm: job.company || "",
    location: Array.isArray(job.locations) ? job.locations.join(", ") : "",
    title: job.title || "",
    link: job.apply_url || "",
    appliedAt: new Date().toISOString(),
  };
}

export function upsertAppliedJob(jobs, incoming) {
  const index = jobs.findIndex((job) => job.id === incoming.id);
  if (index === -1) {
    return [incoming, ...jobs];
  }
  const existing = jobs[index];
  const next = [...jobs];
  next[index] = {
    id: existing.id,
    firm: existing.firm || incoming.firm,
    location: existing.location || incoming.location,
    title: existing.title || incoming.title,
    link: existing.link || incoming.link,
    appliedAt: existing.appliedAt,
  };
  return next;
}

export function removeAppliedJob(jobs, id) {
  return jobs.filter((job) => job.id !== id);
}

export function searchAppliedJobs(jobs, query) {
  const trimmed = query.trim().toLowerCase();
  const sorted = [...jobs].sort((left, right) =>
    right.appliedAt.localeCompare(left.appliedAt),
  );
  if (!trimmed) {
    return sorted;
  }
  const tokens = trimmed.split(/\s+/).filter(Boolean);
  return sorted.filter((job) => {
    const blob = [job.firm, job.title, job.location, job.link]
      .join(" ")
      .toLowerCase();
    return tokens.every((token) => blob.includes(token));
  });
}

export function displayLink(link) {
  try {
    const url = new URL(link);
    return `${url.hostname}${url.pathname}`.replace(/\/$/, "");
  } catch {
    return link || "—";
  }
}

export function formatAppliedDate(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function dateInputValue(iso) {
  const date = new Date(iso || Date.now());
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 10);
}

export function isoFromDateInput(value) {
  if (!value) {
    return new Date().toISOString();
  }
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return new Date().toISOString();
  }
  return date.toISOString();
}
