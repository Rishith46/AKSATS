from datetime import date
from io import BytesIO
from types import SimpleNamespace

import docx
from pdfminer.high_level import extract_text

from app.services.resume_export import build_docx, build_pdf


candidate = SimpleNamespace(
    full_name="Alex Example",
    email="alex@example.test",
    phone="555-010-1234",
    location="Austin, TX",
    linkedin_url="linkedin.com/in/alex-example",
)
experiences = [
    SimpleNamespace(
        title="Backend Engineer",
        company="Example Systems",
        location="Austin, TX",
        start_date=date(2021, 3, 1),
        start_precision="month",
        end_date=None,
        end_precision=None,
        is_current=True,
        description="Built production REST APIs and improved PostgreSQL query performance.",
    )
]
education = [SimpleNamespace(
    institution="Example University", degree="B.S.", field_of_study="Computer Science",
    start_year=2017, end_year=2021,
)]
certifications = [SimpleNamespace(name="Cloud Certificate", issuer="Example Org", year=2024)]
skills = [SimpleNamespace(
    name="PostgreSQL", years=4.0, last_used_year=2026,
    evidence="Optimized PostgreSQL queries supporting production services.",
)]

docx_bytes = build_docx(candidate, experiences, education, certifications, skills)
document = docx.Document(BytesIO(docx_bytes))
docx_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
assert "Alex Example" in docx_text
assert "Backend Engineer" in docx_text
assert "PostgreSQL (4 years, last used 2026)" in docx_text
assert "Optimized PostgreSQL queries" in docx_text
assert "Example University" in docx_text
assert "Cloud Certificate" in docx_text

pdf_bytes = build_pdf(candidate, experiences, education, certifications, skills)
pdf_text = extract_text(BytesIO(pdf_bytes))
assert "Alex Example" in pdf_text
assert "Backend Engineer" in pdf_text
assert "PostgreSQL (4 years, last used 2026)" in pdf_text
assert "Optimized PostgreSQL queries" in pdf_text
assert "Example University" in pdf_text
assert "Cloud Certificate" in pdf_text

print("ATS resume export checks passed.")
