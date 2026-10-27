from app.services.jd_read import read_jd
from app.services.skill_match import _pattern

SK = {"Power BI": ["PowerBI"], "Six Sigma": ["6 Sigma"], "Lean Manufacturing": ["Lean"],
      "Print Reading": ["Blueprints"], "Creo": [], "3D CAD": [], "SPC": ["Statistical SPC"],
      "Procurement": [], "Machining": [], "Supplier Management": []}
pairs = []
for n, al in SK.items():
    pairs += [(n, n)] + [(n, a) for a in al]
TERMS = [(n, t, _pattern(t)) for n, t in sorted(pairs, key=lambda x: -len(x[1]))]


def R(text):
    return read_jd(text, TERMS)


# pay: the top of a range, and a note when several figures appear
assert R("Title: X\nPay rate: $30-35/hr on W2")["rate"] == 35.0
d = R("Title: X\nPay rate: upto $35 for OPTs, around $40 for USCs")
assert d["rate"] == 40.0 and any("highest" in n for n in d["notes"])
assert R("Title: X\nPay Rate: upto $40/hr on C2C")["rate"] == 40.0

# years: the lower bound is the requirement; a desired line is not a requirement
assert R("Title: X\n- Years of experience: 5-7 years")["required_experience_years"] == 5.0
assert R("Title: X\n- Years of experience:  5+")["required_experience_years"] == 5.0
d = R("Title: X\n- 1 -4 years of mechanical design experience (Desired)")
assert d["required_experience_years"] is None and d["experience_desired_text"] and any("experience check" in n for n in d["notes"])

# required and preferred sections, with the markers these JDs use
d = R("Title: X\nAdditional Technical Skills\n(Required)\n- Machining\n(Desired)\n- Six sigma, lean")
assert d["required_skills"] == ["Machining"], d["required_skills"]
assert d["preferred_skills"] == ["Six Sigma", "Lean Manufacturing"], d["preferred_skills"]

# inline Required: and Desired: lines
d = R("Title: X\nTechnical Skills\nRequired: Machining and welding\nDesired: Creo/3D CAD, good communication.")
assert d["required_skills"] == ["Machining"] and d["preferred_skills"] == ["Creo", "3D CAD"]
assert "welding" in " ".join(d["unrecognized"]) and "communication" in " ".join(d["unrecognized"])

# soft skills are kept, not scored
d = R("Title: X\nTop 3 Skills\n- Supplier Management\nSoft Skills\n- Strong communication")
assert d["required_skills"] == ["Supplier Management"] and d["soft_skills"] == ["Strong communication"]

# a skill listed twice is kept once, as required
d = R("Title: X\nTop 3 Skills\n- Machining\n(Desired)\n- Machining, Procurement")
assert d["required_skills"] == ["Machining"] and d["preferred_skills"] == ["Procurement"]

# a line that matched something still shows what was matched, and a line that matched nothing is flagged
d = R("Title: X\nTop 3 Skills\n- Ability to read and interpret blueprints, technical drawings\n- Ability to multitask")
lines = {r["text"][:20]: r["skills"] for r in d["requirement_lines"]}
assert lines["Ability to read and "] == ["Print Reading"] and lines["Ability to multitask"] == []
assert "Ability to multitask" in d["unrecognized"]

# fields, internships, comparable titles, requisition id, other requirements
d = R("""4)Title: Mechanical Engineer 2- 114255-1
Location: Lafayette, IN
Work environment:
-  Office
Education & Experience Required:
-  4yr engineering degree (Required)
-  BSME (Desired)
-  Cat experience (Desired)
-  Do you accept internships as job experience:  Yes.
-  Are there past or additional job titles or roles that would provide comparable background to this role: Manufacturing Engineer, Process Engineer, Tool & dye maker
""")
assert d["title"] == "Mechanical Engineer 2" and d["requisition_id"] == "114255-1"
assert d["location"] == "Lafayette, IN" and d["work_mode"] == "Onsite"
assert d["accepts_internships"] is True
assert d["comparable_titles"] == ["Manufacturing Engineer", "Process Engineer", "Tool & dye maker"]
assert d["other_requirements"] == ["BSME (Desired)", "Cat experience (Desired)"], d["other_requirements"]
assert d["degree_notes"] == ["4yr engineering degree (Required)"]
assert R("Title: X\n- Do you accept internships as job experience: No")["accepts_internships"] is False

# nothing is invented when the text says nothing
d = R("Some paragraph that does not describe a job in any structured way at all.")
assert d["location"] is None and d["rate"] is None and d["required_experience_years"] is None
assert d["work_mode"] is None and d["accepts_internships"] is None
assert d["required_skills"] == [] and d["preferred_skills"] == []
assert R("Title: X\nWork environment: Remote or hybrid")["work_mode"] == "Remote"
# a (Required) marker under Soft Skills keeps those lines soft, not required
d = R("Title: X\nSoft Skills\n(Required)\n- Great written and oral communication.\nTop 3 Skills\n- Machining")
assert d["soft_skills"] == ["Great written and oral communication"], d["soft_skills"]
assert d["required_skills"] == ["Machining"] and d["unrecognized"] == []
print("job description reader checks passed")