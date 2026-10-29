import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Role, User
from app.security import hash_password
from scripts.seed import RESET_ROLE, RESET_USER_EMAIL


def main() -> None:
    if len(sys.argv) < 3:
        print('Usage: python -m scripts.create_admin you@company.com "Full Name"')
        return
    email, name = sys.argv[1].strip().lower(), sys.argv[2]
    pw = getpass.getpass("Password (min 12 characters): ")
    if len(pw) < 12:
        print("Password too short. Nothing was created.")
        return
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == "admin"))
        if not role:
            print("Admin role missing. Run: python -m scripts.seed")
            return
        if db.scalar(select(User).where(User.email == email)):
            print("A user with that email already exists.")
            return
        user = User(email=email, full_name=name, password_hash=hash_password(pw))
        user.roles = [role]
        if email == RESET_USER_EMAIL:
            reset_role = db.scalar(select(Role).where(Role.name == RESET_ROLE))
            if reset_role is None:
                print("Vamshi's reset role is missing. Run: python -m scripts.seed")
                return
            user.roles.append(reset_role)
        db.add(user)
        db.commit()
        print(f"Admin created: {email}")


if __name__ == "__main__":
    main()