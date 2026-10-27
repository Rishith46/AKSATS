from app.services.experience_extract import split_jobs_with_bodies

# 1. internship listed inside the experience section: one job each, heading not swallowed
t1 = "\n".join([
    "PROFESSIONAL EXPERIENCE",
    "Alpha Co: Jan 2020 - Present (Location: Austin, TX)",
    "\u2022 Built things.",
    "INTERNSHIPS",
    "Role: Intern",
    "Beta Co: Jun 2018 - Aug 2018 (Location: Dallas, TX)",
    "\u2022 Learned things.",
    "EDUCATION",
    "BS CS, Some University, 2014 - 2018",
])
j = split_jobs_with_bodies(t1)
assert len(j) == 2, [h for h, _ in j]
assert j[0][1] == "Built things.", repr(j[0][1])
assert j[1][0].startswith("Role: Intern") and j[1][1] == "Learned things."

# 2. internships section AFTER education: still found, education dates are not a job
t2 = "\n".join([
    "PROFESSIONAL EXPERIENCE",
    "Alpha Co: Jan 2020 - Present (Location: Austin, TX)",
    "\u2022 Built things.",
    "EDUCATION",
    "BS CS, Some University, 2014 - 2018",
    "INTERNSHIPS",
    "Software Intern - Beta Co: Jun 2017 - Aug 2017",
    "\u2022 Learned.",
    "SKILLS",
    "Python, SQL",
])
j = split_jobs_with_bodies(t2)
assert len(j) == 2, [h for h, _ in j]
assert "Beta Co" in j[1][0] and j[1][1] == "Learned."
assert not any("2014" in h for h, _ in j)

# 3. an intern job under the experience heading is just a job
t3 = "\n".join([
    "WORK EXPERIENCE",
    "Software Engineering Intern | Gamma Inc | May 2013 \u2013 Aug 2013",
    "\u2022 Wrote tests.",
    "EDUCATION",
])
j = split_jobs_with_bodies(t3)
assert len(j) == 1 and "Intern" in j[0][0]

# 4. no internship heading: nothing changes
t4 = "PROFESSIONAL EXPERIENCE\nAlpha Co: Jan 2020 - Present\n\u2022 Built things.\nEDUCATION\nBS 2014 - 2018"
assert len(split_jobs_with_bodies(t4)) == 1

# 5. a wrapped sentence that starts with a heading word is not treated as a heading
t5 = "\n".join([
    "PROFESSIONAL EXPERIENCE",
    "Alpha Co: Jan 2020 - Present",
    "\u2022 Led delivery of work",
    "Projects were shipped on time.",
    "EDUCATION",
])
j = split_jobs_with_bodies(t5)
assert "Projects were shipped on time." in j[0][1], repr(j[0][1])
print("internship checks passed")