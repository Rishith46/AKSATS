import re

BULLET_RE = re.compile(r"^\s*[-\u2022\u00b7*]+\s*")
LEAD_NUM_RE = re.compile(r"^\s*\d+\)\s*")

REQ_HEAD = re.compile(r"^(?:top\s*\d*\s*skills?|(?:additional\s+)?technical\s+skills?|required\s+skills?|must\s+have)\b", re.I)
SOFT_HEAD = re.compile(r"^soft\s+skills?\b", re.I)
PREF_HEAD = re.compile(r"^(?:preferred|desired|nice\s+to\s+have)\s+skills?\b", re.I)
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
    if x not in lst:
        lst.append(x)


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
         "mentioned_only": [], "unrecognized": [], "other_requirements": [], "requirement_lines": [],
         "notes": []}

    for i, (_, t) in enumerate(lines):
        m = re.match(r"title\s*:\s*(.+)$", t, re.I)
        if m and d["title"] is None:
            title = m.group(1).strip()
            r = re.search(r"\s*-?\s*(\d{5,}(?:-\d+)?)\s*$", title)
            if r:
                d["requisition_id"] = r.group(1)
                title = title[:r.start()].rstrip(" -")
            d["title"] = title
        m = re.match(r"location\s*:\s*(.+)$", t, re.I)
        if m and d["location"] is None and re.search(r"[A-Za-z .'-]+,\s*[A-Z]{2}\b", m.group(1)):
            d["location"] = m.group(1).strip()
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
        m = re.match(r"work\s+environment\s*:?\s*(.*)$", t, re.I)
        if m and d["work_mode"] is None:
            val = m.group(1).strip() or (lines[i + 1][1] if i + 1 < len(lines) else "")
            if re.search(r"remote", val, re.I):
                d["work_mode"] = "Remote"
            elif re.search(r"hybrid", val, re.I):
                d["work_mode"] = "Hybrid"
            elif re.search(r"office|factory|plant|shop|floor|manufacturing", val, re.I):
                d["work_mode"] = "Onsite"
                d["notes"].append(f"Work mode is Onsite, taken from the work environment text: {val}")
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
    for bulleted, t in lines:
        content = t
        if SOFT_HEAD.match(t):
            bucket = "soft"
            continue
        if PREF_HEAD.match(t):
            bucket = "preferred"
            continue
        if REQ_HEAD.match(t):
            bucket = "required"
            continue
        mi = INLINE.match(t)
        if mi:
            bucket = "required" if mi.group(1).lower() == "required" else "preferred"
            content = mi.group(2)
        elif MARK_REQ.match(t):
            if bucket != "soft":
                bucket = "required"
            continue
        elif MARK_PREF.match(t):
            if bucket != "soft":
                bucket = "preferred"
            continue
        elif bucket is not None and not bulleted:
            bucket = None
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
    return d