from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Permission, Role, User
from app.models.system import ActivityLog
from scripts.seed import RESET_PERMISSION, RESET_ROLE, RESET_USER_EMAIL

# Designations are for identification only. Every account below gets the same role.
TEAM = {
    "rishith@allknownservices.com": "Recruiter",
    "john@allknownservices.com": "Recruiter",
    "vamshi@allknownservices.com": "Admin",
}


def main() -> None:
    with SessionLocal() as db:
        perms = [p for p in db.scalars(select(Permission)).all() if p.code != RESET_PERMISSION]
        role = db.scalar(select(Role).where(Role.name == "team_member"))
        if role is None:
            role = Role(name="team_member",
                        description="Equal access for every team member. The designation is for identification only.")
            db.add(role)
        role.permissions = list(perms)
        reset_role = db.scalar(select(Role).where(Role.name == RESET_ROLE))
        if reset_role is None or not any(p.code == RESET_PERMISSION for p in reset_role.permissions):
            raise RuntimeError("Run scripts.seed to configure Vamshi-only ATS reset access.")
        db.flush()
        changed = []
        for email, designation in TEAM.items():
            u = db.scalar(select(User).where(User.email == email))
            if u is None:
                print(f"{email}: NOT FOUND, skipped")
                continue
            old = {"designation": u.designation, "roles": sorted(r.name for r in u.roles)}
            u.designation = designation
            u.roles = [role, reset_role] if email == RESET_USER_EMAIL else [role]
            new_roles = [role.name for role in u.roles]
            changed.append({"email": email, "old": old, "new": {"designation": designation, "roles": new_roles}})
            print(f"{email}: designation {designation}, roles {', '.join(new_roles)}")
        db.add(ActivityLog(user_id=None, action="team.permissions_equalized", object_type="user",
                           new_value={"permissions": len(perms), "users": changed}))
        db.commit()
        print("team_member permissions:", len(role.permissions))


if __name__ == "__main__":
    main()