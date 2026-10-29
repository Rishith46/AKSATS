from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Permission, Role, User
from app.models.system import MatchConfig

RESET_PERMISSION = "ats.reset"
RESET_ROLE = "ats_reset"
RESET_USER_EMAIL = "vamshi@allknownservices.com"

PERMISSIONS = {
    "candidate.view": "View candidates",
    "candidate.edit": "Create and edit candidates",
    "candidate.archive": "Archive and restore candidates",
    "candidate.delete": "Permanently delete candidates",
    "document.upload": "Upload candidate documents",
    "note.add": "Add candidate notes",
    "job.manage": "Create and edit jobs",
    "job.delete": "Permanently delete jobs",
    "submission.manage": "Create and update submissions",
    "search.use": "Use candidate search and matching",
    "user.manage": "Manage users and roles",
    "audit.view": "View the full audit log",
    RESET_PERMISSION: "Reset all ATS candidate and job data",
}
ADMIN_ONLY = {"user.manage", "candidate.delete", "audit.view", RESET_PERMISSION}
GUEST_EXCLUDED = ADMIN_ONLY | {"job.delete"}
ROLES = {
    "admin": [c for c in PERMISSIONS if c != RESET_PERMISSION],
    "recruiter": [c for c in PERMISSIONS if c not in ADMIN_ONLY],
    "team_member": [c for c in PERMISSIONS if c != RESET_PERMISSION],
    "guest": [c for c in PERMISSIONS if c not in GUEST_EXCLUDED],
}
DEFAULT_WEIGHTS = {
    "required_skills": 25, "semantic_similarity": 30, "relevant_experience": 15,
    "recent_experience": 10, "job_title": 10, "location": 5, "visa": 5,
}


def main() -> None:
    with SessionLocal() as db:
        perms = {}
        for code, desc in PERMISSIONS.items():
            p = db.scalar(select(Permission).where(Permission.code == code))
            if not p:
                p = Permission(code=code, description=desc)
                db.add(p)
            perms[code] = p
        db.flush()
        for name, codes in ROLES.items():
            r = db.scalar(select(Role).where(Role.name == name))
            if not r:
                r = Role(name=name)
                db.add(r)
            r.permissions = [perms[c] for c in codes]
        reset_role = db.scalar(select(Role).where(Role.name == RESET_ROLE))
        if reset_role is None:
            reset_role = Role(name=RESET_ROLE, description="Exclusive ATS reset access for Vamshi.")
            db.add(reset_role)
        reset_role.permissions = [perms[RESET_PERMISSION]]
        db.flush()
        for role in db.scalars(select(Role).where(Role.name != RESET_ROLE)).all():
            role.permissions = [permission for permission in role.permissions
                                if permission.code != RESET_PERMISSION]
        for user in db.scalars(select(User)).all():
            if user.email.casefold() == RESET_USER_EMAIL:
                if reset_role not in user.roles:
                    user.roles.append(reset_role)
            else:
                user.roles = [role for role in user.roles if role.name != RESET_ROLE]
        if not db.scalar(select(MatchConfig).where(MatchConfig.name == "default")):
            db.add(MatchConfig(name="default", weights=DEFAULT_WEIGHTS, is_active=True))
        db.commit()
        print(
            f"Seeded {len(PERMISSIONS)} permissions, roles: "
            f"{', '.join((*ROLES, RESET_ROLE))}, default match weights."
        )


if __name__ == "__main__":
    main()