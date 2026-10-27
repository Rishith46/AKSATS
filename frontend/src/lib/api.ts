export const API_URL = "http://127.0.0.1:8000";

export type Me = {
  id: number;
  email: string;
  full_name: string;
  designation: string | null;
  roles: string[];
  permissions: string[];
};

export async function login(email: string, password: string): Promise<string> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email.trim(), password }),
    });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new Error("Incorrect email or password");
  if (!res.ok) throw new Error("Sign-in failed. Please try again.");
  const data = await res.json();
  return data.access_token as string;
}

export async function fetchMe(token: string): Promise<Me> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (!res.ok) throw new Error("Session is no longer valid");
  return (await res.json()) as Me;
}
export type Candidate = {
  id: number;
  full_name: string | null;
  email: string | null;
  location: string | null;
  status: string;
  parse_status: string;
  archived_at: string | null;
  created_at: string;
};

export class SessionError extends Error {}

export async function listCandidates(token: string, includeArchived: boolean): Promise<Candidate[]> {
  let res: Response;
  try {
    res = await fetch(
      `${API_URL}/candidates?include_archived=${includeArchived}&limit=200`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) throw new Error("Could not load candidates");
  return (await res.json()) as Candidate[];
}
export type InboxItem = {
  id: number;
  filename: string;
  status: string;
  issues: { reason?: string } | null;
  candidate_id: number | null;
  received_at: string;
  processed_at: string | null;
};

export type InboxData = {
  total: number;
  by_status: Record<string, number>;
  items: InboxItem[];
};

export type UploadResult = {
  received: number;
  failed: number;
  items: { id: number; filename: string; status: string; issues: { reason?: string } | null }[];
};

export async function getInbox(token: string): Promise<InboxData> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/inbox?limit=100`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) throw new Error("Could not load the inbox");
  return (await res.json()) as InboxData;
}

export async function uploadResumes(token: string, files: File[]): Promise<UploadResult> {
  const body = new FormData();
  files.forEach((f) => body.append("files", f));
  let res: Response;
  try {
    res = await fetch(`${API_URL}/inbox/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body,
    });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) {
    let detail = "Upload failed";
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
    } catch {}
    throw new Error(detail);
  }
  return (await res.json()) as UploadResult;
}
export type Profile = {
  id: number;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  location: string | null;
  visa_status: string | null;
  rate: string | null;
  total_experience_years: string | null;
  status: string;
  parse_status: string;
  field_sources: Record<string, string>;
  archived_at: string | null;
  created_at: string;
  experiences: {
    id: number;
    company: string | null;
    title: string | null;
    start_date: string | null;
    start_precision: string | null;
    end_date: string | null;
    end_precision: string | null;
    is_current: boolean;
  }[];
  skills: { name: string; evidence: string | null; source: string }[];
  documents: {
    id: number;
    kind: string;
    filename: string;
    version_no: number | null;
    is_current: boolean;
    uploaded_at: string;
  }[];
};

export async function getProfile(token: string, id: number): Promise<Profile> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/candidates/${id}/profile`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (res.status === 404) throw new Error("This candidate no longer exists");
  if (!res.ok) throw new Error("Could not load the profile");
  return (await res.json()) as Profile;
}
export type Note = {
  id: number;
  candidate_id: number;
  author_id: number | null;
  body: string;
  created_at: string;
};

export async function listNotes(token: string, id: number): Promise<Note[]> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/candidates/${id}/notes`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) throw new Error("Could not load notes");
  return (await res.json()) as Note[];
}

export async function addNote(token: string, id: number, body: string): Promise<Note> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/candidates/${id}/notes`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (res.status === 403) throw new Error("You do not have permission to add notes");
  if (!res.ok) throw new Error("Could not save the note");
  return (await res.json()) as Note;
}
export type CandidateRow = Candidate & { total_experience_years: string | null; visa_status: string | null };

export type CandidateFilters = {
  q?: string;
  location?: string;
  title?: string;
  skills?: string[];
  minExperience?: number;
  visa?: string;
};

export async function listCandidatesFiltered(
  token: string,
  includeArchived: boolean,
  f: CandidateFilters
): Promise<CandidateRow[]> {
  const p = new URLSearchParams();
  p.set("include_archived", String(includeArchived));
  p.set("limit", "200");
  if (f.q) p.set("q", f.q);
  if (f.location) p.set("location", f.location);
  if (f.title) p.set("title", f.title);
  (f.skills ?? []).forEach((s) => p.append("skill", s));
  if (f.minExperience !== undefined) p.set("min_experience", String(f.minExperience));
  if (f.visa) p.set("visa", f.visa);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/candidates?${p.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) throw new Error("Could not load candidates");
  return (await res.json()) as CandidateRow[];
}
export type Job = {
  id: number;
  title: string;
  client: string | null;
  description: string | null;
  location: string | null;
  work_mode: string | null;
  required_experience_years: string | null;
  visa_requirements: string | null;
  rate: string | null;
  status: string;
  owner_id: number | null;
  created_at: string;
  updated_at: string;
  required_skills: string[];
  preferred_skills: string[];
};

export async function listJobs(token: string): Promise<Job[]> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/jobs?limit=200`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (!res.ok) throw new Error("Could not load jobs");
  return (await res.json()) as Job[];
}

export async function saveJob(token: string, id: number | null, payload: Record<string, unknown>): Promise<Job> {
  let res: Response;
  try {
    res = await fetch(id === null ? `${API_URL}/jobs` : `${API_URL}/jobs/${id}`, {
      method: id === null ? "POST" : "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (res.status === 403) throw new Error("You do not have permission to manage jobs");
  if (!res.ok) {
    let detail = "Could not save the job";
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (res.status === 422) detail = "Please check the fields and try again";
    } catch {}
    throw new Error(detail);
  }
  return (await res.json()) as Job;
}

export type MatchSignal = { score: number | null; weight: number; detail: string };

export type MatchSkill = { skill: string; evidence: string | null };

export type MatchCandidate = {
  candidate_id: number;
  full_name: string | null;
  parse_status: string;
  score: number | null;
  score_floor: number;
  coverage_percent: number;
  signals: Record<string, MatchSignal>;
  matching_required: MatchSkill[];
  missing_required: string[];
  matching_preferred: MatchSkill[];
  missing_preferred: string[];
  restrictions: { type: string; blocking: boolean }[];
};

export type MatchResult = {
  job_id: number;
  job_title: string;
  label: string;
  ranking: string;
  not_scored: string[];
  candidates: MatchCandidate[];
};

export async function getMatches(token: string, jobId: number): Promise<MatchResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/jobs/${jobId}/matches?limit=200`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (res.status === 403) throw new Error("You do not have permission to use matching");
  if (res.status === 404) throw new Error("This job no longer exists");
  if (!res.ok) throw new Error("Could not load matches");
  return (await res.json()) as MatchResult;
}
export type VisaOption = { value: string; label: string };

export async function getVisaOptions(token: string): Promise<VisaOption[]> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/meta/visa-statuses`, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    throw new Error("Cannot reach the server");
  }
  if (!res.ok) throw new Error("Could not load the visa list");
  return (await res.json()) as VisaOption[];
}