from decimal import Decimal

from sqlalchemy import and_, func, or_, select

from app.db import SessionLocal
from app.models.candidates import TitleMapping

# Starting values written by the developer, not business rules from the client. Edit freely.
PAIRS = [
    ("Software Engineer", "Software Developer", 0.9),
    ("Backend Developer", "Software Developer", 0.7),
    ("Backend Developer", "Software Engineer", 0.7),
    ("Java Developer", "Software Developer", 0.7),
    ("Java Developer", "Software Engineer", 0.6),
    ("Java Developer", "Java Software Engineer", 0.9),
    ("Java Software Engineer", "Software Engineer", 0.8),
    ("Java Software Engineer", "Software Developer", 0.7),
    ("Java Developer", "Backend Developer", 0.6),
    ("Java Software Engineer", "Backend Developer", 0.6),
]


def main() -> None:
    added = 0
    with SessionLocal() as db:
        for a, b, rel in PAIRS:
            exists = db.scalar(select(TitleMapping.id).where(or_(
                and_(TitleMapping.title_a == a, TitleMapping.title_b == b),
                and_(TitleMapping.title_a == b, TitleMapping.title_b == a))))
            if not exists:
                db.add(TitleMapping(title_a=a, title_b=b, relatedness=Decimal(str(rel))))
                added += 1
        db.commit()
        total = db.scalar(select(func.count()).select_from(TitleMapping))
    print(f"Title pairs added: {added}, total: {total}")


if __name__ == "__main__":
    main()