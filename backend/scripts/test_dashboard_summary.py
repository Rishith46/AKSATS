from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.candidates import Candidate
from app.routers.dashboard import summary


def main() -> None:
    with SessionLocal() as db:
        result = summary(months=3, db=db, user=None)
        active_candidates = db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.archived_at.is_(None),
                Candidate.merged_into_id.is_(None),
            )
        ) or 0

    assert len(result["months"]) == 3
    assert all("new_candidates" in month for month in result["months"])
    assert result["totals"]["active_candidates"] == active_candidates
    assert sum(item["count"] for item in result["candidate_statuses"]) == active_candidates
    assert sum(item["count"] for item in result["candidate_parse_statuses"]) == active_candidates
    assert sum(month["new_candidates"] for month in result["months"]) <= active_candidates
    assert "deleted records are not included" in result["candidate_count_definition"]
    print("Active-candidate dashboard aggregation checks passed.")


if __name__ == "__main__":
    main()
