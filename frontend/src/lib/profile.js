export const PROFILE_STORAGE_KEY = "jobboard.profile";

const DEFAULT_CONFIDENCE = { high: 0.82, medium: 0.55 };

export function emptyAddress() {
  return {
    street1: "",
    street2: "",
    city: "",
    state: "",
    postalCode: "",
    country: "",
  };
}

export function emptyEducation() {
  return {
    school: "",
    degree: "",
    fieldOfStudy: "",
    startDate: "",
    endDate: "",
    currentlyEnrolled: false,
    gpa: "",
    gpaMax: "",
    location: "",
  };
}

export function emptyEmployment() {
  return {
    company: "",
    title: "",
    location: "",
    startDate: "",
    endDate: "",
    currentlyEmployed: false,
    description: "",
  };
}

export function emptyLanguage() {
  return { name: "", proficiency: "" };
}

export function emptyReference() {
  return { name: "", relationship: "", company: "", email: "", phone: "" };
}

export function emptyProfile() {
  return {
    identity: {
      legalFirstName: "",
      legalLastName: "",
      preferredFirstName: "",
      preferredLastName: "",
      middleName: "",
      suffix: "",
    },
    contact: {
      personalEmail: "",
      workEmail: "",
      personalPhone: "",
      workPhone: "",
    },
    addresses: {
      current: emptyAddress(),
      mailing: emptyAddress(),
      mailingSameAsCurrent: true,
    },
    workAuthorization: {
      authorizedToWorkUS: "",
      needSponsorshipNow: "",
      needSponsorshipFuture: "",
      citizenship: "",
      countriesAuthorized: "",
    },
    education: [],
    employment: [],
    links: {
      linkedin: "",
      github: "",
      portfolio: "",
      other: [],
    },
    languages: [],
    references: [],
    demographics: {
      raceEthnicity: "",
      gender: "",
      veteranStatus: "",
      disability: "",
      optIn: {
        raceEthnicity: false,
        gender: false,
        veteranStatus: false,
        disability: false,
      },
    },
    salary: {
      expectation: "",
      optIn: false,
    },
    confidence: { ...DEFAULT_CONFIDENCE },
  };
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function mergeObject(base, incoming) {
  if (!isObject(incoming)) {
    return base;
  }
  const next = { ...base };
  for (const key of Object.keys(base)) {
    if (!(key in incoming)) {
      continue;
    }
    const current = base[key];
    const value = incoming[key];
    if (Array.isArray(current)) {
      next[key] = Array.isArray(value) ? value : current;
    } else if (isObject(current)) {
      next[key] = mergeObject(current, value);
    } else if (value !== undefined) {
      next[key] = value;
    }
  }
  return next;
}

export function loadProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
    if (!raw) {
      return emptyProfile();
    }
    const parsed = JSON.parse(raw);
    const data = isObject(parsed?.profile) ? parsed.profile : parsed;
    return mergeObject(emptyProfile(), data);
  } catch {
    return emptyProfile();
  }
}

export function saveProfile(profile) {
  const envelope = {
    schemaVersion: 1,
    profile,
    legacy: {},
  };
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(envelope));
}
