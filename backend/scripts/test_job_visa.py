from pydantic import ValidationError

from app.schemas.jobs import JobCreate, JobUpdate
from app.services.matching import visa_score


assert JobCreate.model_validate({
    "title": "Engineer", "visa_requirements": ["USC", "GC", "USC"],
}).visa_requirements == ["USC", "GC"]
assert JobCreate.model_validate({
    "title": "Engineer", "visa_requirements": "USC, GC",
}).visa_requirements == ["USC", "GC"]
assert JobUpdate.model_validate({"visa_requirements": ["OPT"]}).visa_requirements == ["OPT"]
assert JobUpdate.model_validate({}).model_fields_set == set()

try:
    JobCreate.model_validate({"title": "Engineer", "visa_requirements": ["Not a visa type"]})
except ValidationError:
    pass
else:
    raise AssertionError("unknown visa types must be rejected")

assert visa_score("USC,GC", "GC")[0] == 1.0
assert visa_score("USC,GC", "H1B")[0] == 0.0
assert visa_score(None, "H1B")[0] is None

print("job visa checks passed")
