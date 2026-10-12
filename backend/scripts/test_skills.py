from app.db import SessionLocal
from app.services.skill_match import find_skills, load_terms

mock = """MOCK resume (test data)
Built Java microservices using Spring Boot and K8s on AWS.
Wrote JavaScript and TypeScript front ends. Used C# and .NET for tooling.
Experience with CI/CD pipelines and Node.js.
Went to market faster; going to the office. Worked with Golang services.
"""

with SessionLocal() as db:
    terms = load_terms(db)

res = find_skills(mock, terms)
names = sorted(r["skill"] for r in res)
print("Found:", names)
print("Java found:", "Java" in names)
print("JavaScript found:", "JavaScript" in names)
print("Kubernetes via K8s:", "Kubernetes" in names)
print("Amazon Web Services via AWS:", "Amazon Web Services" in names)
print("Go found via Golang:", "Go" in names)
print("Python found (should be False):", "Python" in names)
print("Spring (alone) found:", "Spring" in names)
print("Example evidence:", [r["evidence"] for r in res if r["skill"] == "Kubernetes"])