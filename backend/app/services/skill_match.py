import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidates import Skill, SkillAlias

CASE_SENSITIVE = {"Go", "ML", "TS", "JS", "PLC", "PLCs", "CPP"}


def _pattern(term: str) -> re.Pattern:
    flags = 0 if term in CASE_SENSITIVE else re.I
    return re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(term) + r"(?![A-Za-z0-9+#])", flags)


def load_terms(db: Session) -> list[tuple[str, str, re.Pattern]]:
    """Returns (canonical_name, term, pattern), longest terms first."""
    terms = []
    for s in db.scalars(select(Skill)).all():
        terms.append((s.name, s.name))
    for a, name in db.execute(select(SkillAlias.alias, Skill.name).join(Skill, Skill.id == SkillAlias.skill_id)).all():
        terms.append((name, a))
    terms.sort(key=lambda t: -len(t[1]))
    return [(name, term, _pattern(term)) for name, term in terms]


def _sentence(text: str, start: int, end: int) -> str:
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start))
    right_candidates = [i for i in (text.find("\n", end), text.find(". ", end)) if i != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right + 1].strip()[:300]


def find_skills(text: str, terms) -> list[dict]:
    """Longest terms are tried first. A shorter term does not count when the only
    place it appears is inside a span already claimed by a longer matched term."""
    found = {}
    claimed = []  # (start, end) spans already used by longer terms

    def overlaps(s, e):
        return any(s < ce and e > cs for cs, ce in claimed)

    for name, term, rx in terms:
        if name in found:
            continue
        for m in rx.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            claimed.append((m.start(), m.end()))
            found[name] = {"skill": name, "matched_as": m.group(0),
                           "evidence": _sentence(text, m.start(), m.end())}
            break
    return list(found.values())