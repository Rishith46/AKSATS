import getpass
import sys

import httpx
from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models.jobs import Job
from app.models.system import ActivityLog

BASE = "http://127.0.0.1:8000"
EMAIL = "rishith@allknownservices.com"
NAMES = {"tx": "TEST Loc Texas", "ok": "TEST Loc Oklahoma", "none": "TEST Loc Unknown", "india": "TEST Loc India"}

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


cands, jobs = {}, []


def new_job(**kw):
    body = {"title": "TEST Loc Job", **kw}
    r = c.post("/jobs", json=body)
    if r.status_code == 201:
        jobs.append(r.json()["id"])
    return r


def result(jid):
    m = c.get(f"/jobs/{jid}/matches").json()
    mine = set(cands.values())
    ranked = {x["candidate_id"]: x for x in m["candidates"] if x["candidate_id"] in mine}
    excl = {x["candidate_id"]: x for x in m["excluded"] if x["candidate_id"] in mine}
    return ranked, excl


try:
    for key, body in {
        "tx": {"full_name": NAMES["tx"], "location": "Austin, TX"},
        "ok": {"full_name": NAMES["ok"], "location": "Tulsa, OK"},
        "none": {"full_name": NAMES["none"]},
        "india": {"full_name": NAMES["india"], "location": "Hyderabad, Telangana", "country": "India"},
    }.items():
        r = c.post("/candidates", json=body)
        check(f"create {key} candidate", r.status_code == 201, r.text[:100])
        cands[key] = r.json()["id"]
    TX, OK, NONE, IND = cands["tx"], cands["ok"], cands["none"], cands["india"]

    # ---------- a job with no preference behaves as before ----------
    r = new_job(location="Dallas, TX", work_mode="Onsite")
    legacy = r.json()["id"]
    check("a job with no preference has no locations", r.json()["location_preference"] is None and r.json()["locations"] == [])
    ranked, excl = result(legacy)
    check("legacy: nobody is excluded for location", {TX, OK, NONE, IND} <= set(ranked), str(list(excl)))
    check("legacy: location check is not applicable", ranked[OK]["location_check"]["status"] == "not_applicable")
    check("legacy: same state still scores a half", ranked[TX]["signals"]["location"]["score"] == 0.5, str(ranked[TX]["signals"]["location"]))

    # ---------- Relocation OK ----------
    r = new_job(location="Dallas, TX", work_mode="Onsite", location_preference="relocation_ok")
    check("create a Relocation OK job", r.status_code == 201 and r.json()["location_preference"] == "relocation_ok", r.text[:140])
    j1 = r.json()["id"]
    ranked, excl = result(j1)
    check("OK: Texas, Oklahoma and unknown are all eligible", {TX, OK, NONE} <= set(ranked), str(list(ranked)))
    check("OK: a candidate outside the US is excluded", IND in excl and excl[IND]["kind"] == "location" and "outside the US" in excl[IND]["reason"], str(excl.get(IND)))
    check("OK: location is not scored", ranked[OK]["signals"]["location"]["score"] is None, str(ranked[OK]["signals"]["location"]))

    # ---------- Relocation Not OK ----------
    r = new_job(location="Dallas, TX", work_mode="Onsite", location_preference="relocation_not_ok")
    check("create a Relocation Not OK job", r.status_code == 201, r.text[:140])
    j2 = r.json()["id"]
    ranked, excl = result(j2)
    check("Not OK: a Texas candidate in another city is eligible", TX in ranked and ranked[TX]["location_check"]["status"] == "eligible")
    check("Not OK: an Oklahoma candidate is excluded with the reason", OK in excl and "Relocation not OK" in excl[OK]["reason"], str(excl.get(OK)))
    check("Not OK: a candidate outside the US is excluded", IND in excl)
    check("Not OK: no location is flagged, not excluded", NONE in ranked and ranked[NONE]["location_check"]["status"] == "unknown", str(ranked.get(NONE, {}).get("location_check")))
    check("Not OK: the flag appears in the reasons", any(x.startswith("Location:") for x in ranked[NONE]["recommendation_reasons"]))

    # ---------- Multiple locations ----------
    two = [{"city": "Austin", "state": "tx", "relocation_ok": False}, {"city": "Tulsa", "state": "Oklahoma", "relocation_ok": False}]
    r = new_job(location="Austin, TX", work_mode="Onsite", location_preference="multiple", locations=two)
    check("create a Multiple locations job", r.status_code == 201 and len(r.json()["locations"]) == 2, r.text[:160])
    j3 = r.json()["id"]
    got = [(l["city"], l["state"], l["relocation_ok"]) for l in r.json()["locations"]]
    check("states are normalized and the order is kept", got == [("Austin", "TX", False), ("Tulsa", "OK", False)], str(got))
    ranked, excl = result(j3)
    check("Multiple: Texas and Oklahoma candidates both qualify", TX in ranked and OK in ranked)
    check("Multiple: unknown location is flagged", ranked[NONE]["location_check"]["status"] == "unknown")
    check("Multiple: a candidate outside the US is excluded", IND in excl)

    r = c.patch(f"/jobs/{j3}", json={"locations": [{"city": "Austin", "state": "TX", "relocation_ok": False},
                                                   {"city": "Denver", "state": "CO", "relocation_ok": False}]})
    check("replace the locations", r.status_code == 200 and [l["state"] for l in r.json()["locations"]] == ["TX", "CO"], r.text[:160])
    ranked, excl = result(j3)
    check("after the change the Oklahoma candidate is excluded", OK in excl and TX in ranked, str(list(excl)))

    r = c.patch(f"/jobs/{j3}", json={"locations": [{"city": "Austin", "state": "TX", "relocation_ok": False},
                                                   {"city": "Boston", "state": "MA", "relocation_ok": True}]})
    ranked, excl = result(j3)
    check("one Relocation OK location widens eligibility", OK in ranked and ranked[OK]["location_check"]["status"] == "eligible", str(list(excl)))
    check("one Relocation OK location makes unknown eligible", ranked[NONE]["location_check"]["status"] == "eligible")
    got = [(l["city"], l["relocation_ok"]) for l in c.get(f"/jobs/{j3}").json()["locations"]]
    check("each location keeps its own flag", got == [("Austin", False), ("Boston", True)], str(got))

    r = c.patch(f"/jobs/{j3}", json={"location_preference": "relocation_ok"})
    j = r.json()
    check("switching away from Multiple clears the locations", r.status_code == 200 and j["locations"] == [] and j["location_preference"] == "relocation_ok", r.text[:160])

    # ---------- refused combinations ----------
    one = [{"city": "Austin", "state": "TX", "relocation_ok": False}]
    for label, body in [
        ("Multiple with an empty list", dict(location_preference="multiple", locations=[])),
        ("Multiple with no list", dict(location_preference="multiple")),
        ("Not OK with no US state in the job location", dict(location="Remote", location_preference="relocation_not_ok")),
        ("Not OK with no job location", dict(location_preference="relocation_not_ok")),
        ("a state that does not exist", dict(location_preference="multiple", locations=[{"city": "X", "state": "ZZ", "relocation_ok": False}])),
        ("the same location twice", dict(location_preference="multiple", locations=one + one)),
        ("locations with Relocation OK", dict(location="Dallas, TX", location_preference="relocation_ok", locations=one)),
        ("locations with no preference", dict(locations=one)),
        ("an unknown preference", dict(location_preference="anywhere")),
    ]:
        check(f"refused: {label}", new_job(**body).status_code == 422)
    r = c.patch(f"/jobs/{j2}", json={"location": "Remote"})
    check("refused: removing the state from a Not OK job", r.status_code == 422, str(r.status_code))
    check("the refused edit changed nothing", c.get(f"/jobs/{j2}").json()["location"] == "Dallas, TX")
    r = c.patch(f"/jobs/{j2}", json={"location": "Plano, TX"})
    check("moving a Not OK job within its state is fine", r.status_code == 200 and r.json()["location_preference"] == "relocation_not_ok", r.text[:140])

    # ---------- audit ----------
    with SessionLocal() as db:
        edited = db.scalar(select(func.count()).select_from(ActivityLog).where(
            ActivityLog.action == "job.edited", ActivityLog.object_id == j3))
        created = db.scalar(select(func.count()).select_from(ActivityLog).where(
            ActivityLog.action == "job.created", ActivityLog.object_id == j3))
        last = db.scalars(select(ActivityLog).where(ActivityLog.action == "job.edited", ActivityLog.object_id == j3)
                          .order_by(ActivityLog.id.desc())).first()
    check("audit: job created and edited rows", created == 1 and edited >= 3, f"{created}, {edited}")
    check("audit: an edit records the old and new locations",
          last is not None and "locations" in (last.old_value or {}) and "locations" in (last.new_value or {}),
          str(last.new_value if last else None))
finally:
    for key, cid in cands.items():
        c.delete(f"/candidates/{cid}", params={"confirm_name": NAMES[key]})
    with SessionLocal() as db:
        db.execute(delete(Job).where(Job.id.in_(jobs)))
        db.commit()
        left = db.scalar(select(func.count()).select_from(Job).where(Job.title == "TEST Loc Job"))
    check("test jobs removed", left == 0, str(left))
    gone = [cid for cid in cands.values() if c.get(f"/candidates/{cid}").status_code != 404]
    check("test candidates removed", not gone, str(gone))

print(f"{passed} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  -", f)
    sys.exit(1)