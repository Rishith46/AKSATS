import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.services.text_extract import ExtractionError, extract_text

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "mock_resume.pdf"
    c = canvas.Canvas(str(p), pagesize=letter)
    y = 750
    for line in [
        "MOCK PERSON (test data, not a real candidate)",
        "mock.person@example.com | 555-010-0000 | Dallas, TX",
        "Senior Java Developer, Acme Mock Corp, 2021 - Present",
        "Built Java microservices with Spring Boot on AWS.",
    ]:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    text = extract_text(p)
    print("PDF extracted characters:", len(text))
    print("Contains email:", "mock.person@example.com" in text)
    print("Contains Spring Boot:", "Spring Boot" in text)

    blank = Path(d) / "blank.pdf"
    c = canvas.Canvas(str(blank), pagesize=letter)
    c.save()
    try:
        extract_text(blank)
        print("Blank PDF: NOT rejected (unexpected)")
    except ExtractionError as e:
        print("Blank PDF rejected:", e)

    short = Path(d) / "short.pdf"
    c = canvas.Canvas(str(short), pagesize=letter)
    c.drawString(72, 750, "Short resume")
    c.save()
    assert extract_text(short) == "Short resume"
    print("Short PDF accepted")