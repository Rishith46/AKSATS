from sqlalchemy import select

from app.db import SessionLocal
from app.models.access import Permission, Role
from app.models.system import MatchConfig

PERMISSIONS = {
    "candidate.view": "View candidates",
    "candidate.edit": "Create and edit candidates",
    "candidate.archive": "Archive and restore candidates",
    "candidate.delete": "Permanently delete candidates",
    "document.upload": "Upload candidate documents",
    "note.add": "Add candidate notes",
    "job.manage": "Create and edit jobs",
    "submission.manage": "Create and update submissions",
    "search.use": "Use candidate search and matching",
    "user.manage": "Manage users and roles",
    "audit.view": "View the full audit log",
}
ADMIN_ONLY = {"user.manage", "candidate.delete", "audit.view"}
ROLES = {
    "admin": list(PERMISSIONS),
    "recruiter": [c for c in PERMISSIONS if c not in ADMIN_ONLY],
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
        if not db.scalar(select(MatchConfig).where(MatchConfig.name == "default")):
            db.add(MatchConfig(name="default", weights=DEFAULT_WEIGHTS, is_active=True))
        db.commit()
        print(f"Seeded {len(PERMISSIONS)} permissions, roles: {', '.join(ROLES)}, default match weights.")


if __name__ == "__main__":
    main()