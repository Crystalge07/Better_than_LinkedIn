import { useEffect, useState } from "react";

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      try {
        const response = await fetch("/api/jobs");
        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }
        const data = await response.json();
        if (!cancelled) {
          setJobs(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load jobs");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadJobs();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <h1>Job Aggregator</h1>
      <p className="subtitle">Internship postings from the last 30 days</p>

      {loading && <div className="status loading">Loading jobs…</div>}
      {error && <div className="status error">{error}</div>}

      {!loading && !error && jobs.length === 0 && (
        <p className="empty">
          No jobs in the database yet. Run the ingest script to populate data.
        </p>
      )}

      {!loading && !error && jobs.length > 0 && (
        <ul className="job-list">
          {jobs.map((job) => (
            <li key={job.id} className="job-card">
              <h2>{job.title}</h2>
              <p className="company">{job.company}</p>
              <p className="meta">
                <span>{job.locations.join(" · ")}</span>
                <span>Posted {formatDate(job.date_posted)}</span>
                <span>{job.source}</span>
              </p>
              <a
                className="apply-link"
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Apply →
              </a>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
