const MIGRATED_KEY = "jobboard.appliedJobs.migrated";

function asJob(row) {
  if (!row || typeof row !== "object") {
    return null;
  }
  const appliedAt = row.appliedAt || row.applied_at;
  if (typeof row.id !== "string" || typeof appliedAt !== "string") {
    return null;
  }
  return {
    id: row.id,
    firm: row.firm || "",
    location: row.location || "",
    title: row.title || "",
    link: row.link || "",
    appliedAt,
  };
}

export async function fetchApplications() {
  const response = await fetch("/api/applications");
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  const data = await response.json();
  return Array.isArray(data) ? data.map(asJob).filter(Boolean) : [];
}

export async function upsertApplication(job) {
  const response = await fetch("/api/applications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(job),
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return asJob(await response.json());
}

export async function patchApplication(id, patch) {
  const response = await fetch(
    `/api/applications?id=${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    },
  );
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return asJob(await response.json());
}

export async function deleteApplication(id) {
  const response = await fetch(
    `/api/applications?id=${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
}

export async function migrateLocalApplications() {
  if (localStorage.getItem(MIGRATED_KEY)) {
    return;
  }
  let local = [];
  try {
    const raw = localStorage.getItem("jobboard.appliedJobs");
    local = raw ? JSON.parse(raw) : [];
  } catch {
    local = [];
  }
  if (!Array.isArray(local) || local.length === 0) {
    localStorage.setItem(MIGRATED_KEY, "1");
    return;
  }
  for (const job of local) {
    const parsed = asJob(job);
    if (parsed) {
      await upsertApplication(parsed);
    }
  }
  localStorage.setItem(MIGRATED_KEY, "1");
}

export function isJobApplied(job, appliedJobs) {
  const applyUrl = job.apply_url || "";
  return appliedJobs.some(
    (item) => item.id === applyUrl || item.link === applyUrl,
  );
}
