from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Permission, Role, User
from app.models.system import ActivityLog

# Designations are for identification only. Every account below gets the same role.
TEAM = {
    "rishith@allknownservices.com": "Recruiter",
    "john@allknownservices.com": "Recruiter",
    "vamshi@allknownservices.com": "Admin",
}


def main() -> None:
    with SessionLocal() as db:
        perms = db.scalars(select(Permission)).all()
        role = db.scalar(select(Role).where(Role.name == "team_member"))
        if role is None:
            role = Role(name="team_member",
                        description="Equal access for every team member. The designation is for identification only.")
            db.add(role)
        role.permissions = list(perms)
        db.flush()
        changed = []
        for email, designation in TEAM.items():
            u = db.scalar(select(User).where(User.email == email))
            if u is None:
                print(f"{email}: NOT FOUND, skipped")
                continue
            old = {"designation": u.designation, "roles": sorted(r.name for r in u.roles)}
            u.designation = designation
            u.roles = [role]
            changed.append({"email": email, "old": old, "new": {"designation": designation, "roles": ["team_member"]}})
            print(f"{email}: designation {designation}, role team_member")
        db.add(ActivityLog(user_id=None, action="team.permissions_equalized", object_type="user",
                           new_value={"permissions": len(perms), "users": changed}))
        db.commit()
        print("team_member permissions:", len(role.permissions))


if __name__ == "__main__":
    main()