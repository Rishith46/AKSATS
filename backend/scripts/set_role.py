import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Role, User
from scripts.seed import RESET_ROLE, RESET_USER_EMAIL


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
        if user.email.casefold() == RESET_USER_EMAIL:
            reset_role = db.scalar(select(Role).where(Role.name == RESET_ROLE))
            if reset_role is None:
                print("Vamshi's reset role is missing. Run: python -m scripts.seed")
                return
            if reset_role not in user.roles:
                user.roles.append(reset_role)
        db.commit()
        print(f"{email} now has only the role: {role_name}")


if __name__ == "__main__":
    main()