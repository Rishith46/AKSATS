import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_\-%]+/?", re.I)
NAME_RE = re.compile(r"^[A-Z][a-zA-Z'\-\.]+(?:\s+[A-Z][a-zA-Z'\-\.]+){1,3}$")
LOCATION_RE = re.compile(r"\b([A-Z][a-zA-Z\. ]{2,30}),[ ]*([A-Z]{2})\b")


TITLE_WORDS = re.compile(
    r"\b(developer|engineer|manager|analyst|architect|consultant|resume|curriculum|vitae|"
    r"specialist|administrator|designer|lead|director|intern)\b", re.I)


def _first(rx, text):
    m = rx.search(text)
    return m.group(0).strip().rstrip("/") if m else None


def extract_fields(text: str) -> dict:
    """Rule-based extraction. A value of None means 'Not Mentioned'. Nothing is guessed."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = lines[:15]
    head_text = "\n".join(head)

    name = None
    if lines:
        first = lines[0]
        lm = re.search(r"\s+([A-Z][a-zA-Z\.]+),[ ]*[A-Z]{2}\b", first)
        if lm:
            first = first[:lm.start()].strip(" ,|-")
            if len(first.split()) > 3:
                first = ""
        if NAME_RE.match(first) and not TITLE_WORDS.search(first):
            name = first

    location = None
    m = None
    if name and lines and lines[0].startswith(name) and lines[0][len(name):].strip(" ,|-"):
        m = re.search(r"([A-Z][a-zA-Z\.]+),[ ]*([A-Z]{2})\b", lines[0][len(name):])
    if m is None:
        m = LOCATION_RE.search("\n".join(lines[1:15]) if name else head_text)
    if m:
        location = f"{m.group(1).strip()}, {m.group(2)}"

    return {
        "full_name": name,
        "email": _first(EMAIL_RE, text),
        "phone": _first(PHONE_RE, text),
        "linkedin_url": _first(LINKEDIN_RE, text),
        "location": location,
    }