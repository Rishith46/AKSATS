import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Role, User


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.set_role email role")
        return
    email, role_name = sys.argv[1].strip().lower(), sys.argv[2]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not user or not role:
            print("User or role not found. Nothing was changed.")
            return
        user.roles = [role]
        db.commit()
        print(f"{email} now has only the role: {role_name}")


if __name__ == "__main__":
    main()