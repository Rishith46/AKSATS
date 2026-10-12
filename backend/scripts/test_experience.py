import time

from app.services.experience_extract import extract_experiences

mock = """MOCK resume (test data, not a real candidate)
Jane Mockperson, Dallas, TX

EXPERIENCE
Senior Java Developer - Acme Mock Corp - Jan 2021 to Present
Built Java microservices with Spring Boot on AWS.

Java Developer - Beta Test Systems - 2018 - 2020
Maintained internal Java applications.

EDUCATION
BS Computer Science, Example University, 2017
"""

t = time.time()
res = extract_experiences(mock)
print(f"Seconds: {time.time() - t:.1f}")
for r in res:
    print(r)
print("Count:", len(res))
print("Invented employer present (should be False):",
      any(r["company"] and r["company"].lower() not in mock.lower() for r in res))