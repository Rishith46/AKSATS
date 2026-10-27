from datetime import date
from decimal import Decimal

from app.services.skill_match import find_skills


def _merge(spans):
    spans = sorted(spans)
    merged = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def skill_history(roles, terms, today=None):
    """Per skill: years (merged role ranges that mention it), first/last year, and the bullet
    from the most recent such role. Assumes the skill was used throughout each role that
    mentions it, so years is an upper-bound estimate. Roles without usable dates are skipped."""
    today = today or date.today()
    spans, evidence = {}, {}
    for r in roles:
        start = r.get("start")
        end = today if r.get("is_current") else r.get("end")
        if not start or not end or end < start:
            continue
        text = "\n".join(x for x in (r.get("title"), r.get("description")) if x)
        if not text:
            continue
        for f in find_skills(text, terms):
            name = f["skill"]
            spans.setdefault(name, []).append((start, end))
            if name not in evidence or end > evidence[name][0]:
                evidence[name] = (end, f["evidence"])
    out = {}
    for name, sp in spans.items():
        merged = _merge(sp)
        days = sum((e - s).days for s, e in merged)
        out[name] = {
            "years": Decimal(str(round(days / 365.25, 1))),
            "first_year": merged[0][0].year,
            "last_year": max(e for _, e in merged).year,
            "evidence": evidence[name][1],
            "roles": len(sp),
        }
    return out