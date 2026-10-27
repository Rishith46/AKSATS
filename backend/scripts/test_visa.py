from app.services.matching import visa_score
from app.visa import VISA_OPTIONS, VISA_VALUES, check_visa

# the list
assert len(VISA_VALUES) == 10 and len(set(VISA_VALUES)) == 10
assert VISA_VALUES == ["Indian Candidate", "USC", "GC", "H1B", "H4-EAD", "GC-EAD", "OPT", "STEM-OPT", "TN", "E3"]
assert dict(VISA_OPTIONS)["USC"] == "USC (United States Citizen)" and dict(VISA_OPTIONS)["GC"] == "GC (Green Card)"

# validation
for v in VISA_VALUES:
    assert check_visa(v) == v
assert check_visa(None) is None and check_visa("") is None and check_visa("  ") is None
assert check_visa(" OPT ") == "OPT"
for bad in ["H-1B", "opt", "Citizen", "F1", "Green Card", "H4"]:
    try:
        check_visa(bad)
        raise SystemExit("accepted a bad value: " + bad)
    except ValueError:
        pass

# matching: whole-token comparison
assert visa_score("USC or GC", "GC")[0] == 1.0
assert visa_score("USC or GC", "H1B")[0] == 0.0
assert visa_score("USC or GC", None)[0] is None and visa_score(None, "H1B")[0] is None
assert visa_score("STEM-OPT only", "OPT")[0] == 0.0
assert visa_score("OPT or STEM-OPT", "OPT")[0] == 1.0
assert visa_score("OPT or STEM-OPT", "STEM-OPT")[0] == 1.0
assert visa_score("GC-EAD only", "GC")[0] == 0.0
assert visa_score("GC, GC-EAD", "GC-EAD")[0] == 1.0
assert visa_score("US Citizen or Green Card", "USC")[0] == 1.0
assert visa_score("US Citizen or Green Card", "GC")[0] == 1.0
assert visa_score("USC/GC", "GC")[0] == 1.0
assert visa_score("H-1B ok", "H1B")[0] == 1.0
assert visa_score("USC, GC", "TN")[0] == 0.0
assert visa_score("non-citizen visas only", "USC")[0] == 0.0
print("visa checks passed")