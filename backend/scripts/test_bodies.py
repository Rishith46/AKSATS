from app.services.experience_extract import split_jobs_with_bodies

text = "\n".join([
    "PROFESSIONAL EXPERIENCE",
    "Role: Sr. Developer",
    "Alpha Test Co: OCT 2025 \u2013 Present (Location: Austin, TX (Remote))",
    "\u2022 Built things for customers",
    "and kept them running.",
    "\u2022 More things.",
    "Environment: Java, Python, Agile/Scrum.Role: Backend Developer",
    "Beta Test LLC: Jan 2019 - Sep 2022 (Location: Dallas, TX)",
    "\u2022 Did stuff.",
    "Environment: Go, Linux,",
    "Docker, Terraform.",
    "Role: Developer",
    "Gamma Test Inc: May 2014 \u2013 Nov 2015 Wrote old code in COBOL for banks.",
    "EDUCATION",
    "Some University AUG 2010 \u2013 APR 2014",
])
jobs = split_jobs_with_bodies(text)
assert len(jobs) == 3, len(jobs)
b0, b1, b2 = jobs[0][1], jobs[1][1], jobs[2][1]
assert b0 == "Built things for customers and kept them running.\nMore things.", repr(b0)
assert b1 == "Did stuff.", repr(b1)
assert "Docker" not in b1 and "Environment" not in b0
assert b2 == "Wrote old code in COBOL for banks.", repr(b2)
assert jobs[1][0].startswith("Role: Backend Developer")
print("body checks passed")