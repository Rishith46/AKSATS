export type FormState = {
  fullName: string;
  email: string;
  phone: string;
  linkedin: string;
  city: string;
  state: string;
  country: string;
  visa: string;
  rate: string;
  rateUnit: string;
  availability: string;
};

export type ProfileFields = {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  visa_status: string | null;
  rate: string | null;
  rate_unit: string | null;
  availability: string | null;
};

const nextYear = () => new Date().getFullYear() + 1;

export function checkEmail(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(t) ? null : "Enter a valid email address";
}

export function checkPhone(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  const digits = t.replace(/\D/g, "");
  if (!/^[0-9+()\-.\s xX]+$/.test(t) || digits.length < 7 || digits.length > 15) return "Phone must have 7 to 15 digits";
  return null;
}

export function checkLinkedIn(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  return /linkedin\.com\//i.test(t) ? null : "Enter a linkedin.com address";
}

export function checkRate(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  const n = Number(t);
  return isNaN(n) || n < 0 || n > 1000000 ? "Rate must be a number from 0 to 1,000,000" : null;
}

export function checkPartialDate(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  const m = /^(\d{4})(?:-(0[1-9]|1[0-2]))?$/.exec(t);
  if (!m) return "Write the date as YYYY-MM or YYYY";
  const y = Number(m[1]);
  return y < 1950 || y > nextYear() ? "The year is out of range" : null;
}

export function checkYears(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  const n = Number(t);
  return isNaN(n) || n < 0 || n > 60 ? "Years must be from 0 to 60" : null;
}

export function checkLastYear(v: string): string | null {
  const t = v.trim();
  if (t === "") return null;
  const n = Number(t);
  return !Number.isInteger(n) || n < 1970 || n > nextYear() ? "Enter a four-digit year" : null;
}

export function formFromProfile(p: ProfileFields): FormState {
  return {
    fullName: p.full_name ?? "",
    email: p.email ?? "",
    phone: p.phone ?? "",
    linkedin: p.linkedin_url ?? "",
    city: p.city ?? "",
    state: p.state ?? "",
    country: p.country ?? "",
    visa: p.visa_status ?? "",
    rate: p.rate === null ? "" : String(Number(p.rate)),
    rateUnit: p.rate_unit ?? "hour",
    availability: p.availability ?? "",
  };
}

/** Only what changed, so an untouched field is never relabeled as confirmed. A blank value clears a field. */
export function buildPatch(a: FormState, b: FormState): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const text = (key: string, x: string, y: string) => {
    if (x.trim() !== y.trim()) out[key] = y.trim();
  };
  text("full_name", a.fullName, b.fullName);
  text("email", a.email, b.email);
  text("phone", a.phone, b.phone);
  text("linkedin_url", a.linkedin, b.linkedin);
  text("availability", a.availability, b.availability);
  text("visa_status", a.visa, b.visa);
  text("country", a.country, b.country);
  if (a.city.trim() !== b.city.trim() || a.state.trim() !== b.state.trim()) {
    out.city = b.city.trim();
    out.state = b.state.trim();
  }
  if (a.rate.trim() !== b.rate.trim()) out.rate = b.rate.trim() === "" ? null : Number(b.rate);
  if (a.rateUnit !== b.rateUnit) out.rate_unit = b.rateUnit;
  return out;
}