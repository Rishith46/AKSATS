from app.services.matching import (DEFAULT_WEIGHTS, combine, experience_gate, recommend,
                                   skill_status, skills_assessment)

Y = 2026
assert sum(DEFAULT_WEIGHTS.values()) == 100

# one skill, each state
assert skill_status(None, None, Y, 5)[:2] == (0.0, "missing")
assert skill_status({"years": None, "last_year": None}, None, Y, 5)[:2] == (0.5, "listed")
assert skill_status({"years": 3.0, "last_year": 2019}, None, Y, 5)[:2] == (0.4, "dated")
assert skill_status({"years": 3.0, "last_year": 2021}, None, Y, 5)[:2] == (1.0, "recent")
assert skill_status({"years": 3.0, "last_year": 2020}, None, Y, 5)[1] == "dated"
s, st, d = skill_status({"years": 2.0, "last_year": 2026}, 4, Y, 5)
assert st == "partial" and s == 0.5 and "2 of 4 years" in d
assert skill_status({"years": 5.0, "last_year": 2026}, 4, Y, 5)[:2] == (1.0, "recent")
assert skill_status({"years": 5.0, "last_year": 2026}, None, Y, 5)[1] == "recent"

# a skill list
have = {"Python": {"years": 6.0, "last_year": 2026, "evidence": "Built Python services."},
        "Docker": {"years": 3.0, "last_year": 2018, "evidence": "Used Docker."},
        "Java": {"years": None, "last_year": None, "evidence": "Java"}}
score, summary, rows = skills_assessment([("Python", None), ("Docker", None), ("Java", None), ("Spark", None)], have, Y)
assert [r["status"] for r in rows] == ["recent", "dated", "listed", "missing"]
assert abs(score - (1.0 + 0.4 + 0.5 + 0.0) / 4) < 1e-9
assert "3 of 4 found, 1 used in the last 5 years" == summary
assert rows[0]["evidence"] == "Built Python services." and rows[3]["evidence"] is None
assert skills_assessment([], have, Y)[0] is None

# the experience gate: strict by default, the job's required years
assert experience_gate(7, 6.7)[0] is True
assert experience_gate(7, 6.7)[1] == "6.7 years is below the required 7 years"
assert experience_gate(10, 9.9)[0] is True
assert experience_gate(10, 10)[0] is False
assert experience_gate(7, 7.6)[0] is False
assert experience_gate(10, None)[0] is False
assert experience_gate(None, 2)[0] is False
assert experience_gate(0, 2)[0] is False
assert experience_gate(10, 7.0, 0.7)[0] is False
assert experience_gate(10, 6.9, 0.7)[0] is True
assert "below the minimum of 7" in experience_gate(10, 5, 0.7)[1]
# recommendations
assert recommend(90, 80, False, "", [], [])[0] == "Strong consider"
assert recommend(90, 80, False, "", ["X"], [])[0] == "Consider"
assert recommend(70, 80, False, "", ["X", "Y"], [])[0] == "Borderline"
assert recommend(30, 80, False, "", [], [])[0] == "Not recommended"
assert recommend(95, 40, False, "", [], [])[0] == "Borderline"
assert recommend(95, 80, True, "5 years is below", [], [])[0] == "Not recommended"
assert recommend(None, 0, False, "", [], [])[0] == "Unable to determine"
lvl, why = recommend(95, 80, True, "5 years is below", [], [])
assert why == ["Experience: 5 years is below"]

# not-scored signals are listed, not counted as zero
sc, cov, br = combine(DEFAULT_WEIGHTS, {"required_skills": (1.0, ""), "preferred_skills": (None, ""),
                                         "relevant_experience": (1.0, ""), "job_title": (0.0, ""),
                                         "location": (None, ""), "visa": (None, "")})
assert br["recent_roles"]["score"] is None and "embeddings" in br["recent_roles"]["detail"]
assert sc == round(100 * (40 + 20 + 0) / (40 + 20 + 5)) and cov == 65.0
print("matcher v2 checks passed")