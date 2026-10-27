import getpass
import sys
from datetime import date

import httpx
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models.candidates import Skill
from app.models.system import ActivityLog
from app.services.experience_years import years_from

BASE = "http://127.0.0.1:8000"
NAME = "TEST Edit Candidate Two"
NEWSKILL = "TEST Skill Zebrafish"
EMAIL = "rishith@allknownservices.com"
THIS_YEAR = date.today().year

pw = __import__("os").environ.get("AKS_TEST_PASSWORD") or getpass.getpass("Rishith password: ")
c = httpx.Client(base_url=BASE, timeout=60)
r = c.post("/auth/login", data={"username": EMAIL, "password": pw})
if r.status_code != 200:
    sys.exit(f"Login failed ({r.status_code})")
c.headers["Authorization"] = "Bearer " + r.json()["access_token"]

passed, failed = 0, []


def check(name, cond, extra=""):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(f"{name} {extra}")


def expected(rows):
    return years_from([{"start": s, "end": e, "is_current": cur} for s, e, cur in rows])


def same_total(resp, rows):
    exp = expected(rows)
    got = resp.json().get("total_experience_years")
    return got is not None and exp is not None and abs(float(got) - exp) < 0.06


def profile(cid):
    return c.get(f"/candidates/{cid}/profile").json()


cid = None
try:
    r = c.post("/candidates", json={"full_name": NAME})
    check("create mock candidate", r.status_code == 201, r.text[:120])
    cid = r.json()["id"]
    sk = f"/candidates/{cid}/skills"
    ex = f"/candidates/{cid}/experiences"

    # ---------- skills ----------
    r = c.post(sk, json={"name": "Python", "years": 4, "last_used_year": THIS_YEAR})
    check("add a skill", r.status_code == 201 and r.json()["name"] == "Python" and r.json()["source"] == "confirmed", r.text[:140])
    py_id = r.json()["skill_id"]
    r = c.post(sk, json={"name": "K8s"})
    check("an alias finds the real skill", r.status_code == 201 and r.json()["name"] == "Kubernetes", r.text[:140])
    k8s_id = r.json()["skill_id"]
    r = c.post(sk, json={"name": NEWSKILL})
    check("unknown skill is refused", r.status_code == 409 and "Unknown skill" in r.text, r.text[:140])
    r = c.post(sk, json={"name": NEWSKILL, "create_if_missing": True})
    check("unknown skill added after confirming", r.status_code == 201 and r.json()["created"] is True, r.text[:140])
    r = c.post(sk, json={"name": "python", "years": 5})
    check("adding an existing skill updates it", r.status_code == 200 and r.json()["years"] == 5.0, r.text[:140])
    names = [s["name"] for s in profile(cid)["skills"]]
    check("no duplicate skill row", names.count("Python") == 1, str(names))
    r = c.patch(f"{sk}/{py_id}", json={"years": 6, "last_used_year": THIS_YEAR - 1})
    check("edit a skill", r.status_code == 200 and r.json()["years"] == 6.0 and r.json()["last_used_year"] == THIS_YEAR - 1, r.text[:140])
    check("refused: negative years", c.post(sk, json={"name": "Java", "years": -1}).status_code == 422)
    check("refused: last used in 1900", c.post(sk, json={"name": "Java", "last_used_year": 1900}).status_code == 422)
    check("refused: blank skill name", c.post(sk, json={"name": "  "}).status_code == 422)
    check("edit of a skill the candidate lacks is 404", c.patch(f"{sk}/999999", json={"years": 1}).status_code == 404)

    m = c.get("/jobs/2/matches").json()
    mine = [x for x in m["candidates"] if x["candidate_id"] == cid]
    py_row = [x for x in mine[0]["required_detail"] if x["skill"] == "Python"] if mine else []
    check("a manual skill reaches matching", bool(py_row) and py_row[0]["status"] == "recent" and py_row[0]["years"] == 6.0, str(py_row))

    r = c.delete(f"{sk}/{k8s_id}")
    check("remove a skill", r.status_code == 200 and r.json()["removed"] == "Kubernetes", r.text[:140])
    check("removed skill is gone", "Kubernetes" not in [s["name"] for s in profile(cid)["skills"]])

    # ---------- experience ----------
    A = (date(2020, 1, 1), date(2022, 1, 1), False)
    r = c.post(ex, json={"company": "Alpha Test", "title": "Developer", "start": "2020-01", "end": "2022-01",
                         "description": "Wrote Python scripts."})
    check("add a job", r.status_code == 201 and r.json()["experience"]["start"] == "2020-01", r.text[:160])
    check("total follows the first job", same_total(r, [A]), r.text[:160])

    B_cur = (date(2022, 2, 1), None, True)
    r = c.post(ex, json={"company": "Beta Test", "title": "Senior Developer", "start": "2022-02", "is_current": True})
    b_id = r.json()["experience"]["id"]
    check("a current job counts to today", same_total(r, [A, B_cur]), r.text[:160])

    r = c.post(ex, json={"company": "Gamma Test", "title": "Contractor", "start": "2020-06", "end": "2021-06"})
    c_id = r.json()["experience"]["id"]
    check("an overlapping job is not counted twice", same_total(r, [A, B_cur]), r.text[:160])

    B_end = (date(2022, 2, 1), date(2023, 1, 1), False)
    r = c.patch(f"{ex}/{b_id}", json={"end": "2023-01", "is_current": False})
    check("ending a job changes the total", r.status_code == 200 and same_total(r, [A, B_end]), r.text[:160])

    r = c.post(ex, json={"company": "Delta Test", "start": "2019", "end": "2019"})
    d_id = r.json()["experience"]["id"]
    check("a year-only date stays a year", r.status_code == 201 and r.json()["experience"]["start"] == "2019", r.text[:160])

    r = c.patch(f"{ex}/{b_id}", json={"is_current": True})
    check("making a job current clears its end", r.status_code == 200 and r.json()["experience"]["end"] is None
          and r.json()["experience"]["is_current"] is True, r.text[:160])

    other_exp = c.get("/candidates/5/profile").json()["experiences"]
    if other_exp:
        check("another candidate's job cannot be edited here",
              c.patch(f"{ex}/{other_exp[0]['id']}", json={"title": "X"}).status_code == 404)
    check("refused: end before start", c.post(ex, json={"company": "X", "start": "2022-01", "end": "2020-01"}).status_code == 422)
    check("refused: current job with an end date", c.post(ex, json={"company": "X", "start": "2020-01", "end": "2021-01", "is_current": True}).status_code == 422)
    check("refused: month 13", c.post(ex, json={"company": "X", "start": "2020-13"}).status_code == 422)
    check("refused: words instead of a date", c.post(ex, json={"company": "X", "start": "Jan 2020"}).status_code == 422)
    check("refused: no company and no title", c.post(ex, json={"start": "2020-01"}).status_code == 422)
    check("refused: a malformed date on edit is 422, not an error", c.patch(f"{ex}/{b_id}", json={"start": "2020-99"}).status_code == 422)

    r = c.delete(f"{ex}/{c_id}")
    check("remove a job", r.status_code == 200 and r.json()["removed"] == c_id, r.text[:140])
    p = profile(cid)
    check("job text and dates are in the profile",
          any(e["description"] == "Wrote Python scripts." and e["start"] == "2020-01" and e["end"] == "2022-01" for e in p["experiences"]),
          str([(e["start"], e["end"]) for e in p["experiences"]]))
    check("calculated total is labeled inferred", p["field_sources"].get("total_experience_years") == "inferred", str(p["field_sources"]))

    # a total set by hand is never overwritten
    r = c.patch(f"/candidates/{cid}", json={"total_experience_years": 9})
    check("set the total by hand", r.status_code == 200 and float(r.json()["total_experience_years"]) == 9.0, r.text[:140])
    r = c.post(ex, json={"company": "Epsilon Test", "title": "Dev", "start": "2000-01", "end": "2001-01"})
    check("a manual total survives a new job", float(r.json()["total_experience_years"]) == 9.0, r.text[:160])
    r = c.delete(f"{ex}/{d_id}")
    check("a manual total survives a removed job", float(r.json()["total_experience_years"]) == 9.0, r.text[:160])

    # ---------- audit ----------
    with SessionLocal() as db:
        counts = dict(db.execute(select(ActivityLog.action, func.count()).where(
            ActivityLog.object_type == "candidate", ActivityLog.object_id == cid).group_by(ActivityLog.action)).all())
    for action, least in [("candidate.skill_added", 3), ("candidate.skill_updated", 2), ("candidate.skill_removed", 1),
                          ("candidate.experience_added", 5), ("candidate.experience_edited", 2),
                          ("candidate.experience_removed", 2)]:
        check(f"audit: {action}", counts.get(action, 0) >= least, str(counts))
finally:
    if cid is not None:
        d = c.delete(f"/candidates/{cid}", params={"confirm_name": NAME})
        check("mock candidate removed", d.status_code == 200, str(d.status_code))
    with SessionLocal() as db:
        db.execute(delete(Skill).where(Skill.name == NEWSKILL))
        db.commit()
        left = db.scalar(select(func.count()).select_from(Skill).where(Skill.name == NEWSKILL))
    check("the test skill was cleaned up", left == 0)

print(f"{passed} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  -", f)
    sys.exit(1)