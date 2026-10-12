import sys

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.candidates import Candidate, CandidateDocument, CandidateExperience
from app.models.system import ResumeIngestion
from app.services.process_inbox import process_ingestion


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.process_inbox <inbox_row_id>")
        return
    iid = int(sys.argv[1])
    with SessionLocal() as db:
        print("Result:", process_ingestion(db, iid))
        db.expire_all()
        row = db.get(ResumeIngestion, iid)
        print("Inbox row:", row.status, row.issues, "| candidate", row.candidate_id,
              "| document", row.document_id)
        print("Still in inbox folder:", (settings.storage_dir / row.staged_path).exists())
        if row.candidate_id:
            c = db.get(Candidate, row.candidate_id)
            print("Candidate:", c.full_name, "|", c.email, "|", c.phone, "|", c.location,
                  "|", c.parse_status)
            for d in db.scalars(select(CandidateDocument).where(CandidateDocument.candidate_id == c.id)):
                print("Document:", d.original_filename, "| v", d.version_no, "| current", d.is_current,
                      "|", d.storage_path)
            for e in db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == c.id)):
                print("Experience:", e.company, "|", e.title, "|", e.start_date, e.start_precision,
                      "|", e.end_date, e.end_precision, "|", e.is_current)


if __name__ == "__main__":
    main()