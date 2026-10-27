import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import CandidateSkill, Skill

with SessionLocal() as db:
    for cid in [int(x) for x in sys.argv[1:]]:
        rows = db.execute(select(Skill.name, CandidateSkill.years, CandidateSkill.last_used_year)
                          .join(Skill, Skill.id == CandidateSkill.skill_id)
                          .where(CandidateSkill.candidate_id == cid)).all()
        dated = [r for r in rows if r[1] is not None]
        top = sorted(dated, key=lambda r: -float(r[1]))[:6]
        print(f"Candidate {cid}: skills {len(rows)} | with dates {len(dated)}")
        print("   top by years:", "; ".join(f"{n} {float(y)}y last {ly}" for n, y, ly in top))