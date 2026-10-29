from datetime import date
from types import SimpleNamespace

from app.services.matching import (combine, experience_score, location_score, skills_score,
                                   recent_roles_score, title_score, visa_score)

assert title_score("TEST Backend Developer", ["Backend Developer"])[0] == 1.0
assert title_score("Platform Engineer", ["Software Engineer"])[0] == 0.5
assert title_score("Backend Developer", ["Data Engineer"])[0] == 0.0
assert title_score("Backend Developer", [])[0] is None
assert location_score("Dallas, TX", "Hybrid", "Austin, TX")[0] == 0.5
assert location_score("Dallas, TX", "Hybrid", "Dallas, TX")[0] == 1.0
assert location_score("Dallas, TX", "Hybrid", "Denver, CO")[0] == 0.0
assert location_score("Dallas, TX", "Remote", "Austin, TX")[0] is None
assert location_score("Dallas, TX", "Hybrid", None)[0] is None
role = SimpleNamespace(
    title="Backend Engineer", description="Built Python APIs using PostgreSQL and Redis.",
    start_date=date(2023, 1, 1), end_date=date(2025, 1, 1), is_current=False,
)
role_score, role_detail = recent_roles_score(
    "Build Python APIs using PostgreSQL and Redis.", [role], as_of=date(2026, 10, 29))
assert role_score is not None and role_score > 0.5
assert "overlapping keywords" in role_detail
old_role = SimpleNamespace(**{**vars(role), "end_date": date(2019, 1, 1)})
assert recent_roles_score(
    "Build Python APIs using PostgreSQL and Redis.", [old_role], as_of=date(2026, 10, 29)
)[0] is None
assert recent_roles_score("", [role])[0] is None
assert visa_score("USC or GC", None)[0] is None
assert visa_score("USC or GC", "GC")[0] == 1.0
assert visa_score("USC or GC", "H1B")[0] == 0.0
assert visa_score(None, "H1B")[0] is None
assert experience_score(7, 7.6)[0] == 1.0
assert round(experience_score(7, 3.5)[0], 2) == 0.5
assert experience_score(7, None)[0] is None
s, d, m, x = skills_score(["Python", "Amazon Web Services", "PostgreSQL"], ["Python", "Amazon Web Services", "Spark"])
assert round(s, 3) == 0.667 and x == ["PostgreSQL"]
score, cov, _ = combine({"a": 50, "b": 50}, {"a": (1.0, ""), "b": (None, "unknown")})
assert score == 100 and cov == 50.0
score, cov, _ = combine({"a": 50, "b": 50}, {"a": (None, ""), "b": (None, "")})
assert score is None and cov == 0.0
print("all scoring checks passed")