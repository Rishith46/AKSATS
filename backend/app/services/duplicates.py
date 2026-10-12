import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidates import Candidate, CandidateDocument, DuplicateCandidate


def norm_phone(p):
    d = re.sub(r"\D", "", p or "")
    return d[-10:] if len(d) >= 10 else None


def norm_linkedin(u):
    if not u:
        return None
    m = re.search(r"linkedin\.com/in/([A-Za-z0-9_\-%]+)", u, re.I)
    return m.group(1).lower() if m else None


def find_by_hash(db: Session, sha: str):
    return db.scalar(select(CandidateDocument.candidate_id).where(CandidateDocument.sha256 == sha))


def find_matches(db: Session, cand: Candidate) -> dict[int, list[str]]:
    """Returns {other_candidate_id: [signals]}. Name alone is never a signal."""
    found: dict[int, list[str]] = {}
    email = (cand.email or "").strip().lower()
    phone = norm_phone(cand.phone)
    li = norm_linkedin(cand.linkedin_url)
    for o in db.scalars(select(Candidate).where(Candidate.id != cand.id,
                                                Candidate.merged_into_id.is_(None))):
        sig = []
        if email and (o.email or "").strip().lower() == email:
            sig.append("email")
        if phone and norm_phone(o.phone) == phone:
            sig.append("phone")
        if li and norm_linkedin(o.linkedin_url) == li:
            sig.append("linkedin")
        if sig:
            found[o.id] = sig
    return found


def record_pair(db: Session, a: int, b: int, signals: list[str]) -> None:
    lo, hi = sorted((a, b))
    if not db.scalar(select(DuplicateCandidate.id).where(
            DuplicateCandidate.candidate_a_id == lo, DuplicateCandidate.candidate_b_id == hi)):
        db.add(DuplicateCandidate(candidate_a_id=lo, candidate_b_id=hi,
                                  signals={"matched": signals}, confidence=1.0))