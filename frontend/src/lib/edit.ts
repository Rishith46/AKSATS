import { API_URL, SessionError } from "@/lib/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export type FullProfile = {
  id: number;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  location: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  availability: string | null;
  visa_status: string | null;
  rate: string | null;
  rate_unit: string | null;
  total_experience_years: string | null;
  field_sources: Record<string, string>;
  skills: {
    skill_id: number; name: string; source: string; years: number | null;
    last_used_year: number | null; evidence: string | null;
  }[];
  experiences: {
    id: number;
    company: string | null;
    title: string | null;
    location: string | null;
    start: string | null;
    end: string | null;
    is_current: boolean;
    description: string | null;
  }[];
};

export type SkillOut = {
  skill_id: number; name: string; years: number | null; last_used_year: number | null;
  source: string; evidence: string | null; created: boolean;
};
export type ExpResult = { total_experience_years: string | null };

function messageOf(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = Array.isArray(d?.loc) ? d.loc.filter((x: unknown) => x !== "body").join(" ") : "";
        const msg = String(d?.msg ?? "Invalid value").replace(/^Value error, /, "");
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join("; ");
  }
  return "The request was refused";
}

async function call<T>(token: string, method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server", 0);
  }
  if (res.status === 401) throw new SessionError("Your session has expired");
  if (res.status === 403) throw new ApiError("You do not have permission to do that", 403);
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = (await res.json()).detail;
    } catch {}
    throw new ApiError(messageOf(detail), res.status);
  }
  return (await res.json()) as T;
}

export const getFullProfile = (token: string, id: number) =>
  call<FullProfile>(token, "GET", `/candidates/${id}/profile`);
export const patchCandidate = (token: string, id: number, body: Record<string, unknown>) =>
  call<unknown>(token, "PATCH", `/candidates/${id}`, body);
export const addSkill = (token: string, id: number, body: Record<string, unknown>) =>
  call<SkillOut>(token, "POST", `/candidates/${id}/skills`, body);
export const removeSkill = (token: string, id: number, skillId: number) =>
  call<{ removed: string; note: string | null }>(token, "DELETE", `/candidates/${id}/skills/${skillId}`);
export const addExperience = (token: string, id: number, body: Record<string, unknown>) =>
  call<ExpResult>(token, "POST", `/candidates/${id}/experiences`, body);
export const editExperience = (token: string, id: number, eid: number, body: Record<string, unknown>) =>
  call<ExpResult>(token, "PATCH", `/candidates/${id}/experiences/${eid}`, body);
export const removeExperience = (token: string, id: number, eid: number) =>
  call<ExpResult>(token, "DELETE", `/candidates/${id}/experiences/${eid}`);