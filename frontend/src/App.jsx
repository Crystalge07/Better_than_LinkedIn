import { useEffect, useState } from "react";
import ApplicationsPage from "./pages/ApplicationsPage.jsx";
import JobsPage from "./pages/JobsPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import {
  deleteApplication,
  fetchApplications,
  migrateLocalApplications,
  patchApplication,
  upsertApplication,
} from "./lib/applicationsApi.js";

const PAGES = [
  { id: "jobs", label: "Jobs" },
  { id: "applications", label: "Applications" },
  { id: "profile", label: "Autofill profile" },
];
const POLL_MS = 2000;

function pageFromHash() {
  const hash = window.location.hash.replace(/^#/, "");
  return PAGES.some((page) => page.id === hash) ? hash : "jobs";
}

export default function App() {
  const [page, setPage] = useState(pageFromHash);
  const [appliedJobs, setAppliedJobs] = useState([]);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    if (!window.location.hash) {
      history.replaceState(null, "", "#jobs");
    }
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      if (document.activeElement?.closest(".sheet")) {
        return;
      }
      try {
        const jobs = await fetchApplications();
        if (!cancelled) {
          setAppliedJobs(jobs);
        }
      } catch {
        // Keep the last successful snapshot if the API blips.
      }
    }

    async function start() {
      try {
        await migrateLocalApplications();
      } catch {
        // First load can still poll the API even if migration fails.
      }
      await refresh();
    }

    start();
    const timer = window.setInterval(refresh, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  async function handleUpsert(incoming) {
    const saved = await upsertApplication(incoming);
    setAppliedJobs(await fetchApplications());
    return saved;
  }

  async function handlePatch(id, patch) {
    await patchApplication(id, patch);
    setAppliedJobs(await fetchApplications());
  }

  async function handleRemove(id) {
    await deleteApplication(id);
    setAppliedJobs(await fetchApplications());
  }

  return (
    <main className="page">
      <header className="app-header">
        <div className="brand">
          <span className="brand-pip" aria-hidden="true" />
          <h1>Job Aggregator</h1>
        </div>
        <nav>
          {PAGES.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              aria-current={page === item.id ? "page" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </header>

      {page === "jobs" && (
        <JobsPage
          appliedJobs={appliedJobs}
          onAppliedJobsChange={(incoming) => handleUpsert(incoming)}
        />
      )}
      {page === "applications" && (
        <ApplicationsPage
          appliedJobs={appliedJobs}
          onUpsert={handleUpsert}
          onPatch={handlePatch}
          onRemove={handleRemove}
        />
      )}
      {page === "profile" && <ProfilePage />}
    </main>
  );
}
