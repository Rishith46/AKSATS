from pydantic import ValidationError

from app.schemas.candidates import CandidateCreate, CandidateUpdate
from app.visa import VISA_VALUES

for cls in (CandidateCreate, CandidateUpdate):
    for v in VISA_VALUES:
        assert cls(visa_status=v).visa_status == v, (cls.__name__, v)
    assert cls().visa_status is None
    assert cls(visa_status="").visa_status is None
    assert cls(visa_status=" OPT ").visa_status == "OPT"
    for bad in ["Bogus", "H-1B", "opt", "Green Card"]:
        try:
            cls(visa_status=bad)
            raise SystemExit(f"{cls.__name__} accepted a bad value: {bad}")
        except ValidationError:
            pass
assert "visa_status" not in CandidateUpdate(location="Austin, TX").model_dump(exclude_unset=True)
print("visa schema checks passed")