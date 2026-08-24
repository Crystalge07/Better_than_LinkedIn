import { useEffect, useState } from "react";

const DATE_PRESETS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "all", label: "All time" },
  { value: "custom", label: "Custom range" },
];

const DEFAULT_PRESET = "30";
const SEARCH_DEBOUNCE_MS = 300;

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function toIsoDate(date) {
  return date.toISOString().slice(0, 10);
}

function daysAgoIso(days) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return toIsoDate(date);
}

function buildJobsQuery({ q, title, location, datePreset, postedAfter, postedBefore }) {
  const params = new URLSearchParams();
  params.set("active_only", "true");
  params.set("open_only", "true");

  const search = q.trim();
  if (search) params.set("q", search);

  const titleTerm = title.trim();
  if (titleTerm) params.set("title", titleTerm);

  const locationTerm = location.trim();
  if (locationTerm) params.set("location", locationTerm);

  if (datePreset === "all") {
    // Explicit wide window so the API does not apply the 30-day default.
    params.set("posted_after", "2000-01-01");
  } else if (datePreset === "custom") {
    if (postedAfter) params.set("posted_after", postedAfter);
    if (postedBefore) params.set("posted_before", postedBefore);
  } else {
    params.set("posted_after", daysAgoIso(Number(datePreset)));
  }

  return params.toString();
}

export default function App() {
  const [q, setQ] = useState("");
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [datePreset, setDatePreset] = useState(DEFAULT_PRESET);
  const [postedAfter, setPostedAfter] = useState("");
  const [postedBefore, setPostedBefore] = useState("");

  const [debouncedQ, setDebouncedQ] = useState("");
  const [debouncedTitle, setDebouncedTitle] = useState("");
  const [debouncedLocation, setDebouncedLocation] = useState("");

  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTitle(title), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [title]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedLocation(location), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [location]);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      setLoading(true);
      setError(null);

      const query = buildJobsQuery({
        q: debouncedQ,
        title: debouncedTitle,
        location: debouncedLocation,
        datePreset,
        postedAfter,
        postedBefore,
      });

      try {
        const response = await fetch(`/api/jobs?${query}`);
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
  }, [
    debouncedQ,
    debouncedTitle,
    debouncedLocation,
    datePreset,
    postedAfter,
    postedBefore,
  ]);

  return (
    <main className="page">
      <h1>Job Aggregator</h1>
      <p className="subtitle">Internships and new-grad roles from community feeds and company career boards — not just tech</p>

      <form
        className="filters"
        onSubmit={(event) => event.preventDefault()}
      >
        <label className="filter-field">
          <span>Search</span>
          <input
            type="search"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Title or company"
            autoComplete="off"
          />
        </label>

        <label className="filter-field">
          <span>Role / title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="e.g. Firmware"
            autoComplete="off"
          />
        </label>

        <label className="filter-field">
          <span>Location</span>
          <input
            type="text"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="City or location"
            autoComplete="off"
          />
        </label>

        <label className="filter-field">
          <span>Date posted</span>
          <select
            value={datePreset}
            onChange={(event) => setDatePreset(event.target.value)}
          >
            {DATE_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {preset.label}
              </option>
            ))}
          </select>
        </label>

        {datePreset === "custom" && (
          <>
            <label className="filter-field">
              <span>From</span>
              <input
                type="date"
                value={postedAfter}
                onChange={(event) => setPostedAfter(event.target.value)}
              />
            </label>
            <label className="filter-field">
              <span>To</span>
              <input
                type="date"
                value={postedBefore}
                onChange={(event) => setPostedBefore(event.target.value)}
              />
            </label>
          </>
        )}
      </form>

      {/*
        Result count from jobs.length is a temporary shortcut valid only while
        there is no pagination. Switch to a real COUNT(*) (or response total)
        when pagination lands — response length will then be page size, not
        the full match set.
      */}
      {!loading && !error && (
        <p className="result-count" aria-live="polite">
          {jobs.length} {jobs.length === 1 ? "job" : "jobs"}
        </p>
      )}

      {loading && <div className="status loading">Loading jobs…</div>}
      {error && <div className="status error">{error}</div>}

      {!loading && !error && jobs.length === 0 && (
        <p className="empty">
          No jobs match these filters. Try widening the date range or clearing search.
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
