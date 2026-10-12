import io
import uuid

import docx
from sqlalchemy import delete, func, select

from app.config import settings
from app.db import SessionLocal
from app.models.candidates import Candidate, DuplicateCandidate
from app.models.system import ResumeIngestion
from app.services.process_inbox import process_ingestion


def make(lines):
    d = docx.Document()
    for ln in lines:
        d.add_paragraph(ln)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


A = ["Dana Fakeperson", "Irving, TX | dana.fake@example.com | (555) 010-1111", "EXPERIENCE",
     "QA Engineer - Globex Mock LLC - Jan 2021 to Present", "Wrote Selenium tests."]
B = ["Dana Fakeperson", "Irving, TX | DANA.FAKE@example.com | 555.010.1111", "EXPERIENCE",
     "Test Engineer - Initech Test Inc - 2018 - 2020", "Used Java and Selenium."]
C = ["Dana Fakeperson", "Irving, TX | other.dana@example.com | (555) 010-2222", "EXPERIENCE",
     "Analyst - Umbrella Test Co - 2019 - 2021", "Built reports in Tableau."]

files = {"A": make(A), "B": make(B), "C": make(C)}
files["A_again"] = files["A"]
row_ids, staged = [], []

try:
    with SessionLocal() as db:
        for key in ["A", "A_again", "B", "C"]:
            rel = f"inbox/{uuid.uuid4().hex}.docx"
            full = settings.storage_dir / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(files[key])
            staged.append(full)
            r = ResumeIngestion(source="upload", original_filename=f"MOCK_{key}.docx",
                                staged_path=rel, status="Received")
            db.add(r)
            db.commit()
            row_ids.append(r.id)
            process_ingestion(db, r.id)
            db.expire_all()
            r = db.get(ResumeIngestion, r.id)
            print(f"{key}: row status={r.status} | candidate={r.candidate_id} | "
                  f"duplicate_of={r.duplicate_of_candidate_id} | issues={r.issues}")
            if r.candidate_id:
                print("   candidate parse_status:", db.get(Candidate, r.candidate_id).parse_status)
        print("duplicate_candidates rows:",
              db.scalar(select(func.count()).select_from(DuplicateCandidate)))
except Exception as exc:
    print("TEST ERROR:", type(exc).__name__, exc)
finally:
    with SessionLocal() as db:
        cand_ids = [c for (c,) in db.execute(
            select(ResumeIngestion.candidate_id).where(ResumeIngestion.id.in_(row_ids),
                                                       ResumeIngestion.candidate_id.is_not(None))).all()]
        for cid in cand_ids:
            c = db.get(Candidate, cid)
            if c:
                for d in c.documents:
                    (settings.storage_dir / d.storage_path).unlink(missing_ok=True)
                db.delete(c)
        db.execute(delete(ResumeIngestion).where(ResumeIngestion.id.in_(row_ids)))
        db.commit()
        for cid in cand_ids:
            try:
                (settings.storage_dir / "candidates" / str(cid)).rmdir()
            except OSError:
                pass
    for p in staged:
        p.unlink(missing_ok=True)
    with SessionLocal() as db:
        print("Leftover candidates:", [i for (i,) in db.execute(select(Candidate.id).order_by(Candidate.id)).all()])
        print("Leftover inbox rows:", [i for (i,) in db.execute(select(ResumeIngestion.id).order_by(ResumeIngestion.id)).all()])
    print("Leftover inbox files:", len(list((settings.storage_dir / "inbox").glob("*"))))