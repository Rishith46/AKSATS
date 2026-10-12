from app.services.matching import (combine, experience_score, location_score, skills_score,
                                   title_score, visa_score)

assert title_score("TEST Backend Developer", ["Backend Developer"])[0] == 1.0
assert title_score("Platform Engineer", ["Software Engineer"])[0] == 0.5
assert title_score("Backend Developer", ["Data Engineer"])[0] == 0.0
assert title_score("Backend Developer", [])[0] is None
assert location_score("Dallas, TX", "Hybrid", "Austin, TX")[0] == 0.5
assert location_score("Dallas, TX", "Hybrid", "Dallas, TX")[0] == 1.0
assert location_score("Dallas, TX", "Hybrid", "Denver, CO")[0] == 0.0
assert location_score("Dallas, TX", "Remote", "Austin, TX")[0] is None
assert location_score("Dallas, TX", "Hybrid", None)[0] is None
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