from datetime import date


def years_from(experiences, today=None):
    """Approximate total years covered by the jobs. Overlaps are counted once.
    Jobs without a usable start or end are skipped. Returns None if nothing is usable."""
    today = today or date.today()
    spans = []
    for e in experiences:
        s = e.get("start")
        if not s:
            continue
        end = today if e.get("is_current") else e.get("end")
        if not end or end < s:
            continue
        spans.append((s, end))
    if not spans:
        return None
    spans.sort()
    merged = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    days = sum((e - s).days for s, e in merged)
    return round(days / 365.25, 1)