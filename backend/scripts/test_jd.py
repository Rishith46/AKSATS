from app.services.jd_read import read_jd
from app.services.skill_match import _pattern

SK = {"Power BI": ["PowerBI"], "Six Sigma": ["6 Sigma"], "Lean Manufacturing": ["Lean"],
      "Print Reading": ["Blueprints"], "Creo": [], "3D CAD": [], "SPC": ["Statistical SPC"],
      "Procurement": [], "Machining": [], "Supplier Management": [],
      "Java": [], "Python": [], "Kubernetes": [], "PostgreSQL": [], "Redis": [],
      "REST APIs": ["REST API"], "AWS": [], "EC2": [], "AWS CDK": [],
      "API integration": [], "performance optimization": []}
pairs = []
for n, al in SK.items():
    pairs += [(n, n)] + [(n, a) for a in al]
TERMS = [(n, t, _pattern(t)) for n, t in sorted(pairs, key=lambda x: -len(x[1]))]


def R(text):
    return read_jd(text, TERMS)


def R_EMPTY(text):
    return read_jd(text, [])


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
assert {"Machining", "Creo", "3D CAD", "welding", "communication"}.issubset(
    set(d["skill_suggestions"])
)

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

# a plain first-line title and explicit visa types are carried into the editable draft
d = R("Senior Java Developer\nLocation: Austin, TX\nVisa: USC, H-1B, STEM OPT")
assert d["title"] == "Senior Java Developer"
assert d["visa_requirements"] == ["USC", "H1B", "STEM-OPT"]
d = R("Title: X\nNo visa requirements are mentioned.")
assert d["visa_requirements"] == []

# common JD field labels and qualifications headings populate job title and required skills
d = R("""Job Title: Senior Software Engineer
Job Description
Required Qualifications:
- 5+ years of Java and Python experience
- Kubernetes
Preferred Qualifications:
- Six Sigma
""")
assert d["title"] == "Senior Software Engineer", d["title"]
assert d["required_skills"] == ["Java", "Python", "Kubernetes"], d["required_skills"]
assert d["preferred_skills"] == ["Six Sigma"], d["preferred_skills"]
d = R("Technical Skills Required: Java, Python")
assert d["required_skills"] == ["Java", "Python"], d["required_skills"]

# representative JD formats with a full state name, work arrangement, and skills in prose/technical groups
d = R("""Job Title: Backend Engineer – Redis & PostgreSQL
Location: San Francisco, California
Work Arrangement: On-site, 5 days per week
Required Experience: 1–5 years
Key Responsibilities
Improve caching strategies and application performance using Redis and PostgreSQL.
Required Qualifications
Strong hands-on experience with PostgreSQL, including database design and query optimization.
Practical experience with Redis and REST APIs in production environments.
Working knowledge of AWS and cloud-based application deployment.
Key Technical Skills
Databases: PostgreSQL
Caching: Redis
API Development: REST APIs, API integration, and performance optimization
Cloud Infrastructure: AWS, EC2, AWS CDK
""")
assert d["title"] == "Backend Engineer – Redis & PostgreSQL", d["title"]
assert d["location"] == "San Francisco, CA", d["location"]
assert d["work_mode"] == "Onsite", d["work_mode"]
assert d["required_experience_years"] == 1.0, d["required_experience_years"]
assert {"PostgreSQL", "Redis", "REST APIs", "AWS"}.issubset(set(d["required_skills"]))
assert {"EC2", "AWS CDK", "API integration", "performance optimization"}.issubset(
    set(d["skill_suggestions"])
)

# skill suggestions still exist when there are no catalog entries to match
d = R_EMPTY("""Job Title: AI Engineer
Location: India (Remote)
Technical Skills & Requirements
Strong programming skills in Python and/or TypeScript, with experience building production systems.
Hands-on experience working with LLMs and modern AI tooling, including prompt engineering, tool use, and multi-step workflow orchestration.
Experience integrating with platforms such as Snowflake, dbt, Google Drive, and Slack.
Familiarity with structured outputs, function calling, retrieval-augmented generation, and CI/CD.
""")
assert d["title"] == "AI Engineer", d["title"]
assert d["location"] == "India", d["location"]
assert d["work_mode"] == "Remote", d["work_mode"]
assert {
    "Python", "TypeScript", "prompt engineering", "tool use",
    "multi-step workflow orchestration", "Snowflake", "dbt", "Google Drive",
    "Slack", "structured outputs", "function calling",
    "retrieval-augmented generation", "CI/CD",
}.issubset(set(d["skill_suggestions"])), d["skill_suggestions"]

# Repeated skills with different capitalization or whitespace appear only once.
d = R_EMPTY("""Job Title: Engineer
Key Technical Skills
Programming: Python, PYTHON, python
Databases: PostgreSQL
Other Skills
Python    PostgreSQL
""")
normalized_suggestions = [
    " ".join(skill.split()).casefold() for skill in d["skill_suggestions"]
]
assert len(normalized_suggestions) == len(set(normalized_suggestions)), d["skill_suggestions"]

# a (Required) marker under Soft Skills keeps those lines soft, not required
d = R("Title: X\nSoft Skills\n(Required)\n- Great written and oral communication.\nTop 3 Skills\n- Machining")
assert d["soft_skills"] == ["Great written and oral communication"], d["soft_skills"]
assert d["required_skills"] == ["Machining"] and d["unrecognized"] == []
print("job description reader checks passed")