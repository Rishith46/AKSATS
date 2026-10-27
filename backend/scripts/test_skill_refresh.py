from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models.candidates import Candidate, CandidateExperience, CandidateSkill, Skill
from app.services.skill_dates import refresh_skill_dates

with SessionLocal() as db:
    cid = None
    try:
        c = Candidate(full_name="TEST Refresh Candidate")
        db.add(c)
        db.flush()
        cid = c.id
        sk = {n: db.scalar(select(Skill).where(Skill.name == n)) for n in ("Python", "Docker", "Java")}
        assert all(sk.values()), "Python, Docker and Java must exist in the skills list"
        db.add_all([
            CandidateSkill(candidate_id=cid, skill_id=sk["Python"].id, years=Decimal("9.0"), last_used_year=2010, source="extracted"),
            CandidateSkill(candidate_id=cid, skill_id=sk["Docker"].id, years=Decimal("3.0"), last_used_year=2018, source="extracted"),
            CandidateSkill(candidate_id=cid, skill_id=sk["Java"].id, years=Decimal("5.0"), last_used_year=2020, source="confirmed"),
        ])
        db.add(CandidateExperience(candidate_id=cid, company="Alpha Test", title="Developer",
                                   start_date=date(2022, 1, 1), start_precision="month",
                                   end_date=date(2024, 1, 1), end_precision="month", is_current=False,
                                   description="Built Python services."))
        db.flush()
        refresh_skill_dates(db, cid)
        db.flush()
        rows = {n: db.scalar(select(CandidateSkill).where(CandidateSkill.candidate_id == cid,
                                                          CandidateSkill.skill_id == s.id)) for n, s in sk.items()}
        py, dk, jv = rows["Python"], rows["Docker"], rows["Java"]
        assert abs(float(py.years) - 2.0) < 0.06 and py.last_used_year == 2024, (py.years, py.last_used_year)
        assert "Python" in (py.evidence or ""), py.evidence
        assert dk.years is None and dk.last_used_year is None, "an extracted skill no job mentions keeps no dates"
        assert float(jv.years) == 5.0 and jv.last_used_year == 2020 and jv.source == "confirmed", "a confirmed skill must not change"
        print("skill date refresh checks passed")
    finally:
        db.rollback()
        if cid is not None:
            c = db.get(Candidate, cid)
            if c is not None:
                db.delete(c)
                db.commit()