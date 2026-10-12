import json
import logging
import re

import ollama

log = logging.getLogger("aks_ats.experience")

MODEL = "qwen2.5:3b"
DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")

HEAD_RE = re.compile(r"^\s*(?:professional\s+|work\s+)?(?:experience|employment\s+history)\s*:?\s*$", re.I | re.M)
END_RE = re.compile(r"^\s*(?:education|certifications?|academic\s+background)\b", re.I | re.M)
ROLE_RE = re.compile(r"\b(?:role|title|position)\s*:", re.I)
BULLETS = ("-", "*", "\u2022", "\u25cf")

MON = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE = rf"(?:{MON}\s*)?\d{{4}}"
RANGE_RE = re.compile(
    rf"\b{DATE}\s*(?:-|\u2013|\u2014|to)\s*(?:{DATE}|present|current|till\s+date|ongoing)", re.I)

MONTHS = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
          "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
PRESENT_RE = re.compile(r"\b(present|current|till date|to date|ongoing)\b", re.I)

PROMPT = """You read the header of ONE job in a resume. Return ONLY JSON, no other text.
Format: {"company": str|null, "title": str|null, "start": "YYYY-MM"|"YYYY"|null, "end": "YYYY-MM"|"YYYY"|null}
Rules:
- Copy company and title exactly as written. Never invent or correct them.
- If a value is not written, use null.
- Use "end": null if the header says Present or Current.
- A line starting with Role: gives the title. The name before the colon on the date line is the company.

Job header:
"""


def split_jobs(text: str) -> list[str]:
    """One short header per job: the date-range line plus the Role: line above it, if any."""
    m = HEAD_RE.search(text)
    section = text[m.end():] if m else text
    e = END_RE.search(section)
    if e:
        section = section[:e.start()]
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
    headers = []
    for i, line in enumerate(lines):
        if len(line) > 220 or line.startswith(BULLETS) or not RANGE_RE.search(line):
            continue
        parts = [line]
        if i > 0:
            ms = list(ROLE_RE.finditer(lines[i - 1]))
            if ms:
                parts.insert(0, lines[i - 1][ms[-1].start():])
        headers.append("\n".join(parts)[:500])
    return headers


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


def extract_experiences(text: str) -> list[dict]:
    """Code finds each job header, the model reads it, code verifies against that header."""
    out = []
    for header in split_jobs(text)[:30]:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": PROMPT + header}],
            format="json",
            options={"temperature": 0, "num_ctx": 2048},
        )
        try:
            data = json.loads(resp["message"]["content"])
        except (json.JSONDecodeError, KeyError, TypeError):
            log.warning("Model returned unparseable output for a job header")
            continue
        if not isinstance(data, dict):
            continue
        low = _norm(header)
        company = data.get("company") if _in_text(data.get("company"), low) else None
        title = data.get("title") if _in_text(data.get("title"), low) else None
        if company is None and title is None:
            continue
        end = _verify_date(data.get("end"), header)
        out.append({
            "company": company.strip() if company else None,
            "title": title.strip() if title else None,
            "start": _verify_date(data.get("start"), header),
            "end": end,
            "is_current": end is None and bool(PRESENT_RE.search(header)),
        })
    return out