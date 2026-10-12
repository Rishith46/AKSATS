from app.services.experience_extract import split_jobs

filler = "Summary line about skills. " * 400
text = filler + "\n".join([
    "",
    "PROFESSIONAL EXPERIENCE",
    "Role: Sr. Developer",
    "Alpha Test Co: OCT 2025 \u2013 Present (Location: Austin, TX (Remote))",
    "\u2022 Built things.",
    "\u2022 More things.",
    "Environment: Java, Python, Agile/Scrum.Role: Backend Developer",
    "Beta Test LLC: Jan 2019 - Sep 2022 (Location: Dallas, TX)",
    "\u2022 Did stuff.",
    "Role: Developer",
    "Gamma Test Inc: May 2014 \u2013 Nov 2015 (Location: Chennai, India)",
    "\u2022 Old stuff.",
    "EDUCATION",
    "Some University AUG 2010 \u2013 APR 2014",
    "",
])
print("experience heading offset:", text.find("PROFESSIONAL EXPERIENCE"))
hs = split_jobs(text)
print("jobs found:", len(hs))
for h in hs:
    print(repr(h[:90]))
assert text.find("PROFESSIONAL EXPERIENCE") > 6000
assert len(hs) == 3
assert hs[1].startswith("Role: Backend Developer")
assert not any("AUG 2010" in h for h in hs)
print("split checks passed")