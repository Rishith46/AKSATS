import re

STOP = {"test", "senior", "sr", "jr", "junior", "lead", "principal", "staff", "i", "ii", "iii",
        "the", "and", "of", "a"}
STATE_RE = re.compile(r",\s*([A-Za-z]{2})\b")

DEFAULT_WEIGHTS = {
    "required_skills": 25, "semantic_similarity": 30, "relevant_experience": 15,
    "recent_experience": 10, "job_title": 10, "location": 5, "visa": 5,
}

NOT_SCORED = {
    "semantic_similarity": "Not available yet: embeddings are not built",
    "recent_experience": "Not available yet: last-used year per skill is not captured",
}


def _words(t):
    return {w for w in re.findall(r"[a-z0-9+#]+", (t or "").lower()) if w not in STOP}


def title_score(job_title, titles):
    jw = _words(job_title)
    if not jw:
        return None, "Job title has no comparable words"
    titles = [t for t in titles if t]
    if not titles:
        return None, "No work-history titles"
    best, best_t = 0.0, None
    for t in titles:
        s = len(jw & _words(t)) / len(jw)
        if s > best or best_t is None:
            best, best_t = s, t
    return best, f"Closest title: {best_t}"


def _state(loc):
    m = STATE_RE.search(loc or "")
    return m.group(1).upper() if m else None


def _city(loc):
    return (loc or "").split(",")[0].strip().lower()


def location_score(job_loc, work_mode, cand_loc):
    if work_mode == "Remote":
        return None, "Remote job, location not scored"
    if not job_loc or not cand_loc:
        return None, "Location not mentioned"
    js, cs = _state(job_loc), _state(cand_loc)
    if _city(job_loc) == _city(cand_loc) and (js == cs or js is None or cs is None):
        return 1.0, "Same city"
    if js and cs and js == cs:
        return 0.5, "Same state, different city"
    return 0.0, "Different location"


def visa_score(job_visa, cand_visa):
    if not job_visa or not job_visa.strip():
        return None, "Job has no work authorization requirement"
    if not cand_visa or not cand_visa.strip():
        return None, "Candidate work authorization not mentioned"
    if cand_visa.strip().lower() in job_visa.lower():
        return 1.0, f"{cand_visa.strip()} is listed in the requirement"
    return 0.0, f"{cand_visa.strip()} is not listed in the requirement"


def experience_score(required, have):
    if required is None or float(required) <= 0:
        return None, "Job has no required experience"
    if have is None:
        return None, "Candidate experience could not be calculated"
    return min(float(have) / float(required), 1.0), f"{float(have)} of {float(required)} years"


def skills_score(required_names, have_names):
    if not required_names:
        return None, "Job has no required skills", [], []
    have = set(have_names)
    matching = [s for s in required_names if s in have]
    missing = [s for s in required_names if s not in have]
    return len(matching) / len(required_names), f"{len(matching)} of {len(required_names)} required skills", matching, missing


def combine(weights, signals):
    """signals: name -> (score or None, detail). Unknown signals are left out, not scored as zero."""
    total = sum(float(w) for w in weights.values())
    used = 0.0
    acc = 0.0
    out = {}
    for name, w in weights.items():
        score, detail = signals.get(name, (None, NOT_SCORED.get(name, "Not scored")))
        w = float(w)
        out[name] = {"score": None if score is None else round(score, 3), "weight": w, "detail": detail}
        if score is not None:
            used += w
            acc += w * score
    if used == 0:
        return None, 0.0, out
    coverage = round(100 * used / total, 1) if total else 0.0
    return round(100 * acc / used), coverage, out