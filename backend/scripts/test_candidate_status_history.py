from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.access import User
from app.models.candidates import Candidate, CandidateNote
from app.models.system import ActivityLog
from app.routers.candidates import update_candidate
from app.schemas.candidates import CandidateUpdate

TEST_EMAIL = "rishith@allknownservices.com"


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == TEST_EMAIL))
        if user is None:
            raise RuntimeError(f"Test account not found: {TEST_EMAIL}")

        candidate = Candidate(full_name="TEST Candidate Status History", recruiter_id=user.id)
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        candidate_id = candidate.id
        try:
            updated = update_candidate(
                candidate_id, CandidateUpdate(status="Open"), db=db, user=user
            )
            assert updated.status == "Open"
            note = db.scalar(
                select(CandidateNote).where(CandidateNote.candidate_id == candidate_id)
            )
            assert note is not None
            assert note.author_id == user.id
            assert "Status changed from New to Open." in note.body
            assert f"Changed by: {user.full_name} ({user.email})" in note.body
            assert "Changed at:" in note.body
            assert note.created_at is not None

            update_candidate(candidate_id, CandidateUpdate(status="Open"), db=db, user=user)
            notes = db.scalars(
                select(CandidateNote).where(CandidateNote.candidate_id == candidate_id)
            ).all()
            assert len(notes) == 1, "Selecting the current status should not add another history note"
        finally:
            db.execute(delete(ActivityLog).where(
                ActivityLog.object_type == "candidate",
                ActivityLog.object_id == candidate_id,
            ))
            db.execute(delete(CandidateNote).where(CandidateNote.candidate_id == candidate_id))
            db.execute(delete(Candidate).where(Candidate.id == candidate_id))
            db.commit()

    print("Candidate status history integration checks passed.")


if __name__ == "__main__":
    main()
