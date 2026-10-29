from pydantic import ValidationError

from app.schemas.candidates import CandidateUpdate


ALLOWED = {
    "Open",
    "Vendor Submission",
    "Client Submission",
    "Vendor Interview Scheduled",
    "Client Interview Scheduled",
    "Rejected",
}

for status in ALLOWED:
    assert CandidateUpdate(status=status).status == status

for status in ("New", "Submitted", "In Progress", "invalid"):
    try:
        CandidateUpdate(status=status)
        raise AssertionError(f"Unsupported candidate status accepted: {status}")
    except ValidationError:
        pass

print("Candidate status schema checks passed.")
