import getpass
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.access import Permission, User
from app.models.candidates import Candidate, Skill
from app.models.jobs import Job, JobLocation

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
TEAM = ["rishith@allknownservices.com", "john@allknownservices.com", "vamshi@allknownservices.com"]

UNIT = ["test_geo", "test_visa", "test_visa_schema", "test_edit_schema", "test_experience_edit",
        "test_matching", "test_titles", "test_matcher_v2", "test_location_rules", "test_jd",
        "test_split", "test_bodies", "test_interns", "test_skill_history", "test_skill_refresh",
        "test_ats_reset_access", "test_dashboard_summary", "test_candidate_status_schema",
        "test_candidate_status_history", "test_candidate_archive_listing"]
API = ["test_edit_api", "test_edit_api2", "test_location_api"]

results = []


def run(name, env):
    p = subprocess.run([sys.executable, "-m", f"scripts.{name}"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=900)
    out = (p.stdout.strip().splitlines() or [""])[-1] if p.returncode == 0 else \
        " | ".join((p.stdout + p.stderr).strip().splitlines()[-3:])
    results.append((name, p.returncode == 0, out[:150]))


def counts():
    with SessionLocal() as db:
        return {
            "candidates": db.scalar(select(func.count()).select_from(Candidate)),
            "jobs": db.scalar(select(func.count()).select_from(Job)),
            "job_locations": db.scalar(select(func.count()).select_from(JobLocation)),
            "test skills": db.scalar(select(func.count()).select_from(Skill).where(Skill.name.like("TEST Skill%"))),
        }


before = counts()
env = dict(os.environ)

api_up = True
try:
    api_up = httpx.get(BASE + "/health", timeout=5).status_code == 200
except Exception:
    api_up = False

if api_up:
    env["AKS_TEST_PASSWORD"] = getpass.getpass("Rishith password (used for the API tests, never printed): ")
else:
    print("The API is not running, so the three API tests will be skipped.")

print("Running rule and unit checks ...")
for n in UNIT:
    run(n, env)
if api_up:
    print("Running API checks ...")
    for n in API:
        run(n, env)
else:
    for n in API:
        results.append((n, False, "SKIPPED: the API is not running"))

after = counts()

# All team accounts share the same permissions except the Vamshi-only ATS reset grant.
access = []
with SessionLocal() as db:
    all_perms = {p.code for p in db.scalars(select(Permission)).all()}
    for email in TEAM:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            access.append((email, False, "no such user"))
            continue
        have = {p.code for r in u.roles for p in r.permissions}
        reset_ok = ("ats.reset" in have) == (email == "vamshi@allknownservices.com")
        access.append((email, have - {"ats.reset"} == all_perms - {"ats.reset"} and reset_ok and u.is_active,
                       f"{len(have)} of {len(all_perms)} permissions, designation {u.designation}, active {u.is_active}"))
    reset_users = db.scalars(select(User)).all()
    unauthorized_reset_users = [
        user.email for user in reset_users
        if user.email.casefold() != "vamshi@allknownservices.com"
        and any(permission.code == "ats.reset" for role in user.roles for permission in role.permissions)
    ]

# the backend must not decide anything by role name
ALLOWED = {Path("app/models/access.py"), Path("app/routers/auth.py"), Path("app/deps.py")}
hits = []
for f in (ROOT / "app").rglob("*.py"):
    rel = f.relative_to(ROOT)
    if rel in ALLOWED:
        continue
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(r"\.roles\b|role\.name|\"admin\"|'admin'|\"recruiter\"|'recruiter'", line):
            hits.append(f"{rel}:{i}: {line.strip()[:90]}")

head = subprocess.run([sys.executable, "-m", "alembic", "heads"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
cur = subprocess.run([sys.executable, "-m", "alembic", "current"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

print("\n=== RESULTS ===")
width = max(len(n) for n, _, _ in results)
for n, ok, msg in results:
    print(f"{'PASS' if ok else 'FAIL'}  {n.ljust(width)}  {msg}")
print("\n=== EQUAL ACCESS (database) ===")
for email, ok, msg in access:
    print(f"{'PASS' if ok else 'FAIL'}  {email}: {msg}")
print(f"{'PASS' if not unauthorized_reset_users else 'FAIL'}  ats.reset restricted to Vamshi"
      + ("" if not unauthorized_reset_users else f": {', '.join(unauthorized_reset_users)}"))
print("\n=== ROLE NAMES IN BACKEND LOGIC ===")
print("PASS  none found outside models, login and permission loading" if not hits else "FAIL  " + "\n      ".join(hits))
print("\n=== DATABASE STATE ===")
for k in before:
    same = before[k] == after[k]
    print(f"{'PASS' if same else 'FAIL'}  {k}: before {before[k]}, after {after[k]}")
print("\n=== MIGRATIONS ===")
print(f"{'PASS' if head.split()[0:1] == cur.split()[0:1] and head else 'CHECK'}  head: {head.splitlines()[0] if head else '?'} | current: {cur.splitlines()[-1] if cur else '?'}")

failed = [n for n, ok, _ in results if not ok] + [e for e, ok, _ in access if not ok] + hits
if unauthorized_reset_users:
    failed.append("unauthorized ats.reset assignments")
failed += [k for k in before if before[k] != after[k]]
print(f"\n{len(results) - sum(1 for _, ok, _ in results if not ok)} of {len(results)} test scripts passed.")
sys.exit(1 if failed else 0)