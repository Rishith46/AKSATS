import sys
import time

from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Candidate, CandidateDocument, CandidateExperience
from app.services.parse_pipeline import parse_document

cid = int(sys.argv[1])
with SessionLocal() as db:
    doc = db.scalar(select(CandidateDocument).where(
        CandidateDocument.candidate_id == cid, CandidateDocument.kind == "resume",
        CandidateDocument.is_current.is_(True)))
    if not doc:
        print("No current resume for that candidate")
        sys.exit(1)
    t = time.time()
    print("Result:", parse_document(db, doc.id))
    print(f"Seconds: {time.time() - t:.0f}")
    db.expire_all()
    c = db.get(Candidate, cid)
    print("Parse status:", c.parse_status, "| estimated years:", c.total_experience_years)
    rows = db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == cid)
                      .order_by(CandidateExperience.start_date.desc().nulls_last())).all()
    print("Experiences:", len(rows))
    for e in rows:
        print(e.start_date, e.start_precision, "->", e.end_date, e.end_precision,
              "| current", e.is_current, "| title found", bool(e.title), "| company found", bool(e.company))