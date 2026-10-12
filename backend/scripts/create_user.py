import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Role, User
from app.security import hash_password


def main() -> None:
    if len(sys.argv) < 4:
        print('Usage: python -m scripts.create_user email "Full Name" role')
        return
    email, name, role_name = sys.argv[1].strip().lower(), sys.argv[2], sys.argv[3]
    pw = getpass.getpass("Password (min 12 characters): ")
    if len(pw) < 12:
        print("Password too short. Nothing was created.")
        return
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            print(f"Role '{role_name}' does not exist.")
            return
        if db.scalar(select(User).where(User.email == email)):
            print("A user with that email already exists.")
            return
        user = User(email=email, full_name=name, password_hash=hash_password(pw))
        user.roles = [role]
        db.add(user)
        db.commit()
        print(f"User created: {email} with role {role_name}")


if __name__ == "__main__":
    main()