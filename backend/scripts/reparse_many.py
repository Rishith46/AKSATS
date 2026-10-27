import sys
import time

from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Candidate, CandidateDocument, CandidateExperience
from app.services.parse_pipeline import parse_document

with SessionLocal() as db:
    for cid in [int(x) for x in sys.argv[1:]]:
        doc = db.scalar(select(CandidateDocument).where(
            CandidateDocument.candidate_id == cid, CandidateDocument.kind == "resume",
            CandidateDocument.is_current.is_(True)))
        if not doc:
            print(f"Candidate {cid}: no current resume")
            continue
        t = time.time()
        res = parse_document(db, doc.id)
        db.expire_all()
        c = db.get(Candidate, cid)
        rows = db.scalars(select(CandidateExperience).where(CandidateExperience.candidate_id == cid)
                          .order_by(CandidateExperience.start_date.desc().nulls_last(),
                                    CandidateExperience.id)).all()
        lens = [len(e.description or "") for e in rows]
        print(f"Candidate {cid}: {res['status']} | jobs {len(rows)} | years {c.total_experience_years} "
              f"| responsibilities chars per job {lens} | {time.time() - t:.0f}s")