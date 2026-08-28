import { useEffect, useState } from "react";
import {
  dateInputValue,
  displayLink,
  isoFromDateInput,
  searchAppliedJobs,
} from "../lib/applied.js";
import { appliedJobId } from "../lib/applied.js";

const SEARCH_DEBOUNCE_MS = 180;

const EMPTY_DRAFT = {
  firm: "",
  location: "",
  title: "",
  link: "",
  appliedAt: "",
};

function SheetCell({ value, onCommit, type = "text", placeholder = "" }) {
  const [text, setText] = useState(value ?? "");

  useEffect(() => {
    setText(value ?? "");
  }, [value]);

  return (
    <input
      type={type}
      value={text}
      placeholder={placeholder}
      onChange={(event) => setText(event.target.value)}
      onBlur={() => {
        if (text !== (value ?? "")) {
          onCommit(text);
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.currentTarget.blur();
        }
      }}
    />
  );
}

export default function ApplicationsPage({ appliedJobs, onUpsert, onPatch, onRemove }) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [draft, setDraft] = useState({
    ...EMPTY_DRAFT,
    appliedAt: dateInputValue(new Date().toISOString()),
  });

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  const shown = searchAppliedJobs(appliedJobs, debouncedQuery);
  const searching = debouncedQuery.trim().length > 0;

  function commitDraft() {
    const firm = draft.firm.trim();
    const title = draft.title.trim();
    const link = draft.link.trim();
    if (!firm && !title && !link) {
      return;
    }
    onUpsert({
      id: appliedJobId(link || `manual:${title}:${firm}`),
      firm,
      location: draft.location.trim(),
      title,
      link,
      appliedAt: isoFromDateInput(draft.appliedAt),
    });
    setDraft({
      ...EMPTY_DRAFT,
      appliedAt: dateInputValue(new Date().toISOString()),
    });
  }

  return (
    <>
      <p className="subtitle">
        Spreadsheet of applications you submitted. When the ATS autofiller sees
        you press Submit on Greenhouse or Workday, a row is added here with firm,
        location, title, and link from that posting.
      </p>

      <input
        type="search"
        className="job-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search firm, title, location, or link"
        aria-label="Search applications"
      />

      <p className="result-count" aria-live="polite">
        {searching
          ? `${shown.length} of ${appliedJobs.length} applications`
          : `${appliedJobs.length} ${appliedJobs.length === 1 ? "application" : "applications"}`}
      </p>

      <div className="table-wrap sheet">
        <table className="jobs-table sheet-table">
          <thead>
            <tr>
              <th>Firm</th>
              <th>Location</th>
              <th>Title</th>
              <th>Link</th>
              <th>Date applied</th>
              <th> </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((job) => (
              <tr key={job.id}>
                <td>
                  <SheetCell
                    value={job.firm}
                    onCommit={(value) => onPatch(job.id, { firm: value })}
                  />
                </td>
                <td>
                  <SheetCell
                    value={job.location}
                    onCommit={(value) => onPatch(job.id, { location: value })}
                  />
                </td>
                <td>
                  <SheetCell
                    value={job.title}
                    onCommit={(value) => onPatch(job.id, { title: value })}
                  />
                </td>
                <td>
                  <SheetCell
                    value={job.link}
                    onCommit={(value) => onPatch(job.id, { link: value })}
                    type="url"
                  />
                  {job.link && !job.link.startsWith("manual:") ? (
                    <a
                      className="sheet-link"
                      href={job.link}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {displayLink(job.link)}
                    </a>
                  ) : null}
                </td>
                <td>
                  <SheetCell
                    type="date"
                    value={dateInputValue(job.appliedAt)}
                    onCommit={(value) =>
                      onPatch(job.id, { appliedAt: isoFromDateInput(value) })
                    }
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="linkish"
                    onClick={() => onRemove(job.id)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            <tr
              className="sheet-new"
              onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget)) {
                  commitDraft();
                }
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  commitDraft();
                }
              }}
            >
              <td>
                <input
                  value={draft.firm}
                  placeholder="Firm"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, firm: event.target.value }))
                  }
                />
              </td>
              <td>
                <input
                  value={draft.location}
                  placeholder="Location"
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      location: event.target.value,
                    }))
                  }
                />
              </td>
              <td>
                <input
                  value={draft.title}
                  placeholder="Title"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, title: event.target.value }))
                  }
                />
              </td>
              <td>
                <input
                  type="url"
                  value={draft.link}
                  placeholder="Link"
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, link: event.target.value }))
                  }
                />
              </td>
              <td>
                <input
                  type="date"
                  value={draft.appliedAt}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      appliedAt: event.target.value,
                    }))
                  }
                />
              </td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
    </>
  );
}
