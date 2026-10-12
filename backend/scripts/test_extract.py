import tempfile
from pathlib import Path

import docx

from app.services.text_extract import ExtractionError, extract_text

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "mock_resume.docx"
    doc = docx.Document()
    doc.add_paragraph("MOCK PERSON (test data, not a real candidate)")
    doc.add_paragraph("mock.person@example.com | 555-010-0000 | Dallas, TX")
    doc.add_paragraph("Senior Java Developer, Acme Mock Corp, 2021 - Present")
    doc.add_paragraph("Built Java microservices with Spring Boot on AWS.")
    doc.save(str(p))
    text = extract_text(p)
    print("DOCX extracted characters:", len(text))
    print("Contains email:", "mock.person@example.com" in text)
    print("Contains Spring Boot:", "Spring Boot" in text)

    bad = Path(d) / "empty.docx"
    docx.Document().save(str(bad))
    try:
        extract_text(bad)
        print("Empty file: NOT rejected (unexpected)")
    except ExtractionError as e:
        print("Empty file rejected:", e)