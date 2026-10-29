from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models.access import User
from app.models.candidates import Candidate
from app.models.system import ActivityLog
from app.routers.candidates import archive_candidate, list_candidates, restore_candidate

TEST_EMAIL = "rishith@allknownservices.com"


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == TEST_EMAIL))
        if user is None:
            raise RuntimeError(f"Test account not found: {TEST_EMAIL}")

        candidate = Candidate(full_name="TEST Candidate Archive Listing", recruiter_id=user.id)
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        candidate_id = candidate.id
        try:
            archive_candidate(candidate_id, db=db, user=user)
            archived = list_candidates(archived_only=True, skill=[], db=db, user=user)
            active = list_candidates(skill=[], db=db, user=user)
            assert candidate_id in {row.id for row in archived}
            assert candidate_id not in {row.id for row in active}

            restore_candidate(candidate_id, db=db, user=user)
            archived_after_restore = list_candidates(archived_only=True, skill=[], db=db, user=user)
            active_after_restore = list_candidates(skill=[], db=db, user=user)
            assert candidate_id not in {row.id for row in archived_after_restore}
            assert candidate_id in {row.id for row in active_after_restore}
        finally:
            db.execute(delete(ActivityLog).where(
                ActivityLog.object_type == "candidate",
                ActivityLog.object_id == candidate_id,
            ))
            db.execute(delete(Candidate).where(Candidate.id == candidate_id))
            db.commit()

    print("Candidate archive-tab listing and restore checks passed.")


if __name__ == "__main__":
    main()
