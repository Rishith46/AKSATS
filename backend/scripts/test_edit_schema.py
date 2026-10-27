from pydantic import ValidationError

from app.schemas.candidates import CandidateCreate, CandidateUpdate

assert CandidateUpdate(email="  ").email is None
assert CandidateUpdate(email=" a@b.co ").email == "a@b.co"
for bad in ({"email": "nope"}, {"phone": "12"}, {"rate": -1}, {"rate_unit": "week"},
            {"linkedin_url": "https://example.com"}, {"total_experience_years": -1}):
    try:
        CandidateUpdate(**bad)
        raise SystemExit("accepted a bad value: " + repr(bad))
    except ValidationError:
        pass
assert CandidateUpdate(country="usa").country == "United States"
assert CandidateUpdate(phone="(555) 010-9999").phone == "(555) 010-9999"
assert CandidateUpdate(city="Plano").model_dump(exclude_unset=True) == {"city": "Plano"}
assert "city" not in CandidateCreate().model_dump()
print("edit schema checks passed")