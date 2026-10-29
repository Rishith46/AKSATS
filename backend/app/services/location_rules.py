from app.geo import is_us, split_location, state_code
from app.services.matching import location_score

PREFS = ("relocation_ok", "relocation_not_ok", "multiple")
LABELS = {"relocation_ok": "Relocation OK", "relocation_not_ok": "Relocation Not OK", "multiple": "Multiple locations"}


def _state_of(location):
    st = split_location(location)[1] if location else None
    return state_code(st) if st else None


def check_location(pref, job_location, locations, cand_location, cand_country):
    """(status, detail). status is not_applicable, eligible, ineligible or unknown.
    unknown means the location could not be confirmed, which never excludes a candidate.
    locations: objects with .city, .state and .relocation_ok."""
    if pref is None:
        return "not_applicable", "No location preference is set for this job"
    if cand_country is not None and not is_us(cand_country):
        return "ineligible", f"Candidate is in {cand_country}, outside the US"
    cstate = _state_of(cand_location)
    if pref == "relocation_ok":
        return "eligible", "Relocation OK: the candidate's location does not restrict eligibility"
    if pref == "relocation_not_ok":
        jstate = _state_of(job_location)
        if jstate is None:
            return "unknown", "The job location has no US state, so the location was not checked"
        if cstate is None:
            return "unknown", f"Candidate location not mentioned, so it cannot be confirmed that they are in {jstate}"
        if cstate == jstate:
            return "eligible", f"In {cstate}, the state this job is in"
        return "ineligible", f"Relocation not OK: candidate is in {cstate}, the job is in {jstate}"
    if pref == "multiple":
        if not locations:
            return "unknown", "The job lists no locations, so the location was not checked"
        if any(l.relocation_ok for l in locations):
            return "eligible", "At least one location is Relocation OK, so candidates from anywhere in the US qualify"
        states = sorted({state_code(l.state) for l in locations if state_code(l.state)})
        if cstate is None:
            return "unknown", f"Candidate location not mentioned; the job accepts candidates in {', '.join(states)}"
        if cstate in states:
            return "eligible", f"In {cstate}, one of the job's states"
        return "ineligible", f"Candidate is in {cstate}; the job accepts candidates in {', '.join(states)}"
    return "unknown", f"Unrecognized location preference: {pref}"


def location_signal(pref, job_location, work_mode, locations, cand_location):
    """(score or None, detail) for the small location factor in the match score."""
    if work_mode == "Remote":
        return None, "Remote job, location not scored"
    if pref is None or pref == "relocation_not_ok":
        return location_score(job_location, work_mode, cand_location)
    if pref == "relocation_ok":
        return 1.0, "Relocation OK: candidate is eligible regardless of current location"
    best = None
    cstate = _state_of(cand_location)
    for l in locations:
        if l.city:
            s, _ = location_score(f"{l.city}, {l.state}", work_mode, cand_location)
        else:
            s = None if cstate is None else (0.5 if cstate == state_code(l.state) else 0.0)
        if s is not None and (best is None or s > best):
            best = s
    if any(l.relocation_ok for l in locations):
        return 1.0, "Relocation OK: candidate is eligible for at least one job location"
    if best is None:
        return None, "Location not mentioned"
    return best, "Same city as a job location" if best == 1.0 else "Same state as a job location"