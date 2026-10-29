import json
import logging
import re

import ollama

log = logging.getLogger("aks_ats.experience")

MODEL = "qwen2.5:3b"
DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")

HEAD_RE = re.compile(
    r"^\s*(?:(?:professional|work|career|employment)\s+)?"
    r"(?:experience|history|employment\s+history|career\s+history|work\s+history)\s*:?\s*$",
    re.I | re.M,
)
END_RE = re.compile(
    r"^\s*(?:education|certifications?|academic\s+background|skills|technical\s+skills|"
    r"projects?|publications|awards|languages)\b", re.I | re.M)
INTERN_HEAD_RE = re.compile(
    r"^\s*(?:internships?|internship\s+experience|summer\s+internships?|industrial\s+training|trainee(?:ship)?)\s*:?\s*$",
    re.I | re.M)
SECTION_END_RE = re.compile(
    r"^\s*(?:education|certifications?|academic\s+background|projects?|technical\s+skills|skills|awards|achievements|references|publications)\b",
    re.I | re.M)
HEADING_ONLY_RE = re.compile(
    r"(?:internships?|internship\s+experience|summer\s+internships?|industrial\s+training|trainee(?:ship)?|"
    r"education|certifications?|academic\s+background|projects?|technical\s+skills|skills|awards|achievements|"
    r"references|publications)\s*:?",
    re.I)
ROLE_RE = re.compile(r"\b(?:role|title|position)\s*:", re.I)
ROLE_LINE_RE = re.compile(r"^\s*(?:role|title|position)\s*:", re.I)
LOC_RE = re.compile(r"\(\s*location\s*:[^()]*(?:\([^()]*\))?[^()]*\)", re.I)
BULLETS = ("-", "*", "\u2022", "\u25cf")
MAX_BODY = 30000

MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE = rf"(?:{MON}\s+\d{{4}}|\d{{1,2}}[/.-]\d{{4}}|\d{{4}}[/.-]\d{{1,2}}|\d{{4}})"
RANGE_RE = re.compile(
    rf"\b{DATE}\s*(?:-|\u2013|\u2014|to)\s*(?:{DATE}|present|current|till\s+date|ongoing)", re.I)

MONTHS = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
          "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
PRESENT_RE = re.compile(r"\b(present|current|till date|to date|ongoing)\b", re.I)
TITLE_WORDS = re.compile(
    r"\b(?:engineer|developer|analyst|architect|consultant|manager|designer|administrator|"
    r"specialist|director|intern|scientist|technician|coordinator|officer|lead)\b",
    re.I,
)

PROMPT = """You read the header of ONE job in a resume. Return ONLY JSON, no other text.
Format: {"company": str|null, "title": str|null, "start": "YYYY-MM"|"YYYY"|null, "end": "YYYY-MM"|"YYYY"|null}
Rules:
- Copy company and title exactly as written. Never invent or correct them.
- If a value is not written, use null.
- Use "end": null if the header says Present or Current.
- A line starting with Role: gives the title. The name before the colon on the date line is the company.

Job header:
"""


def _blocks(section: str) -> list[tuple[str, str]]:
    """(header, responsibilities) for every job found in a block of text."""
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
    date_rows = [(i, line) for i, line in enumerate(lines)
                 if len(line) <= 220 and not line.startswith(BULLETS) and RANGE_RE.search(line)]

    def role_header(line: str) -> bool:
        if (len(line) > 180 or line.startswith(BULLETS) or RANGE_RE.search(line)
                or line.lower().startswith(("environment:", "technical skills:", "skills:"))
                or re.search(r"[!?]|\.\s*$", line)):
            return False
        if ROLE_LINE_RE.match(line):
            return True
        if "|" in line and (TITLE_WORDS.search(line) or line.rstrip().endswith("|")):
            return True
        words = line.split()
        if len(words) > 10 or not TITLE_WORDS.search(line):
            return False
        return not re.match(
            r"^(?:i|we|they|he|she|built|led|developed|designed|managed|created|"
            r"improved|responsible|experience|worked|working|collaborated|implemented)\b",
            line, re.I,
        )

    headers = [i for i, line in enumerate(lines) if role_header(line)]
    assigned: list[tuple[int, int, str]] = []
    used_headers: set[int] = set()
    for date_index, date_line in date_rows:
        preceding = [i for i in headers if i not in used_headers and 0 <= date_index - i <= 18]
        following = [i for i in headers if i not in used_headers and 0 < i - date_index <= 3]
        header_index = max(preceding) if preceding else (min(following) if following else date_index)
        used_headers.add(header_index)
        assigned.append((header_index, date_index, date_line))

    assigned.sort()
    date_indexes = {i for i, _ in date_rows}
    out = []
    for n, (header_index, date_index, date_line) in enumerate(assigned):
        header_parts = []
        if header_index != date_index:
            header_parts.append(lines[header_index])
        header_parts.append(date_line)
        if header_index > 0 and not RANGE_RE.search(lines[header_index - 1]):
            previous = lines[header_index - 1]
            if (len(previous) <= 100 and not previous.startswith(BULLETS)
                    and not re.search(r"[!?]|\.\s*$", previous)
                    and not HEADING_ONLY_RE.fullmatch(previous)
                    and not previous.lower().startswith(("environment:", "professional experience"))):
                if "|" not in lines[header_index] and not ROLE_LINE_RE.match(lines[header_index]):
                    header_parts.insert(0, previous)
        header = "\n".join(dict.fromkeys(header_parts))[:500]

        end_index = assigned[n + 1][0] if n + 1 < len(assigned) else len(lines)
        body_lines = []
        for i in range(header_index + 1, end_index):
            line = lines[i]
            if i in date_indexes or RANGE_RE.search(line):
                continue
            if line.lower().startswith("environment:") or HEADING_ONLY_RE.fullmatch(line):
                continue
            if ROLE_LINE_RE.match(line):
                continue
            line = line.lstrip("-*\u2022\u25cf� ").strip()
            if line:
                body_lines.append(line)
        out.append((header, "\n".join(body_lines)[:MAX_BODY]))
    return out


def split_jobs_with_bodies(text: str) -> list[tuple[str, str]]:
    """Jobs from the experience section, plus any separate Internships section, which counts
    as experience too. Internship text that is already inside the experience section is not
    counted twice."""
    m = HEAD_RE.search(text)
    section = text[m.end():] if m else text
    e = END_RE.search(section)
    if e:
        section = section[:e.start()]
    jobs = _blocks(section)
    seen = {h for h, _ in jobs}
    for im in INTERN_HEAD_RE.finditer(text):
        rest = text[im.end():]
        em = SECTION_END_RE.search(rest)
        for h, b in _blocks(rest[:em.start()] if em else rest):
            if h not in seen:
                seen.add(h)
                jobs.append((h, b))
    return jobs


def split_jobs(text: str) -> list[str]:
    return [h for h, _ in split_jobs_with_bodies(text)]


def _norm(s: str) -> str:
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def _clean_date(v):
    if isinstance(v, str) and DATE_RE.match(v.strip()):
        return v.strip()
    return None


def _in_text(value, text_norm):
    return isinstance(value, str) and value.strip() != "" and _norm(value) in text_norm


def _verify_date(value, block: str):
    """Keep a date only as precisely as the header wrote it."""
    value = _clean_date(value)
    if not value:
        return None
    year = value[:4]
    if year not in block:
        return None
    if len(value) == 7:
        mon = value[5:7]
        names = [n for n, num in MONTHS.items() if num == mon]
        ok = any(re.search(n + r"[a-z]*\.?,?\s*" + year, block, re.I) for n in names) \
            or re.search(r"\b" + mon + r"[/\-]" + year, block) \
            or re.search(year + r"[/\-]" + mon, block)
        if not ok:
            return year
    return value


def _fallback_experience(header: str, body: str) -> dict | None:
    match = RANGE_RE.search(header)
    if not match:
        return None

    def normalized_date(raw: str) -> str | None:
        raw = raw.strip().lower().replace(".", "")
        month_match = re.fullmatch(r"(\d{1,2})[/.-](\d{4})", raw)
        if month_match:
            month, year = int(month_match.group(1)), month_match.group(2)
            return f"{year}-{month:02d}" if 1 <= month <= 12 else year
        year_month = re.fullmatch(r"(\d{4})[/.-](\d{1,2})", raw)
        if year_month:
            year, month = year_month.group(1), int(year_month.group(2))
            return f"{year}-{month:02d}" if 1 <= month <= 12 else year
        named_month = re.fullmatch(r"([a-z]+)\s+(\d{4})", raw, re.I)
        if named_month:
            month = MONTHS.get(named_month.group(1)[:3].lower())
            return f"{named_month.group(2)}-{month}" if month else named_month.group(2)
        return raw if re.fullmatch(r"\d{4}", raw) else None

    date_parts = re.split(r"\s*(?:-|\u2013|\u2014|to)\s*", match.group(0), maxsplit=1, flags=re.I)
    start = normalized_date(date_parts[0]) if date_parts else None
    end_raw = date_parts[1].strip() if len(date_parts) > 1 else ""
    current = bool(PRESENT_RE.search(end_raw))
    end = None if current else normalized_date(end_raw)

    separators = " \t|,-:\u2013\u2014"
    prefix = header[:match.start()]
    suffix = header[match.end():]
    details = [
        part.strip(separators)
        for part in re.split(r"\n|\s+\|\s+|\s+-\s+", f"{prefix} | {suffix}")
        if part.strip(separators)
    ]
    title = next((part for part in details if TITLE_WORDS.search(part)), None)
    company = next((part for part in details if part != title), None)
    if not title and not company:
        return None
    return {
        "company": company,
        "title": title,
        "start": start,
        "end": end,
        "is_current": current,
        "description": body or None,
    }


def extract_experiences(text: str) -> list[dict]:
    """Code finds each job header and its responsibilities, the model reads the header,
    code verifies the answer against that header."""
    out = []
    for header, body in split_jobs_with_bodies(text)[:30]:
        try:
            resp = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": PROMPT + header}],
                format="json",
                options={"temperature": 0, "num_ctx": 2048},
            )
            data = json.loads(resp["message"]["content"])
        except Exception as exc:
            log.warning("Model could not parse a job header (%s); using source-text fallback", exc)
            fallback = _fallback_experience(header, body)
            if fallback:
                out.append(fallback)
            continue
        if not isinstance(data, dict):
            fallback = _fallback_experience(header, body)
            if fallback:
                out.append(fallback)
            continue
        low = _norm(header)
        company = data.get("company") if _in_text(data.get("company"), low) else None
        title = data.get("title") if _in_text(data.get("title"), low) else None
        if company is None and title is None:
            fallback = _fallback_experience(header, body)
            if fallback:
                out.append(fallback)
            continue
        end = _verify_date(data.get("end"), header)
        out.append({
            "company": company.strip() if company else None,
            "title": title.strip() if title else None,
            "start": _verify_date(data.get("start"), header),
            "end": end,
            "is_current": end is None and bool(PRESENT_RE.search(header)),
            "description": body or None,
        })
    return out