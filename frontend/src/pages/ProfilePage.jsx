import { useState } from "react";
import {
  emptyEducation,
  emptyEmployment,
  emptyLanguage,
  emptyReference,
  loadProfile,
  saveProfile,
} from "../lib/profile.js";

function Field({ label, value, onChange, type = "text" }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Check({ label, checked, onChange }) {
  return (
    <label className="check-field">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}

function Tri({ label, value, onChange }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Leave blank</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    </label>
  );
}

function Repeating({ title, onAdd, children }) {
  return (
    <fieldset>
      <legend>{title}</legend>
      {children}
      <button type="button" onClick={onAdd}>
        Add {title.toLowerCase()}
      </button>
    </fieldset>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState(() => loadProfile());
  const [status, setStatus] = useState("");

  function update(path, value) {
    setProfile((current) => {
      const next = structuredClone(current);
      const keys = path.split(".");
      let cursor = next;
      for (const key of keys.slice(0, -1)) {
        cursor = cursor[key];
      }
      cursor[keys[keys.length - 1]] = value;
      return next;
    });
    setStatus("");
  }

  function patchList(key, index, field, value) {
    setProfile((current) => {
      const next = structuredClone(current);
      next[key][index][field] = value;
      return next;
    });
    setStatus("");
  }

  function addItem(key, factory) {
    setProfile((current) => ({
      ...structuredClone(current),
      [key]: [...current[key], factory()],
    }));
    setStatus("");
  }

  function addOtherLink() {
    setProfile((current) => {
      const next = structuredClone(current);
      next.links.other.push({ label: "", url: "" });
      return next;
    });
    setStatus("");
  }

  function handleSubmit(event) {
    event.preventDefault();
    const next = structuredClone(profile);
    if (next.addresses.mailingSameAsCurrent) {
      next.addresses.mailing = structuredClone(next.addresses.current);
    }
    saveProfile(next);
    setProfile(next);
    setStatus("Saved in this browser.");
  }

  const p = profile;
  const mailingHidden = p.addresses.mailingSameAsCurrent;

  return (
    <>
      <p className="subtitle">
        Fields used to fill Greenhouse and Workday applications. Stored only in
        this browser until accounts exist. EEO and salary stay unused unless you
        opt in.
      </p>

      <form id="profile-form" onSubmit={handleSubmit}>
        <fieldset>
          <legend>Identity</legend>
          <div className="row">
            <Field
              label="Legal first name"
              value={p.identity.legalFirstName}
              onChange={(value) => update("identity.legalFirstName", value)}
            />
            <Field
              label="Legal last name"
              value={p.identity.legalLastName}
              onChange={(value) => update("identity.legalLastName", value)}
            />
          </div>
          <div className="row">
            <Field
              label="Preferred first name"
              value={p.identity.preferredFirstName}
              onChange={(value) => update("identity.preferredFirstName", value)}
            />
            <Field
              label="Preferred last name"
              value={p.identity.preferredLastName}
              onChange={(value) => update("identity.preferredLastName", value)}
            />
          </div>
          <div className="row">
            <Field
              label="Middle name"
              value={p.identity.middleName}
              onChange={(value) => update("identity.middleName", value)}
            />
            <Field
              label="Suffix"
              value={p.identity.suffix}
              onChange={(value) => update("identity.suffix", value)}
            />
          </div>
        </fieldset>

        <fieldset>
          <legend>Contact</legend>
          <div className="row">
            <Field
              label="Personal email"
              type="email"
              value={p.contact.personalEmail}
              onChange={(value) => update("contact.personalEmail", value)}
            />
            <Field
              label="Work email"
              type="email"
              value={p.contact.workEmail}
              onChange={(value) => update("contact.workEmail", value)}
            />
          </div>
          <div className="row">
            <Field
              label="Personal phone"
              type="tel"
              value={p.contact.personalPhone}
              onChange={(value) => update("contact.personalPhone", value)}
            />
            <Field
              label="Work phone"
              type="tel"
              value={p.contact.workPhone}
              onChange={(value) => update("contact.workPhone", value)}
            />
          </div>
        </fieldset>

        <fieldset>
          <legend>Addresses</legend>
          <Field
            label="Street"
            value={p.addresses.current.street1}
            onChange={(value) => update("addresses.current.street1", value)}
          />
          <Field
            label="Street 2"
            value={p.addresses.current.street2}
            onChange={(value) => update("addresses.current.street2", value)}
          />
          <div className="row">
            <Field
              label="City"
              value={p.addresses.current.city}
              onChange={(value) => update("addresses.current.city", value)}
            />
            <Field
              label="State"
              value={p.addresses.current.state}
              onChange={(value) => update("addresses.current.state", value)}
            />
          </div>
          <div className="row">
            <Field
              label="Postal code"
              value={p.addresses.current.postalCode}
              onChange={(value) => update("addresses.current.postalCode", value)}
            />
            <Field
              label="Country"
              value={p.addresses.current.country}
              onChange={(value) => update("addresses.current.country", value)}
            />
          </div>
          <Check
            label="Mailing address is the same as current"
            checked={p.addresses.mailingSameAsCurrent}
            onChange={(value) => update("addresses.mailingSameAsCurrent", value)}
          />
          {!mailingHidden && (
            <>
              <Field
                label="Mailing street"
                value={p.addresses.mailing.street1}
                onChange={(value) => update("addresses.mailing.street1", value)}
              />
              <Field
                label="Mailing street 2"
                value={p.addresses.mailing.street2}
                onChange={(value) => update("addresses.mailing.street2", value)}
              />
              <div className="row">
                <Field
                  label="Mailing city"
                  value={p.addresses.mailing.city}
                  onChange={(value) => update("addresses.mailing.city", value)}
                />
                <Field
                  label="Mailing state"
                  value={p.addresses.mailing.state}
                  onChange={(value) => update("addresses.mailing.state", value)}
                />
              </div>
              <div className="row">
                <Field
                  label="Mailing postal code"
                  value={p.addresses.mailing.postalCode}
                  onChange={(value) =>
                    update("addresses.mailing.postalCode", value)
                  }
                />
                <Field
                  label="Mailing country"
                  value={p.addresses.mailing.country}
                  onChange={(value) => update("addresses.mailing.country", value)}
                />
              </div>
            </>
          )}
        </fieldset>

        <fieldset>
          <legend>Work authorization</legend>
          <Tri
            label="Authorized to work in the US"
            value={p.workAuthorization.authorizedToWorkUS}
            onChange={(value) =>
              update("workAuthorization.authorizedToWorkUS", value)
            }
          />
          <Tri
            label="Need sponsorship now"
            value={p.workAuthorization.needSponsorshipNow}
            onChange={(value) =>
              update("workAuthorization.needSponsorshipNow", value)
            }
          />
          <Tri
            label="Need sponsorship in the future"
            value={p.workAuthorization.needSponsorshipFuture}
            onChange={(value) =>
              update("workAuthorization.needSponsorshipFuture", value)
            }
          />
          <Field
            label="Citizenship"
            value={p.workAuthorization.citizenship}
            onChange={(value) => update("workAuthorization.citizenship", value)}
          />
          <Field
            label="Countries authorized (comma separated)"
            value={p.workAuthorization.countriesAuthorized}
            onChange={(value) =>
              update("workAuthorization.countriesAuthorized", value)
            }
          />
        </fieldset>

        <fieldset>
          <legend>Links</legend>
          <Field
            label="LinkedIn"
            type="url"
            value={p.links.linkedin}
            onChange={(value) => update("links.linkedin", value)}
          />
          <Field
            label="GitHub"
            type="url"
            value={p.links.github}
            onChange={(value) => update("links.github", value)}
          />
          <Field
            label="Portfolio"
            type="url"
            value={p.links.portfolio}
            onChange={(value) => update("links.portfolio", value)}
          />
        </fieldset>

        <Repeating
          title="Education"
          onAdd={() => addItem("education", emptyEducation)}
        >
          {p.education.map((item, index) => (
            <div key={`edu-${index}`} className="stack">
              <Field
                label={`School ${index + 1}`}
                value={item.school}
                onChange={(value) => patchList("education", index, "school", value)}
              />
              <Field
                label="Degree"
                value={item.degree}
                onChange={(value) => patchList("education", index, "degree", value)}
              />
              <Field
                label="Field of study"
                value={item.fieldOfStudy}
                onChange={(value) =>
                  patchList("education", index, "fieldOfStudy", value)
                }
              />
              <Field
                label="Location"
                value={item.location}
                onChange={(value) =>
                  patchList("education", index, "location", value)
                }
              />
              <div className="row">
                <Field
                  label="Start (YYYY-MM)"
                  value={item.startDate}
                  onChange={(value) =>
                    patchList("education", index, "startDate", value)
                  }
                />
                <Field
                  label="End (YYYY-MM)"
                  value={item.endDate}
                  onChange={(value) =>
                    patchList("education", index, "endDate", value)
                  }
                />
              </div>
              <div className="row">
                <Field
                  label="GPA"
                  value={item.gpa}
                  onChange={(value) => patchList("education", index, "gpa", value)}
                />
                <Field
                  label="GPA max"
                  value={item.gpaMax}
                  onChange={(value) =>
                    patchList("education", index, "gpaMax", value)
                  }
                />
              </div>
              <Check
                label="Currently enrolled"
                checked={item.currentlyEnrolled}
                onChange={(value) =>
                  patchList("education", index, "currentlyEnrolled", value)
                }
              />
            </div>
          ))}
        </Repeating>

        <Repeating
          title="Employment"
          onAdd={() => addItem("employment", emptyEmployment)}
        >
          {p.employment.map((item, index) => (
            <div key={`emp-${index}`} className="stack">
              <Field
                label={`Company ${index + 1}`}
                value={item.company}
                onChange={(value) =>
                  patchList("employment", index, "company", value)
                }
              />
              <Field
                label="Title"
                value={item.title}
                onChange={(value) => patchList("employment", index, "title", value)}
              />
              <Field
                label="Location"
                value={item.location}
                onChange={(value) =>
                  patchList("employment", index, "location", value)
                }
              />
              <div className="row">
                <Field
                  label="Start (YYYY-MM)"
                  value={item.startDate}
                  onChange={(value) =>
                    patchList("employment", index, "startDate", value)
                  }
                />
                <Field
                  label="End (YYYY-MM)"
                  value={item.endDate}
                  onChange={(value) =>
                    patchList("employment", index, "endDate", value)
                  }
                />
              </div>
              <Check
                label="Currently employed"
                checked={item.currentlyEmployed}
                onChange={(value) =>
                  patchList("employment", index, "currentlyEmployed", value)
                }
              />
              <label className="form-field">
                <span>Description</span>
                <textarea
                  value={item.description}
                  onChange={(event) =>
                    patchList("employment", index, "description", event.target.value)
                  }
                />
              </label>
            </div>
          ))}
        </Repeating>

        <Repeating
          title="Languages"
          onAdd={() => addItem("languages", emptyLanguage)}
        >
          {p.languages.map((item, index) => (
            <div key={`lang-${index}`} className="row">
              <Field
                label="Language"
                value={item.name}
                onChange={(value) => patchList("languages", index, "name", value)}
              />
              <Field
                label="Proficiency"
                value={item.proficiency}
                onChange={(value) =>
                  patchList("languages", index, "proficiency", value)
                }
              />
            </div>
          ))}
        </Repeating>

        <Repeating
          title="References"
          onAdd={() => addItem("references", emptyReference)}
        >
          {p.references.map((item, index) => (
            <div key={`ref-${index}`} className="stack">
              <Field
                label="Name"
                value={item.name}
                onChange={(value) => patchList("references", index, "name", value)}
              />
              <Field
                label="Relationship"
                value={item.relationship}
                onChange={(value) =>
                  patchList("references", index, "relationship", value)
                }
              />
              <Field
                label="Company"
                value={item.company}
                onChange={(value) =>
                  patchList("references", index, "company", value)
                }
              />
              <div className="row">
                <Field
                  label="Email"
                  type="email"
                  value={item.email}
                  onChange={(value) =>
                    patchList("references", index, "email", value)
                  }
                />
                <Field
                  label="Phone"
                  type="tel"
                  value={item.phone}
                  onChange={(value) =>
                    patchList("references", index, "phone", value)
                  }
                />
              </div>
            </div>
          ))}
        </Repeating>

        <Repeating title="Other links" onAdd={addOtherLink}>
          {p.links.other.map((item, index) => (
            <div key={`other-${index}`} className="row">
              <Field
                label="Label"
                value={item.label}
                onChange={(value) => {
                  setProfile((current) => {
                    const next = structuredClone(current);
                    next.links.other[index].label = value;
                    return next;
                  });
                  setStatus("");
                }}
              />
              <Field
                label="URL"
                type="url"
                value={item.url}
                onChange={(value) => {
                  setProfile((current) => {
                    const next = structuredClone(current);
                    next.links.other[index].url = value;
                    return next;
                  });
                  setStatus("");
                }}
              />
            </div>
          ))}
        </Repeating>

        <fieldset>
          <legend>EEO / demographics (opt-in)</legend>
          <p className="warning">
            These are never treated as fillable unless the matching opt-in is
            checked. Default is leave blank.
          </p>
          <Check
            label="Fill race / ethnicity"
            checked={p.demographics.optIn.raceEthnicity}
            onChange={(value) =>
              update("demographics.optIn.raceEthnicity", value)
            }
          />
          <Field
            label="Race / ethnicity"
            value={p.demographics.raceEthnicity}
            onChange={(value) => update("demographics.raceEthnicity", value)}
          />
          <Check
            label="Fill gender"
            checked={p.demographics.optIn.gender}
            onChange={(value) => update("demographics.optIn.gender", value)}
          />
          <Field
            label="Gender"
            value={p.demographics.gender}
            onChange={(value) => update("demographics.gender", value)}
          />
          <Check
            label="Fill veteran status"
            checked={p.demographics.optIn.veteranStatus}
            onChange={(value) => update("demographics.optIn.veteranStatus", value)}
          />
          <Field
            label="Veteran status"
            value={p.demographics.veteranStatus}
            onChange={(value) => update("demographics.veteranStatus", value)}
          />
          <Check
            label="Fill disability"
            checked={p.demographics.optIn.disability}
            onChange={(value) => update("demographics.optIn.disability", value)}
          />
          <Field
            label="Disability"
            value={p.demographics.disability}
            onChange={(value) => update("demographics.disability", value)}
          />
        </fieldset>

        <fieldset>
          <legend>Salary (opt-in)</legend>
          <Check
            label="Fill salary expectation"
            checked={p.salary.optIn}
            onChange={(value) => update("salary.optIn", value)}
          />
          <Field
            label="Salary expectation"
            value={p.salary.expectation}
            onChange={(value) => update("salary.expectation", value)}
          />
        </fieldset>

        <div className="actions">
          <button type="submit">Save profile</button>
        </div>
      </form>
      <p className="save-status" role="status">
        {status}
      </p>
    </>
  );
}