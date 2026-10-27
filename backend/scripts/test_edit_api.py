import getpass
import sys

import httpx

BASE = "http://127.0.0.1:8000"
NAME = "TEST Edit Candidate"
EMAIL = "rishith@allknownservices.com"

pw = __import__("os").environ.get("AKS_TEST_PASSWORD") or getpass.getpass("Rishith password: ")
c = httpx.Client(base_url=BASE, timeout=30)
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


def patch(cid, body):
    return c.patch(f"/candidates/{cid}", json=body)


cid = None
try:
    r = c.post("/candidates", json={"full_name": NAME, "location": "Austin, TX"})
    check("create mock candidate", r.status_code == 201, r.text[:120])
    cid = r.json()["id"]

    r = patch(cid, {"city": "Dallas"})
    check("edit city only keeps the state", r.status_code == 200 and r.json()["location"] == "Dallas, TX", r.text[:120])
    r = patch(cid, {"state": "Oklahoma", "city": "Tulsa"})
    check("full state name becomes a code", r.json()["location"] == "Tulsa, OK", r.text[:120])
    r = patch(cid, {"state": "Karnataka"})
    check("non-US state is refused without a country", r.status_code == 422, str(r.status_code))
    r = patch(cid, {"country": "India", "city": "Hyderabad", "state": "Telangana"})
    check("non-US location with country", r.status_code == 200 and r.json()["country"] == "India"
          and r.json()["location"] == "Hyderabad, Telangana", r.text[:160])
    r = patch(cid, {"country": "usa", "city": "Plano", "state": "tx"})
    check("country spelling and state code are normalized",
          r.json()["country"] == "United States" and r.json()["location"] == "Plano, TX", r.text[:160])

    r = patch(cid, {"rate": 65.5, "rate_unit": "hour", "visa_status": "H1B", "availability": "2 weeks notice",
                    "phone": "(555) 010-9999", "email": "edit.test@example.com",
                    "linkedin_url": "https://www.linkedin.com/in/edit-test"})
    j = r.json()
    check("edit rate, visa, availability and contact details", r.status_code == 200 and j["visa_status"] == "H1B"
          and j["availability"] == "2 weeks notice" and j["email"] == "edit.test@example.com"
          and float(j["rate"]) == 65.5 and j["rate_unit"] == "hour", r.text[:200])

    for label, body in [("bad email", {"email": "nope"}), ("short phone", {"phone": "12"}),
                        ("negative rate", {"rate": -5}), ("bad rate unit", {"rate_unit": "week"}),
                        ("bad visa", {"visa_status": "Bogus"}),
                        ("bad LinkedIn", {"linkedin_url": "https://example.com/x"}),
                        ("negative years", {"total_experience_years": -1})]:
        check(f"refused: {label}", patch(cid, body).status_code == 422)
    j = c.get(f"/candidates/{cid}").json()
    check("refused edits changed nothing", j["email"] == "edit.test@example.com" and j["visa_status"] == "H1B"
          and j["location"] == "Plano, TX")

    r = patch(cid, {"availability": "", "linkedin_url": ""})
    check("blank clears a field", r.status_code == 200 and r.json()["availability"] is None
          and r.json()["linkedin_url"] is None, r.text[:160])

    p = c.get(f"/candidates/{cid}/profile").json()
    check("profile shows city, state and country",
          (p.get("city"), p.get("state"), p.get("country")) == ("Plano", "TX", "United States"),
          str((p.get("city"), p.get("state"), p.get("country"))))
    check("edited fields are labeled confirmed",
          all(p["field_sources"].get(k) == "confirmed" for k in ("location", "country", "visa_status", "email", "phone", "rate")),
          str(p["field_sources"]))
    check("search finds the new location", cid in [x["id"] for x in c.get("/candidates", params={"location": "plano"}).json()])
    check("visa filter finds the candidate", cid in [x["id"] for x in c.get("/candidates", params={"visa": "H1B"}).json()])
finally:
    if cid is not None:
        d = c.delete(f"/candidates/{cid}", params={"confirm_name": NAME})
        check("mock candidate removed", d.status_code == 200, str(d.status_code))

print(f"{passed} checks passed")
if failed:
    print("FAILED:")
    for f in failed:
        print("  -", f)
    sys.exit(1)