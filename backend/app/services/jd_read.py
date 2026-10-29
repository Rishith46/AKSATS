import re

from app.geo import state_code
from app.visa import VISA_VALUES, mentions

BULLET_RE = re.compile(r"^\s*[-\u2022\u00b7*]+\s*")
LEAD_NUM_RE = re.compile(r"^\s*\d+\)\s*")

REQ_HEAD = re.compile(
    r"^(?:top\s*\d*\s*skills?|(?:additional\s+)?technical\s+skills?(?:\s*&\s*requirements?)?|must\s+have|"
    r"(?:required|minimum|basic)\s+(?:skills?|qualifications?|requirements?|experience)|"
    r"(?:(?:technical\s+)?skills?|qualifications?|requirements?)\s+required|"
    r"skills?\s+and\s+(?:experience|qualifications?)|experience\s+and\s+qualifications?|"
    r"qualifications?|requirements?|skills?|"
    r"what\s+(?:you(?:'ll| will)|we(?:'re| are))\s+(?:need|bring|looking\s+for))$",
    re.I,
)
SOFT_HEAD = re.compile(r"^soft\s+skills?\b", re.I)
PREF_HEAD = re.compile(
    r"^(?:(?:preferred|desired|nice\s+to\s+have)\s+(?:skills?|qualifications?|requirements?|experience)|"
    r"(?:skills?|qualifications?|requirements?)\s+(?:preferred|desired))$",
    re.I,
)
MARK_REQ = re.compile(r"^\(?required\)?\s*:?\s*$", re.I)
MARK_PREF = re.compile(r"^\(?(?:desired|preferred|nice\s+to\s+have|plus)\)?\s*:?\s*$", re.I)
INLINE = re.compile(r"^(required|desired|preferred)\s*:\s*(.+)$", re.I)

FILLER = {"and", "or", "etc", "related", "other", "the", "a", "an", "experience", "knowledge", "skills",
          "ability", "expertise", "good", "strong", "excellent", "working", "with", "of", "in", "to"}


def scan(text, terms):
    """terms: (canonical name, term, compiled pattern), longest first. A shorter term does not count
    inside a span already claimed by a longer one. Returns (names in text order, claimed spans)."""
    claimed, found = [], []
    for name, _term, rx in terms:
        for m in rx.finditer(text):
            if any(m.start() < ce and m.end() > cs for cs, ce in claimed):
                continue
            claimed.append((m.start(), m.end()))
            found.append((m.start(), name))
    names = []
    for _, n in sorted(found):
        if n not in names:
            names.append(n)
    return names, claimed


def _leftover_tokens(text, spans):
    chars = list(text)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = ","
    out = []
    for tok in re.split(r"[,;()]| and ", "".join(chars)):
        tok = tok.strip(" .:-/")
        if len(tok) < 2 or len(tok.split()) > 5:
            continue
        words = [w for w in re.findall(r"[A-Za-z0-9+#&/'-]+", tok)]
        while words and words[0].lower() in FILLER:
            words.pop(0)
        while words and words[-1].lower() in FILLER:
            words.pop()
        if words:
            out.append(" ".join(words))
    return out


def _add(lst, x):
    key = re.sub(r"\s+", " ", x).strip().casefold()
    if not any(re.sub(r"\s+", " ", existing).strip().casefold() == key for existing in lst):
        lst.append(x)


def _set_title(d, title):
    title = title.strip()
    requisition = re.search(r"\s*-?\s*(\d{5,}(?:-\d+)?)\s*$", title)
    if requisition:
        d["requisition_id"] = requisition.group(1)
        title = title[:requisition.start()].rstrip(" -")
    d["title"] = title or None


def _location(value):
    value = re.sub(r"\s*\((?:remote|hybrid|on[\s-]?site)\)\s*$", "", value.strip(), flags=re.I)
    match = re.match(r"^\s*(.+?),\s*([A-Za-z .'-]+?)\s*$", value)
    if not match:
        return value or None
    state = state_code(match.group(2))
    return f"{match.group(1).strip()}, {state}" if state else value


def _work_mode(value):
    value = value.lower()
    if re.search(r"\bremote\b", value):
        return "Remote"
    if re.search(r"\bhybrid\b", value):
        return "Hybrid"
    if re.search(r"\bon[\s-]?site\b|\bin[\s-]?office\b|\boffice\b", value):
        return "Onsite"
    return None


def read_jd(text, terms):
    """Draft a job from pasted job-description text. Rules only, nothing is guessed: a field that is
    not written stays None, and skill words that are not in the skills list are returned for review."""
    lower_map = {t.lower(): n for n, t, _ in terms}
    lines = []
    for k, raw in enumerate([r for r in text.splitlines() if r.strip()]):
        s = raw.strip()
        if k == 0:
            s = LEAD_NUM_RE.sub("", s)
        bulleted = bool(BULLET_RE.match(s))
        t = BULLET_RE.sub("", s).strip()
        if t:
            lines.append((bulleted, t))

    d = {"title": None, "requisition_id": None, "client": None, "location": None, "work_mode": None,
         "rate": None, "rate_text": None, "required_experience_years": None, "experience_text": None,
         "experience_desired_text": None, "accepts_internships": None, "degree_notes": [],
         "comparable_titles": [], "required_skills": [], "preferred_skills": [], "soft_skills": [],
         "technical_skills": [],
         "visa_requirements": [],
         "mentioned_only": [], "unrecognized": [], "other_requirements": [], "requirement_lines": [],
         "notes": []}

    d["visa_requirements"] = [status for status in VISA_VALUES if mentions(text, status)]
    if "STEM-OPT" in d["visa_requirements"]:
        d["visa_requirements"].remove("OPT")
    for _, line in lines:
        m = re.match(r"^(?:(?:job|position)\s+)?(?:title|role|position)(?:\s+title)?\s*[:\-]\s*(.+)$",
                     line, re.I)
        if m:
            _set_title(d, m.group(1))
            break
    if d["title"] is None and lines:
        first = lines[0][1]
        generic_headers = {"job description", "position overview", "job overview", "about us",
                           "responsibilities", "qualifications", "requirements"}
        if (len(first) <= 100 and len(first.split()) <= 8 and
                ":" not in first and not re.search(r"[.!?]$", first) and first.lower() not in generic_headers and
                not re.match(r"^(we are|we're|about the|the role|the position)\b", first, re.I)):
            _set_title(d, first)

    for i, (_, t) in enumerate(lines):
        m = re.match(r"location\s*:\s*(.+)$", t, re.I)
        if m and d["location"] is None:
            d["location"] = _location(m.group(1))
            if d["work_mode"] is None:
                d["work_mode"] = _work_mode(m.group(1))
        m = re.match(r"client\s*:\s*(.+)$", t, re.I)
        if m and d["client"] is None:
            d["client"] = m.group(1).strip()
        m = re.match(r"(?:pay\s+)?rate\s*:\s*(.+)$", t, re.I)
        if m and d["rate_text"] is None:
            nums = [float(x) for pair in re.findall(
                r"\$\s*(\d+(?:\.\d+)?)(?:\s*[-\u2013]\s*\$?\s*(\d+(?:\.\d+)?))?", m.group(1)) for x in pair if x]
            d["rate_text"] = m.group(1).strip()
            if nums:
                d["rate"] = max(nums)
                if len(set(nums)) > 1:
                    d["notes"].append("Several pay figures are written (" + m.group(1).strip() + "); the highest was used. Check it.")
        m = re.match(r"(?:work\s+environment|work\s+arrangement|work\s+mode)\s*:?\s*(.*)$", t, re.I)
        if m and d["work_mode"] is None:
            val = m.group(1).strip() or (lines[i + 1][1] if i + 1 < len(lines) else "")
            d["work_mode"] = _work_mode(val)
        m = re.match(r"(?:required\s+)?experience\s*:\s*(.+)$", t, re.I)
        if m and d["required_experience_years"] is None:
            years = re.search(r"(\d+(?:\.\d+)?)\s*(?:[-\u2013\u2014]|\bto\b)?\s*\d*(?:\.\d+)?\s*years?", m.group(1), re.I)
            if years:
                d["required_experience_years"] = float(years.group(1))
                d["experience_text"] = t
        m = re.search(r"years?\s+of\s+experience\s*:\s*(\d+)\s*(?:(?:-|\u2013|to)\s*(\d+)|(\+))?", t, re.I)
        if m and d["required_experience_years"] is None:
            if re.search(r"\(desired\)", t, re.I):
                d["experience_desired_text"] = t
            else:
                d["required_experience_years"] = float(m.group(1))
                d["experience_text"] = t
        elif re.search(r"\d+\s*-\s*\d+\s*years?.*\(desired\)", t, re.I) and d["experience_desired_text"] is None:
            d["experience_desired_text"] = t
        m = re.search(r"accept\s+internships.*?:\s*(yes|no)\b", t, re.I)
        if m:
            d["accepts_internships"] = m.group(1).lower() == "yes"
        m = re.search(r"comparable\s+background\s+to\s+this\s+role\s*:\s*(.*)$", t, re.I)
        if m and m.group(1).strip():
            d["comparable_titles"] = [x.strip() for x in re.split(r"[;,]", m.group(1)) if x.strip()]
        if re.search(r"\bdegree\b", t, re.I) and len(t) < 200:
            _add(d["degree_notes"], t)

    if d["required_experience_years"] is None:
        d["notes"].append("No required years of experience were found, so the experience check will not apply."
                          + (" Desired: " + d["experience_desired_text"] if d["experience_desired_text"] else ""))

    bucket, desc = None, []
    technical_section = False
    for bulleted, t in lines:
        content = t
        if SOFT_HEAD.match(t):
            bucket = "soft"
            technical_section = False
            continue
        header, separator, inline_content = t.partition(":")
        header = header.strip()
        normalized_header = header.rstrip(" :-").lower()
        if normalized_header in {"key technical skills", "technical skills", "core technical skills"}:
            bucket = None
            technical_section = True
            if separator and inline_content.strip():
                d["technical_skills"].extend(_technical_skill_items(inline_content))
            continue
        if PREF_HEAD.fullmatch(header.rstrip(" :-")) or PREF_HEAD.fullmatch(t):
            bucket = "preferred"
            technical_section = False
            content = inline_content.strip() if separator else ""
            if not content:
                continue
        elif REQ_HEAD.fullmatch(header.rstrip(" :-")) or REQ_HEAD.fullmatch(t):
            bucket = "required"
            technical_section = False
            content = inline_content.strip() if separator else ""
            if not content:
                continue
        else:
            mi = INLINE.match(t)
            if mi:
                bucket = "required" if mi.group(1).lower() == "required" else "preferred"
                technical_section = False
                content = mi.group(2)
            elif MARK_REQ.match(t):
                if bucket != "soft":
                    bucket = "required"
                technical_section = False
                continue
            elif MARK_PREF.match(t):
                if bucket != "soft":
                    bucket = "preferred"
                technical_section = False
                continue
            elif technical_section and separator:
                d["technical_skills"].extend(_technical_skill_items(inline_content))
                recognized, _ = scan(inline_content, terms)
                for skill in recognized:
                    _add(d["technical_skills"], skill)
                continue
            elif not bulleted and _is_section_heading(t):
                bucket = None
                technical_section = False
        if bucket is None:
            desc.append(t)
            continue
        if bucket == "soft":
            _add(d["soft_skills"], content.rstrip("."))
            d["requirement_lines"].append({"bucket": "soft", "text": content.strip(), "skills": []})
            continue
        target = d["required_skills"] if bucket == "required" else d["preferred_skills"]
        names, spans = scan(content, terms)
        d["requirement_lines"].append({"bucket": bucket, "text": content.strip(), "skills": list(names)})
        for n in names:
            _add(target, n)
        if not names:
            if lower_map.get(content.strip(" .").lower()):
                _add(target, lower_map[content.strip(" .").lower()])
            else:
                _add(d["unrecognized"], content.strip().rstrip(".")[:160])
        elif (len(content) <= 90 and ("," in content or "(" in content)) or len(content) <= 40:
            for tok in _leftover_tokens(content, spans):
                if tok.lower() in lower_map:
                    _add(target, lower_map[tok.lower()])
                else:
                    _add(d["unrecognized"], tok)

    for n in list(d["preferred_skills"]):
        if n in d["required_skills"]:
            d["preferred_skills"].remove(n)
            d["notes"].append(f"{n} is listed as both required and preferred; kept as required.")
    for t in desc:
        if re.search(r"\((?:required|desired)\)", t, re.I) and t != d["experience_desired_text"] \
                and not re.search(r"\bdegree\b", t, re.I):
            _add(d["other_requirements"], t)
        names, _ = scan(t, terms)
        for n in names:
            if n not in d["required_skills"] and n not in d["preferred_skills"]:
                _add(d["mentioned_only"], n)
    for skill in scan(text, terms)[0]:
        if skill not in d["required_skills"] and skill not in d["preferred_skills"]:
            _add(d["mentioned_only"], skill)
    d["technical_skills"].extend(_hint_candidates(text))
    d["skill_suggestions"] = []
    for skill in (
        d["required_skills"] + d["preferred_skills"] + d["mentioned_only"] +
        [item for item in d["unrecognized"]
         if len(item) <= 80 and not re.search(r"[.!?]$", item)] +
        d["technical_skills"]
    ):
        _add(d["skill_suggestions"], skill)
    return d


def _technical_skill_items(text):
    return [
        item.strip(" \t.,;:-")
        for item in re.split(r"[,;]|\s+\band\b\s+", text, flags=re.I)
        if len(item.strip(" \t.,;:-")) >= 2
    ]


def _hint_candidates(text):
    cues = re.compile(
        r"\b(?:including|such as|tools?\s+like|skills?\s+in|experience\s+with|"
        r"proficiency\s+in|knowledge\s+of|familiarity\s+with|working\s+knowledge\s+of|"
        r"using|built\s+with)\s+(.+?)(?=[.;]|,\s*(?:with|including|and\s+experience)\b|$)",
        re.I,
    )
    suggestions = []
    for match in cues.finditer(text):
        phrase = match.group(1).strip(" \t,")
        for item in re.split(r"\s*,\s*|\s+(?:and/or|and|or)\s+", phrase, flags=re.I):
            candidate = item.strip(" \t.,;:-")
            candidate = re.sub(r"^(?:and/or|and|or)\s+", "", candidate, flags=re.I)
            candidate = re.sub(r"\s+(?:and/or|and|or)$", "", candidate, flags=re.I)
            words = candidate.split()
            if 1 <= len(words) <= 5 and not candidate.lower().startswith(
                ("experience ", "with ", "to ", "that ", "the ", "a ", "an ", "for ")
            ):
                _add(suggestions, candidate)
    return suggestions


def _is_section_heading(text):
    normalized = text.strip().rstrip(":").lower()
    return normalized in {
        "job description", "key responsibilities", "responsibilities", "what you will do",
        "what you'll do", "preferred qualifications", "key technical skills",
        "ideal candidate profile", "about the role", "about the job", "benefits",
        "employment type", "experience level",
    }