from datetime import date
from unittest.mock import patch

from app.services.experience_extract import _fallback_experience, extract_experiences, split_jobs_with_bodies
from app.services.field_extract import extract_fields
from app.services.experience_years import years_from
from app.services.resume_sections import (
    extract_certifications,
    extract_education,
    extract_resume_skills,
    extract_sections,
)

RESUME = """JANE DOE
Email: jane.doe@example.com | Phone: +44 20 7946 0958
LinkedIn: linkedin.com/in/janedoe
Location: London, UK
Visa Status: H-1B
Availability: 2 weeks notice
Rate: $95/hour
8 years of experience

EDUCATION
University of Example
B.S. Computer Science
2019
Master of Science in Data Analytics | Example College | 2021

CERTIFICATIONS
AWS Certified Solutions Architect, issued by Amazon, 2022
Azure Administrator Associate | 2023

SKILLS
Java, Kotlin, Android
Python | SQL | Docker

EXPERIENCE
Software Engineer
Example Corp | 03/2020 - Present
Built a reliable platform.
"""

fields = extract_fields(RESUME)
assert fields["full_name"] == "JANE DOE"
assert fields["email"] == "jane.doe@example.com"
assert fields["phone"] == "+44 20 7946 0958"
assert fields["location"] == "London, UK"
assert fields["visa_status"] == "H1B"
assert fields["availability"] == "2 weeks notice"
assert fields["rate"] == 95
assert fields["rate_unit"] == "hour"
assert fields["total_experience_years"] == 8
assert extract_fields("MADONNA\nOne-name resume")["full_name"] == "MADONNA"
assert extract_fields("Ravi\nStaff Software Engineer\nravi@example.com")["full_name"] == "Ravi"

sections = extract_sections(RESUME)
assert "EXPERIENCE" not in sections["skills"]
education = extract_education(RESUME)
assert len(education) == 2, education
assert education[0]["institution"] == "University of Example"
assert education[0]["degree"] == "B.S."
assert education[0]["field_of_study"] == "Computer Science"
certifications = extract_certifications(RESUME)
assert certifications == [
    {"name": "AWS Certified Solutions Architect", "issuer": "Amazon", "year": 2022},
    {"name": "Azure Administrator Associate", "issuer": None, "year": 2023},
]
assert extract_resume_skills(RESUME) == ["Java", "Kotlin", "Android", "Python", "SQL", "Docker"]

jobs = split_jobs_with_bodies(RESUME)
assert len(jobs) == 1, jobs
fallback = _fallback_experience(*jobs[0])
assert fallback is not None
assert fallback["title"] == "Software Engineer", fallback
assert fallback["company"] == "Example Corp", fallback
assert fallback["start"] == "2020-03", fallback
assert fallback["is_current"] is True

with patch("app.services.experience_extract.ollama.chat", side_effect=ConnectionError("offline")):
    fallback_result = extract_experiences(RESUME)
assert len(fallback_result) == 1, fallback_result
assert fallback_result[0]["company"] == "Example Corp"

# Resume layouts where the date range follows the role description still produce all jobs.
ORDERED_RESUME = """SAMPLE CANDIDATE
PROFESSIONAL EXPERIENCE
YourTravelBooking.com | Mobile Architect (Contract) | Remote
Architected mobile systems and led the delivery team.
Sep 2026 - Present
Okta | Staff Software Engineer | Remote, TX
Built a cross-platform feature platform.
Apr 2022 - Jul 2026
DocuSign | Lead iOS Engineer | San Francisco, CA
Led mobile platform delivery.
May 2021 - Apr 2022
SmartThings Inc. | Staff / Lead Software Engineer | Mountain View, CA
Modernized the mobile platform.
May 2017 - May 2021
Orion Labs | Senior Software Engineer, Mobile | San Francisco, CA
Built mobile features.
Apr 2016 - May 2017
Visa | Senior Software Engineer, Mobile (Consultant) | Foster City, CA
Delivered the mobile checkout application.
Aug 2014 - Apr 2016
Yash Technologies | Hyderabad, India |
Delivered enterprise applications.
Dec 2012 - May 2014
Hurix Systems | Bombay, India |
Built mobile applications.
Mar 2010 - Nov 2012
EDUCATION
University of Example
"""
ordered_blocks = split_jobs_with_bodies(ORDERED_RESUME)
assert len(ordered_blocks) == 8, ordered_blocks
ordered_experiences = [_fallback_experience(header, body) for header, body in ordered_blocks]
assert all(ordered_experiences), ordered_experiences
assert ordered_experiences[0]["title"] == "Mobile Architect (Contract)"
assert ordered_experiences[0]["company"] == "YourTravelBooking.com"
assert ordered_experiences[2]["title"] == "Lead iOS Engineer"
assert ordered_experiences[2]["company"] == "DocuSign"
assert ordered_experiences[6]["company"] == "Yash Technologies"
dated = []
for experience in ordered_experiences:
    start = date.fromisoformat(experience["start"] + "-01")
    end = date.fromisoformat(experience["end"] + "-01") if experience["end"] else None
    dated.append({"start": start, "end": end, "is_current": experience["is_current"]})
assert years_from(dated, today=date(2026, 10, 1)) == 16.1

with patch("app.services.experience_extract.ollama.chat", side_effect=ConnectionError("offline")):
    ordered_fallbacks = extract_experiences(ORDERED_RESUME)
assert len(ordered_fallbacks) == 8, ordered_fallbacks
assert ordered_fallbacks[2]["company"] == "DocuSign"
assert ordered_fallbacks[2]["title"] == "Lead iOS Engineer"

print("Resume parser quality checks passed.")
