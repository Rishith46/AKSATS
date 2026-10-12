import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import User
from app.security import hash_password


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.reset_password you@company.com")
        return
    email = sys.argv[1].strip().lower()
    pw = getpass.getpass("New password (min 12 characters): ")
    if len(pw) < 12:
        print("Password too short. Nothing was changed.")
        return
    confirm = getpass.getpass("Type it again: ")
    if pw != confirm:
        print("Passwords did not match. Nothing was changed.")
        return
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            print("No user with that email.")
            return
        user.password_hash = hash_password(pw)
        db.commit()
        print(f"Password reset for {email}")


if __name__ == "__main__":
    main()