import re
from decimal import Decimal

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?)"
    r"\d{3,4}[\s.\-]?\d{3,4}(?:\s*(?:ext\.?|x)\s*\d{1,6})?(?!\d)", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9_\-%/]+", re.I)
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\u2019.\-]+[^\W\d_]+){0,4}\.?$", re.UNICODE)
LOCATION_RE = re.compile(r"\b([A-Z][a-zA-Z\. ]{2,30}),[ ]*([A-Z]{2})\b")
LABEL_RE = re.compile(r"^\s*(availability|work authorization|visa status|country|location)\s*:\s*(.+)$", re.I)
RATE_RE = re.compile(
    r"\b(?:rate|salary|compensation)\s*[:\-]?\s*[$€£]?\s*(\d{2,7}(?:,\d{3})*(?:\.\d{1,2})?)"
    r"\s*(/|per\s+)?\s*(hour|hr|year|annual|annually|yr)\b",
    re.I,
)
EXPERIENCE_RE = re.compile(
    r"\b(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+)?experience\b",
    re.I,
)

TITLE_WORDS = re.compile(
    r"\b(developer|engineer|manager|analyst|architect|consultant|resume|curriculum|vitae|"
    r"specialist|administrator|designer|lead|director|intern)\b", re.I)


def _first(rx, text):
    m = rx.search(text)
    return m.group(0).strip().rstrip("/") if m else None


def _name(lines: list[str]) -> str | None:
    ignored = {
        "resume", "curriculum vitae", "professional summary", "summary", "profile",
        "contact", "contact information", "work experience", "experience",
    }
    for line in lines[:12]:
        candidate = re.split(r"\s*(?:\||[—–])\s*|\s+-\s+", line, maxsplit=1)[0].strip(" ,:;-")
        if candidate.lower().startswith("name:"):
            candidate = candidate.split(":", 1)[1].strip()
        candidate = re.sub(r"\s+(?:https?://\S+|www\.\S+)$", "", candidate, flags=re.I)
        if "@" in candidate or any(ch.isdigit() for ch in candidate):
            continue
        if candidate.casefold() in ignored or not NAME_RE.fullmatch(candidate):
            continue
        if TITLE_WORDS.search(candidate):
            continue
        return candidate
    return None


def _phone(text: str) -> str | None:
    lines = text.splitlines()
    for line in lines[:15]:
        if re.search(r"\b(phone|mobile|telephone|tel)\b", line, re.I):
            match = PHONE_RE.search(line)
            if match:
                return match.group(0).strip()
    for line in lines[:12]:
        if re.search(r"\b(?:19|20)\d{2}\b", line):
            continue
        match = PHONE_RE.search(line)
        if match and 7 <= len(re.sub(r"\D", "", match.group(0)).split("ext")[0]) <= 15:
            return match.group(0).strip()
    return None


def extract_fields(text: str) -> dict:
    """Rule-based extraction. A value of None means 'Not Mentioned'. Nothing is guessed."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = lines[:15]
    head_text = "\n".join(head)

    name = _name(lines)

    location = None
    labeled = None
    for line in lines[:20]:
        match = LABEL_RE.match(line)
        if match and match.group(1).lower() == "location":
            labeled = match
            break
    m = None
    if labeled:
        location = labeled.group(2).strip(" ,|-")
    if m is None:
        m = LOCATION_RE.search("\n".join(lines[1:15]) if name else head_text)
    if m and location is None:
        location = f"{m.group(1).strip()}, {m.group(2)}"

    result = {
        "full_name": name,
        "email": _first(EMAIL_RE, text),
        "phone": _phone(text),
        "linkedin_url": _first(LINKEDIN_RE, text),
        "location": location,
        "country": None,
        "availability": None,
        "visa_status": None,
        "rate": None,
        "rate_unit": None,
        "total_experience_years": None,
    }
    for line in lines[:30]:
        label = LABEL_RE.match(line)
        if not label:
            continue
        key, value = label.group(1).lower(), label.group(2).strip()
        if key == "availability":
            result["availability"] = value[:200]
        elif key == "country":
            result["country"] = value[:100]
        elif key == "visa status":
            from app.visa import ALIASES, VISA_VALUES

            for visa in VISA_VALUES:
                if any(re.search(r"(?<![A-Za-z0-9-])" + re.escape(alias) + r"(?![A-Za-z0-9-])",
                                 value, re.I) for alias in ALIASES[visa]):
                    result["visa_status"] = visa
                    break
    rate = RATE_RE.search(text)
    if rate:
        result["rate"] = Decimal(rate.group(1).replace(",", ""))
        result["rate_unit"] = "year" if rate.group(3).lower() in {"year", "annual", "annually", "yr"} else "hour"
    experience = EXPERIENCE_RE.search(text)
    if experience:
        result["total_experience_years"] = Decimal(experience.group(1))
    return result