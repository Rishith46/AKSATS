from types import SimpleNamespace as L

from app.services.location_rules import check_location, location_signal


def loc(city, state, ok):
    return L(city=city, state=state, relocation_ok=ok)


# no preference set: nothing changes for existing jobs
assert check_location(None, "Dallas, TX", [], "Tulsa, OK", None)[0] == "not_applicable"
assert location_signal(None, "Dallas, TX", "Onsite", [], "Austin, TX") == (0.5, "Same state, different city")

# Relocation OK: anywhere in the US
assert check_location("relocation_ok", "Dallas, TX", [], "Tulsa, OK", None)[0] == "eligible"
assert check_location("relocation_ok", "Dallas, TX", [], None, None)[0] == "eligible"
assert check_location("relocation_ok", "Dallas, TX", [], "Tulsa, OK", "United States")[0] == "eligible"
assert check_location("relocation_ok", "Dallas, TX", [], "Hyderabad, Telangana", "India")[0] == "ineligible"
assert location_signal("relocation_ok", "Dallas, TX", "Onsite", [], "Tulsa, OK")[0] is None

# Relocation Not OK: state-level
assert check_location("relocation_not_ok", "Dallas, TX", [], "Austin, TX", None)[0] == "eligible"
assert check_location("relocation_not_ok", "Dallas, TX", [], "Dallas, TX", None)[0] == "eligible"
s, d = check_location("relocation_not_ok", "Dallas, TX", [], "Tulsa, OK", None)
assert s == "ineligible" and "OK" in d and "TX" in d
assert check_location("relocation_not_ok", "Dallas, TX", [], None, None)[0] == "unknown"
assert check_location("relocation_not_ok", "Dallas, TX", [], "Plano", None)[0] == "unknown"
assert check_location("relocation_not_ok", "Remote", [], "Austin, TX", None)[0] == "unknown"
assert check_location("relocation_not_ok", "TX", [], "Austin, TX", None)[0] == "eligible"
assert check_location("relocation_not_ok", "Dallas, TX", [], "Austin, Texas", None)[0] == "eligible"
assert check_location("relocation_not_ok", "Dallas, TX", [], "Hyderabad, Telangana", "India")[0] == "ineligible"
assert location_signal("relocation_not_ok", "Dallas, TX", "Onsite", [], "Dallas, TX")[0] == 1.0
assert location_signal("relocation_not_ok", "Dallas, TX", "Onsite", [], "Austin, TX")[0] == 0.5

# Multiple locations: qualifies if ANY location accepts the candidate
two = [loc("Austin", "TX", False), loc("Tulsa", "OK", False)]
assert check_location("multiple", "Austin, TX", two, "Dallas, TX", None)[0] == "eligible"
assert check_location("multiple", "Austin, TX", two, "Norman, OK", None)[0] == "eligible"
s, d = check_location("multiple", "Austin, TX", two, "Denver, CO", None)
assert s == "ineligible" and "OK, TX" in d and "CO" in d
assert check_location("multiple", "Austin, TX", two, None, None)[0] == "unknown"
mixed = [loc("Austin", "TX", False), loc("Boston", "MA", True)]
assert check_location("multiple", "Austin, TX", mixed, "Denver, CO", None)[0] == "eligible"
assert check_location("multiple", "Austin, TX", mixed, None, None)[0] == "eligible"
assert check_location("multiple", "Austin, TX", mixed, "Hyderabad, Telangana", "India")[0] == "ineligible"
assert check_location("multiple", "Austin, TX", [], "Denver, CO", None)[0] == "unknown"
ok_first = [loc("Austin", "TX", True), loc("Tulsa", "OK", False)]
assert check_location("multiple", None, ok_first, "Denver, CO", None)[0] == "eligible"
state_only = [loc(None, "TX", False)]
assert check_location("multiple", None, state_only, "Waco, TX", None)[0] == "eligible"
assert check_location("multiple", None, state_only, "Tulsa, OK", None)[0] == "ineligible"

# the small score factor for Multiple locations
assert location_signal("multiple", None, "Onsite", two, "Austin, TX")[0] == 1.0
assert location_signal("multiple", None, "Onsite", two, "Waco, TX")[0] == 0.5
assert location_signal("multiple", None, "Onsite", two, "Denver, CO")[0] == 0.0
assert location_signal("multiple", None, "Onsite", state_only, "Waco, TX")[0] == 0.5
assert location_signal("multiple", None, "Onsite", mixed, "Denver, CO")[0] is None
assert location_signal("multiple", None, "Onsite", two, None)[0] is None
print("location rule checks passed")